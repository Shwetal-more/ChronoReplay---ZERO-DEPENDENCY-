"""
Snapshot functionality for ChronoReplay.

A Snapshot represents one historical version of a file.

Only Python standard-library functionality is used.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib


@dataclass
class Snapshot:
    """
    Represents one saved version of a file.
    """

    snapshot_id: str
    file_path: str
    content: str
    timestamp: str
    content_hash: str

    @classmethod
    def create(
        cls,
        snapshot_id: str,
        file_path: str,
        content: str,
    ):
        """
        Create a new Snapshot.

        The content hash is automatically calculated.
        """

        if not isinstance(snapshot_id, str):
            raise ValueError(
                "snapshot_id must be a string."
            )

        if not snapshot_id.strip():
            raise ValueError(
                "snapshot_id cannot be empty."
            )

        if not isinstance(file_path, str):
            raise ValueError(
                "file_path must be a string."
            )

        if not file_path.strip():
            raise ValueError(
                "file_path cannot be empty."
            )

        if not isinstance(content, str):
            raise ValueError(
                "content must be a string."
            )

        content_hash = hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        return cls(
            snapshot_id=snapshot_id,
            file_path=file_path,
            content=content,
            timestamp=timestamp,
            content_hash=content_hash,
        )

    def verify_integrity(self) -> bool:
        """
        Verify that the stored content still matches
        its original hash.
        """

        current_hash = hashlib.sha256(
            self.content.encode("utf-8")
        ).hexdigest()

        return current_hash == self.content_hash