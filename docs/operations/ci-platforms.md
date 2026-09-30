# Native CI platform checks

Crucible's quality workflow runs `make check` on five OS/architecture pairs:
Linux amd64 and arm64, Darwin arm64, and Windows amd64 and arm64.
Darwin amd64 (Intel Mac) is explicitly unsupported, not an untested supported
target. Darwin arm64 is the only supported Mac target.

## Jobs and release gating

`.github/workflows/check.yml` separates the two Linux container cells from the
three native macOS/Windows cells. Each matrix uses `fail-fast: false` so one
failure does not suppress the remaining platform evidence. Its aggregate `check`
job runs even after a prerequisite failure and accepts only `success` from both
matrices; failure, cancellation, skipping or missing results are not success.

The release workflow calls the same quality workflow. Tag signature verification
depends on both the release-specific checks and the complete platform matrix;
publication therefore cannot proceed on a partial platform result.

## Toolchain

Linux uses the pinned glibc tools-runner image with UID 1001. macOS and Windows
install native Go and Python, plus supporting Node tooling, through SHA-pinned
setup actions. Node's process architecture is not asserted by these controls. The
`bootstrap-release-tools` Make target installs only the repo-local verified
sfetch/Goneat chain, without invoking the broader developer package-manager
bootstrap. Windows executable names retain their `.exe` suffix.

`scripts/install-ci-native-tools.sh` installs versioned supporting check tools.
Formatter/linter pins mirror the tools-runner inventory; OS shell prerequisites
are installed through the runner's package manager, and effective tool versions
are logged. This is not a fully hash-locked supporting-tool dependency closure.
The local package lock is not rewritten by CI tool installation.

`scripts/ci-platforms.py` checks OS, architecture, 64-bit Python, runner
architecture metadata and the executing Goneat platform/version against the
Makefile pin. Windows also checks the Python interpreter's build architecture,
not merely the underlying hardware. Go installation checks `GOHOSTARCH` before
building native helper tools. These checks refuse x64 validator/interpreter
emulation on an arm64 cell. Windows shell prerequisites may themselves use the
host's compatibility layer; this does not claim every auxiliary executable is
native arm64.

All cells run the repository's formatting, lint, schema/config, contract and
release-control gates, then require no tracked changes. GNU/Bash prerequisites
support the existing shell controls on macOS and Windows; platform jobs do not
silently omit controls.

## Evidence boundary

Native validator execution is not adopter conformance, runtime storage durability
or image provenance. A green matrix cannot replace signature/attestation review
of the tools-runner image. Re-run checks on the final integrated release head.
