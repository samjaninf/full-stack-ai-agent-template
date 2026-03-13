{%- if cookiecutter.enable_google_drive_ingestion %}
"""Google Drive API client for document ingestion.

This module provides an async Google Drive API client for listing and downloading
files from a specified Google Drive folder.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from app.core.config import settings


# Supported MIME types for ingestion
SUPPORTED_MIME_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
]


@dataclass
class GoogleDriveFile:
    """Represents a file from Google Drive."""

    id: str
    name: str
    mime_type: str
    modified_time: datetime
    size: int | None = None
    web_view_link: str | None = None

    @property
    def is_supported(self) -> bool:
        """Check if the file type is supported for ingestion."""
        return self.mime_type in SUPPORTED_MIME_TYPES

    @property
    def extension(self) -> str:
        """Get the file extension."""
        if "." in self.name:
            return self.name.rsplit(".", 1)[-1].lower()
        return ""


class GoogleDriveClient:
    """Async Google Drive API client.

    Provides methods for authenticating with Google Drive API and
    listing/downloading files from a specified folder.
    """

    def __init__(self) -> None:
        """Initialize the Google Drive client with credentials from settings."""
        self.client_id = settings.GOOGLE_DRIVE_CLIENT_ID
        self.client_secret = settings.GOOGLE_DRIVE_CLIENT_SECRET
        self.refresh_token = settings.GOOGLE_DRIVE_REFRESH_TOKEN
        self._access_token: str | None = None

        # Validate credentials are configured
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            raise ValueError(
                "Google Drive credentials not configured. "
                "Set GOOGLE_DRIVE_CLIENT_ID, GOOGLE_DRIVE_CLIENT_SECRET, "
                "and GOOGLE_DRIVE_REFRESH_TOKEN in environment."
            )

    async def _get_access_token(self) -> str:
        """Get a valid access token using the refresh token.

        Returns:
            A valid access token for API requests.

        Raises:
            httpx.HTTPStatusError: If token refresh fails.
        """
        if self._access_token:
            return self._access_token

        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
            self._access_token = token_data["access_token"]
            return self._access_token

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an authenticated request to the Google Drive API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to httpx

        Returns:
            JSON response from the API.
        """
        access_token = await self._get_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {access_token}"

        url = f"https://www.googleapis.com/drive/v3{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()

    async def list_files_in_folder(
        self,
        folder_id: str,
        page_size: int = 100,
    ) -> list[GoogleDriveFile]:
        """List all files in a specific Google Drive folder.

        Args:
            folder_id: The Google Drive folder ID.
            page_size: Maximum number of files to return per page.

        Returns:
            List of GoogleDriveFile objects.
        """
        query = f"'{folder_id}' in parents and trashed = false"

        params = {
            "q": query,
            "pageSize": page_size,
            "fields": "nextPageToken, files(id, name, mimeType, modifiedTime, size, webViewLink)",
        }

        files: list[GoogleDriveFile] = []
        page_token: str | None = None

        while True:
            if page_token:
                params["pageToken"] = page_token

            data = await self._request("GET", "/files", params=params)

            for file_data in data.get("files", []):
                modified_time = datetime.fromisoformat(
                    file_data["modifiedTime"].replace("Z", "+00:00")
                )
                files.append(
                    GoogleDriveFile(
                        id=file_data["id"],
                        name=file_data["name"],
                        mime_type=file_data["mimeType"],
                        modified_time=modified_time,
                        size=int(file_data["size"]) if "size" in file_data else None,
                        web_view_link=file_data.get("webViewLink"),
                    )
                )

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return files

    async def download_file(self, file_id: str) -> tuple[bytes, str]:
        """Download a file from Google Drive.

        Args:
            file_id: The Google Drive file ID.

        Returns:
            Tuple of (file_content_bytes, mime_type).
        """
        # First get the file metadata to determine mime type
        metadata = await self._request(
            "GET",
            f"/files/{file_id}",
            params={"fields": "mimeType"},
        )
        mime_type = metadata["mimeType"]

        # Download the file content
        content_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        access_token = await self._get_access_token()

        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(content_url, headers=headers)
            response.raise_for_status()
            return response.content, mime_type

    async def get_file_metadata(self, file_id: str) -> GoogleDriveFile:
        """Get metadata for a specific file.

        Args:
            file_id: The Google Drive file ID.

        Returns:
            GoogleDriveFile object with file metadata.
        """
        params = {
            "fields": "id, name, mimeType, modifiedTime, size, webViewLink",
        }

        data = await self._request("GET", f"/files/{file_id}", params=params)

        modified_time = datetime.fromisoformat(
            data["modifiedTime"].replace("Z", "+00:00")
        )

        return GoogleDriveFile(
            id=data["id"],
            name=data["name"],
            mime_type=data["mimeType"],
            modified_time=modified_time,
            size=int(data["size"]) if "size" in data else None,
            web_view_link=data.get("webViewLink"),
        )

    async def check_folder_exists(self, folder_id: str) -> bool:
        """Check if a folder exists and is accessible.

        Args:
            folder_id: The Google Drive folder ID.

        Returns:
            True if the folder exists and is accessible.
        """
        try:
            await self._request(
                "GET",
                f"/files/{folder_id}",
                params={"fields": "id, mimeType"},
            )
            return True
        except httpx.HTTPStatusError:
            return False
{%- else %}
"""Google Drive client - not configured."""
{%- endif %}
