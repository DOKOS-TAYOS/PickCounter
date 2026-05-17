# Changelog

## Unreleased

- Added Dependabot configuration for Python dependencies and GitHub Actions.
- Added GitHub Actions security checks with dependency review and `pip-audit`.
- Documented CodeQL as managed by GitHub default setup to avoid conflicts with advanced CodeQL workflows.
- Pinned runtime dependency versions for more reproducible Streamlit Community Cloud deployments.
- Added a 10 MB per-file upload limit for Streamlit image uploads.
- Ignored local Streamlit secrets files so credentials are not committed accidentally.
- Added upload size validation tests with `unittest`.
