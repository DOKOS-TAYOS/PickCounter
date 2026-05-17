"""Security checks for uploaded files in the Streamlit app."""

from __future__ import annotations

import unittest

from streamlit_app import MAX_UPLOAD_BYTES, UploadedImageTooLargeError, _validate_uploaded_image_size


class StreamlitUploadSecurityTest(unittest.TestCase):
    """Security checks for Streamlit upload validation."""

    def test_validate_uploaded_image_size_accepts_file_at_limit(self) -> None:
        """A file exactly at the configured limit is accepted."""
        _validate_uploaded_image_size(MAX_UPLOAD_BYTES)

    def test_validate_uploaded_image_size_rejects_file_over_limit(self) -> None:
        """A file over the configured limit is rejected before image processing."""
        with self.assertRaisesRegex(UploadedImageTooLargeError, "La imagen es demasiado grande"):
            _validate_uploaded_image_size(MAX_UPLOAD_BYTES + 1)


if __name__ == "__main__":
    unittest.main()
