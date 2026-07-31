#!/usr/bin/env sh
# Validates the journal-set properties of a review journal — the properties
# that span the manifest and the event stream together, which no single-file
# schema check can express:
#
#   1. Cross-stream ceiling: no event's classification exceeds the manifest
#      ceiling on either dimension (sensitivity, access_tier). An event
#      classified 'unknown' under a classified ceiling fails closed — it
#      cannot be compared, so it cannot be admitted.
#   2. Roster closure: seat names are unique in the roster (a duplicated seat
#      makes the event join ambiguous and fails); every event's seat is
#      declared in the roster; every event carries a participant_ref and it
#      resolves to that seat's declared participant.
#   3. Author-does-not-approve, at the person level: the participant occupying
#      an author seat neither records an accepted gate (through any seat) nor
#      sets the ceiling. ceiling.set_by must resolve to exactly one declared
#      roster participant - a setter with no resolvable participant is a
#      failure, never a pass. The event schema enforces the seat-level rule;
#      this check closes the person-level gap via the participant join.
#
# Exit 0 only when every property holds. Schema validation of each file is
# goneat's job and is not repeated here.
set -eu

if [ "$#" -ne 2 ]; then
    echo "usage: validate-review-journal-set.sh <review-manifest.json> <review-events.ndjson>" >&2
    exit 2
fi

manifest_path="$1"
events_path="$2"
failures=0

fail() {
    failures=$((failures + 1))
    printf '    [!!] %s\n' "$1" >&2
}

[ -f "$manifest_path" ] || {
    echo "    [!!] manifest missing: $manifest_path" >&2
    exit 1
}
[ -f "$events_path" ] || {
    echo "    [!!] events missing: $events_path" >&2
    exit 1
}

jq -e . "$manifest_path" >/dev/null || {
    echo "    [!!] manifest is not valid JSON" >&2
    exit 1
}

sens_rank() {
    case "$1" in
        0-public) echo 0 ;;
        1-confidential) echo 1 ;;
        2-blinded) echo 2 ;;
        3-proprietary) echo 3 ;;
        4-personal) echo 4 ;;
        5-privileged) echo 5 ;;
        6-eyes-only) echo 6 ;;
        *) echo -1 ;;
    esac
}

tier_rank() {
    case "$1" in
        public) echo 0 ;;
        internal) echo 1 ;;
        restricted) echo 2 ;;
        privileged) echo 3 ;;
        eyes-only) echo 4 ;;
        *) echo -1 ;;
    esac
}

ceiling_sens=$(jq -r '.ceiling.sensitivity' "$manifest_path")
ceiling_tier=$(jq -r '.ceiling.access_tier' "$manifest_path")
ceiling_set_by=$(jq -r '.ceiling.set_by // ""' "$manifest_path")
ceiling_sens_rank=$(sens_rank "$ceiling_sens")
ceiling_tier_rank=$(tier_rank "$ceiling_tier")

# Roster uniqueness: a duplicated seat name makes the event join ambiguous.
duplicate_seats=$(jq -r '[.seats[].seat] | group_by(.) | map(select(length > 1) | .[0]) | join(" ")' "$manifest_path")
if [ -n "$duplicate_seats" ]; then
    fail "roster declares duplicate seat(s): $duplicate_seats - the event join is ambiguous"
fi

# Participants of author seats, and the participant behind each declared seat.
author_participants=$(jq -r '[.seats[] | select(.seat == "author") | .participant.id] | join("\n")' "$manifest_path")

participant_for_seat() {
    jq -r --arg s "$1" '[.seats[] | select(.seat == $s) | .participant.id] | first // ""' "$manifest_path"
}

is_author_participant() {
    [ -n "$1" ] || return 1
    printf '%s\n' "$author_participants" | grep -Fxq "$1"
}

# Ceiling setter must resolve to exactly one roster participant, and that
# participant may not be an author participant. No resolution = failure.
if [ -z "$ceiling_set_by" ]; then
    fail "ceiling.set_by is missing - the ceiling-setter must be declared"
else
    setter_matches=$(jq -r --arg s "$ceiling_set_by" '[.seats[] | select(.seat == $s)] | length' "$manifest_path")
    if [ "$setter_matches" -ne 1 ]; then
        fail "ceiling.set_by seat '$ceiling_set_by' resolves to $setter_matches roster entries; it must resolve to exactly one"
    else
        setter_participant=$(participant_for_seat "$ceiling_set_by")
        if is_author_participant "$setter_participant"; then
            fail "ceiling.set_by seat '$ceiling_set_by' is occupied by an author participant ('$setter_participant'): the ceiling-setter is not the author"
        fi
    fi
fi

lineno=0
while IFS= read -r line; do
    lineno=$((lineno + 1))
    [ -n "$line" ] || continue

    if ! printf '%s\n' "$line" | jq -e . >/dev/null 2>&1; then
        fail "line $lineno: not valid JSON"
        continue
    fi

    ev_sens=$(printf '%s\n' "$line" | jq -r '.classification.sensitivity // ""')
    ev_tier=$(printf '%s\n' "$line" | jq -r '.classification.access_tier // ""')
    ev_seat=$(printf '%s\n' "$line" | jq -r '.seat // ""')
    ev_gate=$(printf '%s\n' "$line" | jq -r '.gate // ""')
    ev_pref=$(printf '%s\n' "$line" | jq -r '.agent.participant_ref // ""')

    # 1. Cross-stream ceiling.
    if [ "$ceiling_sens" = "unknown" ]; then
        # An unclassified ceiling admits only unclassified entries; the record
        # is in the declared-temporary state end to end or not at all.
        if [ "$ev_sens" != "unknown" ] || [ "$ev_tier" != "unknown" ]; then
            fail "line $lineno: classified entry ($ev_sens/$ev_tier) under an unclassified ceiling"
        fi
    else
        ev_sens_rank=$(sens_rank "$ev_sens")
        ev_tier_rank=$(tier_rank "$ev_tier")
        if [ "$ev_sens_rank" -lt 0 ] || [ "$ev_tier_rank" -lt 0 ]; then
            fail "line $lineno: entry classification ($ev_sens/$ev_tier) cannot be compared to the ceiling and fails closed"
        else
            if [ "$ev_sens_rank" -gt "$ceiling_sens_rank" ]; then
                fail "line $lineno: entry sensitivity '$ev_sens' exceeds ceiling '$ceiling_sens'"
            fi
            if [ "$ev_tier_rank" -gt "$ceiling_tier_rank" ]; then
                fail "line $lineno: entry access_tier '$ev_tier' exceeds ceiling '$ceiling_tier'"
            fi
        fi
    fi

    # 2. Roster closure. The join is mandatory: an event with no
    # participant_ref cannot support the person-level check and fails.
    seat_participant=$(participant_for_seat "$ev_seat")
    if [ -z "$seat_participant" ]; then
        fail "line $lineno: seat '$ev_seat' is not declared in the manifest roster"
    fi
    if [ -z "$ev_pref" ]; then
        fail "line $lineno: event carries no agent.participant_ref - the participant join is mandatory"
    elif [ -n "$seat_participant" ] && [ "$ev_pref" != "$seat_participant" ]; then
        fail "line $lineno: participant_ref '$ev_pref' does not match the roster participant '$seat_participant' for seat '$ev_seat'"
    fi

    # 3. Author-does-not-approve, person level.
    if [ "$ev_gate" = "accepted" ] && [ -n "$ev_pref" ]; then
        if is_author_participant "$ev_pref"; then
            fail "line $lineno: accepted gate recorded by author participant '$ev_pref' (through seat '$ev_seat')"
        fi
    fi
done <"$events_path"

if [ "$failures" -gt 0 ]; then
    printf '    [!!] review journal set: %d violation(s)\n' "$failures" >&2
    exit 1
fi

printf '    [ok] review journal set: cross-stream ceiling, roster closure, and author-does-not-approve hold\n'
