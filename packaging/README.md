# Packaging Artifacts

Release artifacts produced by the GitHub release workflow are intended to be
consumed by packaging workflows.

## Windows winget manifests (internal for now)

Generated winget manifest files are emitted to `dist/` by `tools/release.py`
during release builds.

At the current stage, these files are release-engineering artifacts and are not
the primary end-user install path.
