"""
Workspace manager for ChronoReplay.

Provides safe file operations inside a designated workspace.

Only Python standard-library functionality is used.
"""
from pathlib import Path
import hashlib

from src.snapshot import Snapshot
from src.event import Event


class WorkspaceManager:
    """
    Manages files inside a ChronoReplay workspace.
    """

    def __init__(self, workspace_path):
        """
        Create a workspace manager.
        """

        self.workspace_path = Path(
            workspace_path
        ).resolve()

        self.workspace_path.mkdir(
            parents=True,
            exist_ok=True
        )

    def _safe_path(self, file_path):
        """
        Convert a user-provided path into a safe
        workspace-relative path.

        Prevents accessing files outside the workspace.
        """

        requested_path = (
            self.workspace_path / file_path
        ).resolve()

        try:
            requested_path.relative_to(
                self.workspace_path
            )

        except ValueError:
            raise ValueError(
                "File path must remain inside the workspace."
            )

        return requested_path

    def create_file(
        self,
        file_path,
        content=""
    ):
        """
        Create a new file.
        """

        path = self._safe_path(
            file_path
        )

        if path.exists():
            raise ValueError(
                "File already exists."
            )

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        path.write_text(
            content,
            encoding="utf-8"
        )

        return self.create_snapshot(
            file_path
        )

    def read_file(self, file_path):
        """
        Read a file from the workspace.
        """

        path = self._safe_path(
            file_path
        )

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        return path.read_text(
            encoding="utf-8"
        )

    def modify_file(
        self,
        file_path,
        content
    ):
        """
        Replace the contents of an existing file.
        """

        path = self._safe_path(
            file_path
        )

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        path.write_text(
            content,
            encoding="utf-8"
        )

        return self.create_snapshot(
            file_path
        )

    def delete_file(self, file_path):
        """
        Delete a file from the workspace.
        """

        path = self._safe_path(
            file_path
        )

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        path.unlink()

    def create_snapshot(self, file_path):
        """
        Create a Snapshot from the current file contents.
        """

        content = self.read_file(
            file_path
        )

        snapshot_id = hashlib.sha256(
            (
                file_path
                + "\n"
                + content
            ).encode("utf-8")
        ).hexdigest()[:16]

        return Snapshot.create(
            snapshot_id=snapshot_id,
            file_path=file_path,
            content=content,
        )

    def restore_snapshot(
        self,
        snapshot: Snapshot
    ):
        """
        Restore a file from a Snapshot.
        """

        if not isinstance(
            snapshot,
            Snapshot
        ):
            raise ValueError(
                "snapshot must be a Snapshot."
            )

        path = self._safe_path(
            snapshot.file_path
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        path.write_text(
            snapshot.content,
            encoding="utf-8"
        )

        return True

    def create_file_event(
        self,
        snapshot: Snapshot
    ) -> Event:
        """
        Create a ChronoReplay event for a new file.
        """

        return Event.create(
            "file.created",
            {
                "file_path": snapshot.file_path,
                "snapshot_id": snapshot.snapshot_id,
                "content_hash": snapshot.content_hash,
            },
        )

    def modify_file_event(
        self,
        snapshot: Snapshot
    ) -> Event:
        """
        Create a ChronoReplay event for a modified file.
        """

        return Event.create(
            "file.modified",
            {
                "file_path": snapshot.file_path,
                "snapshot_id": snapshot.snapshot_id,
                "content_hash": snapshot.content_hash,
            },
        )

    def delete_file_event(
        self,
        file_path: str
    ) -> Event:
        """
        Create a ChronoReplay event for a deleted file.
        """

        return Event.create(
            "file.deleted",
            {
                "file_path": file_path,
            },
        )

    def restore_file_event(
        self,
        snapshot: Snapshot
    ) -> Event:
        """
        Create a ChronoReplay event for a restored file.
        """

        return Event.create(
            "file.restored",
            {
                "file_path": snapshot.file_path,
                "snapshot_id": snapshot.snapshot_id,
                "content_hash": snapshot.content_hash,
            },
        )