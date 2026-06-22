# Changelog

## Unreleased

- Added Dependabot configuration for Python dependencies and GitHub Actions.
- Added GitHub Actions security checks with dependency review and `pip-audit`.
- Documented CodeQL as managed by GitHub default setup to avoid conflicts with advanced CodeQL workflows.
- Pinned runtime dependency versions for more reproducible Streamlit Community Cloud deployments.
- Added a 10 MB per-file upload limit for Streamlit image uploads.
- Ignored local Streamlit secrets files so credentials are not committed accidentally.
- Added upload size validation tests with `unittest`.
- Updated Dependabot-recommended Python dependencies: `numpy` 2.4.5 and `streamlit` 1.57.0.
- Updated Dependabot-recommended GitHub Actions: `actions/checkout` v7, `actions/setup-python` v6, and `actions/dependency-review-action` v5.
