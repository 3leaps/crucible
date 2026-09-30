# Native CI platform checks

Crucible's workflow runs `make check-contracts` on five OS/architecture pairs:
Linux amd64 and arm64, Darwin arm64, and Windows amd64 and arm64.
Darwin amd64 (Intel Mac) is explicitly unsupported, not an untested supported
target. Darwin arm64 is the only supported Mac target.

## Jobs and release gating

`.github/workflows/check.yml` has a required Linux repository-quality job plus
two Linux container cells and three native macOS/Windows cells. Each matrix
uses `fail-fast: false` so one
failure does not suppress the remaining platform evidence. Its aggregate `check`
job runs even after a prerequisite failure and accepts only `success` from the
quality job and both matrices; failure, cancellation, skipping or missing
results are not success.

### Required coverage map

| Checks                                                                      | Required Linux quality | All five native cells |
| --------------------------------------------------------------------------- | ---------------------- | --------------------- |
| Full `make check` (unchanged)                                               | Yes                    | No                    |
| Formatting and Goneat lint/workflow policy                                  | Yes                    | No                    |
| Bootstrap engine verification, attribution, release policy/surface controls | Yes                    | No                    |
| Schema meta-validation and configuration/example validation                 | Yes                    | Yes                   |
| Role, coverage and taxonomy controls                                        | Yes                    | Yes                   |
| Contract semantic positive/negative suites and canonical-byte vectors       | Yes                    | Yes                   |
| Manifest validation and supported input read-denial controls                | Yes                    | Yes                   |
| Platform/source/path/permission regression tests                            | Yes                    | Yes                   |
| Executing Goneat/Python native identity and no tracked changes              | Yes                    | Yes                   |

`check-contracts` checks required tools before invoking `lint-schemas`,
`lint-config` and `test-ci-platforms`, including under parallel make. It does not
certify formatter or maintainer-governance stacks on every supported platform.
No existing check is removed from required coverage.

The release workflow calls the same quality workflow. Tag signature verification
depends on both the release-specific checks and the complete platform matrix;
publication therefore cannot proceed on a partial platform result.

## Toolchain

Linux uses the pinned glibc tools-runner image with UID 1001. macOS and Windows
install native Go and Python through SHA-pinned setup actions. The
`bootstrap-release-tools` Make target installs only the repo-local verified
sfetch/Goneat chain, without invoking the broader developer package-manager
bootstrap. Windows executable names retain their `.exe` suffix.

Windows arm64 explicitly selects a native source build because the pinned Goneat
release has no Windows arm64 archive. It still installs verified sfetch through
`bootstrap-sfetch`, but does not attempt or fall back from a Goneat binary download.
`.github/goneat-source.json` pins the Go module/version, module and go.mod checksums,
and compiler. The source route uses the Go checksum database and public module
proxy, with no private-module bypass, automatic compiler download or cross-build.
It verifies downloaded metadata before installation and executable build metadata
afterward, including module checksum, compiler and Windows arm64 identity.

This is a checksum-verified local source build, not a minisigned upstream release
binary. Its `goneat dev` banner is preserved; the pinned module version and build
metadata establish source identity rather than a fabricated release banner.
Other acquisition lanes retain their existing release-binary/container paths.

`scripts/install-ci-native-tools.sh` installs the native acquisition chain only.
OS shell prerequisites (make, jq and macOS hash utilities) come from the runner's
package manager. Native lanes do not install Node, formatters or workflow linters.
The required Linux quality job uses preinstalled tools from the pinned image;
no job installs tools inside that image. OS package-manager prerequisites are
not a fully hash-locked dependency closure.

`scripts/ci-platforms.py` checks OS, architecture, 64-bit Python, runner
architecture metadata and the executing Goneat platform/version against the
Makefile pin. Windows also checks the Python interpreter's build architecture,
not merely the underlying hardware. Go installation checks `GOHOSTARCH` before
acquiring native tools. These checks refuse x64 validator/interpreter
emulation on an arm64 cell. Windows shell prerequisites may themselves use the
host's compatibility layer; this does not claim every auxiliary executable is
native arm64.

All native cells run the same supported contract/input gates and require no
tracked changes. GNU/Bash prerequisites support those shell controls on macOS
and Windows. Formatting/lint and maintainer-governance gates remain required
in the Linux quality job, not silently omitted from CI.

Unreadable-file/directory fixtures use POSIX modes on Unix and current-user deny
ACLs on Windows. The deny mask covers file data/directory listing (`RD`), not
ACL metadata (`READ_CONTROL`), so cleanup can still read and restore the DACL.
Directory fixtures also deny access to their known disposable
record; Windows name enumeration is not assumed to be denied. The shared test
helper verifies that record reads are actually denied
before invoking each normative validator, then restores fixture access. A no-op
permission change fails fixture setup rather than silently skipping that control.

## Evidence boundary

Native validator execution is not adopter conformance, runtime storage durability
or image provenance. A green matrix cannot replace signature/attestation review
of the tools-runner image. Re-run checks on the final integrated release head.
