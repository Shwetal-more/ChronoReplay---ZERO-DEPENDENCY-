"""
ChronoReplay version history.

Provides a high-level API for viewing the historical
versions of workspace files.

This module does not create its own database.
It uses EventStore's existing events and snapshots.

Only Python standard-library functionality is used.
"""

from dataclasses import dataclass
from typing import Optional

from src.store import EventStore
from src.snapshot import Snapshot


@dataclass
class FileVersion:
    """
    Represents one version of a workspace file.
    """

    version: int
    file_path: str
    event_id: str
    event_type: str
    timestamp: str
    snapshot_id: Optional[str]
    content_hash: Optional[str]
    user_id: Optional[str] = None

    def is_deleted(self) -> bool:
        """
        Return True if this version represents
        a deleted file.
        """

        return self.event_type == "file.deleted"

    def is_restorable(self) -> bool:
        """
        Return True if this version has a snapshot
        that can potentially be restored.
        """

        return (
            self.snapshot_id is not None
            and self.event_type in {
                "file.created",
                "file.modified",
                "file.restored",
            }
        )


class VersionHistory:
    """
    High-level interface for ChronoReplay file history.

    It converts low-level events and snapshots into
    file versions suitable for the UI.
    """

    FILE_EVENT_TYPES = {
        "file.created",
        "file.modified",
        "file.deleted",
        "file.restored",
    }

    SNAPSHOT_EVENT_TYPES = {
        "file.created",
        "file.modified",
        "file.restored",
    }

    def __init__(self, store: EventStore):
        """
        Create a VersionHistory instance.

        Args:
            store:
                Existing EventStore instance.
        """

        if not isinstance(store, EventStore):
            raise ValueError(
                "store must be an EventStore instance."
            )

        self.store = store

    # =========================================================
    # FILE LIST
    # =========================================================

    def list_files(self):
        """
        Return all workspace files that have appeared
        in the event history.

        Deleted files are included because they are still
        part of the historical record.
        """

        files = set()

        events = self.store.get_all_events()

        for event in events:

            if event.type not in self.FILE_EVENT_TYPES:
                continue

            file_path = event.data.get("file_path")

            if file_path:
                files.add(file_path)

        return sorted(files)

    # =========================================================
    # FILE HISTORY
    # =========================================================

    def get_file_history(self, file_path):
        """
        Return the complete version history of one file.

        Versions are returned in chronological order.
        """

        if not isinstance(file_path, str):
            raise ValueError(
                "file_path must be a string."
            )

        if not file_path.strip():
            raise ValueError(
                "file_path cannot be empty."
            )

        events = self.store.get_all_events()

        versions = []

        version_number = 0

        for event in events:

            if event.type not in self.FILE_EVENT_TYPES:
                continue

            event_file_path = event.data.get(
                "file_path"
            )

            if event_file_path != file_path:
                continue

            version_number += 1

            snapshot_id = event.data.get(
                "snapshot_id"
            )

            content_hash = event.data.get(
                "content_hash"
            )

            user_id = event.data.get("user_id")

            versions.append(
                FileVersion(
                    version=version_number,
                    file_path=file_path,
                    event_id=event.id,
                    event_type=event.type,
                    timestamp=event.timestamp,
                    snapshot_id=snapshot_id,
                    content_hash=content_hash,
                    user_id=user_id,
                )
            )

        return versions

    def get_user_history(self, user_id):
        """
        Return all file versions and activities performed by a specific user.
        """
        user_versions = []
        for file_path in self.list_files():
            for version in self.get_file_history(file_path):
                if version.user_id == user_id:
                    user_versions.append(version)
        user_versions.sort(key=lambda v: v.timestamp)
        return user_versions

    def get_content_snippet(self, file_path, version, num_lines=3):
        """
        Return a summary snippet (starting and ending lines) for a file version.
        """
        content = self.get_content(file_path, version)
        if content is None:
            return None
        lines = content.splitlines()
        total = len(lines)
        start_lines = lines[:num_lines]
        end_lines = lines[-num_lines:] if total > num_lines else []
        return {
            "start_lines": start_lines,
            "end_lines": end_lines,
            "total_lines": total,
            "char_count": len(content),
            "content": content,
        }

    # =========================================================
    # VERSION
    # =========================================================

    def get_version(
        self,
        file_path,
        version
    ):
        """
        Return one historical version of a file.

        Returns:
            FileVersion if found.
            None if the version does not exist.
        """

        if not isinstance(version, int):
            raise ValueError(
                "version must be an integer."
            )

        if isinstance(version, bool):
            raise ValueError(
                "version must be an integer."
            )

        if version <= 0:
            raise ValueError(
                "version must be greater than zero."
            )

        history = self.get_file_history(
            file_path
        )

        for item in history:

            if item.version == version:
                return item

        return None

    # =========================================================
    # LATEST VERSION
    # =========================================================

    def latest_version(self, file_path):
        """
        Return the latest version of a file.

        Returns:
            FileVersion if history exists.
            None otherwise.
        """

        history = self.get_file_history(
            file_path
        )

        if not history:
            return None

        return history[-1]

    # =========================================================
    # SNAPSHOT FOR VERSION
    # =========================================================

    def get_snapshot_for_version(
        self,
        file_path,
        version
    ):
        """
        Return the Snapshot associated with a version.

        Deleted versions do not have snapshots and therefore
        return None.
        """

        file_version = self.get_version(
            file_path,
            version
        )

        if file_version is None:
            return None

        if file_version.snapshot_id is None:
            return None

        snapshot = self.store.get_snapshot(
            file_version.snapshot_id
        )

        return snapshot

    # =========================================================
    # CONTENT
    # =========================================================

    def get_content(
        self,
        file_path,
        version
    ):
        """
        Return the file contents for a historical version.

        Returns:
            String content if a snapshot exists.
            None if the version does not contain a snapshot.
        """

        snapshot = self.get_snapshot_for_version(
            file_path,
            version
        )

        if snapshot is None:
            return None

        if not snapshot.verify_integrity():
            raise ValueError(
                "Snapshot integrity verification failed."
            )

        return snapshot.content

    def get_content_at_version(self, file_path, version):
        """
        Alias for get_content for backward and UI compatibility.
        """
        return self.get_content(file_path, version)

    def get_version_diff(self, file_path, version):
        """
        Return the delta/diff introduced by this specific version compared to previous version.
        """
        import difflib
        curr_content = self.get_content(file_path, version) or ""
        if version <= 1:
            return "\n".join([f"+ {line}" for line in curr_content.splitlines()[:50]])
        prev_content = self.get_content(file_path, version - 1) or ""
        diff_lines = list(difflib.unified_diff(
            prev_content.splitlines(),
            curr_content.splitlines(),
            fromfile=f"v{version-1}",
            tofile=f"v{version}",
            lineterm=""
        ))
        return "\n".join(diff_lines) if diff_lines else "(No textual changes detected in this version)"

    # =========================================================
    # TIMELINE
    # =========================================================

    def get_timeline(self):
        """
        Return the complete workspace file timeline.

        Each item contains:

            file_path
            version
            event_type
            timestamp
            snapshot_id
        """

        timeline = []

        for file_path in self.list_files():

            history = self.get_file_history(
                file_path
            )

            timeline.extend(history)

        timeline.sort(
            key=lambda item: item.timestamp
        )

        return timeline

    # =========================================================
    # RESTORABLE VERSIONS
    # =========================================================

    def get_restorable_versions(
        self,
        file_path
    ):
        """
        Return versions that contain snapshots
        and can be restored.
        """

        history = self.get_file_history(
            file_path
        )

        return [
            version
            for version in history
            if version.is_restorable()
        ]

    # =========================================================
    # SNAPSHOT HELPERS
    # =========================================================

    def get_snapshot(
        self,
        snapshot_id
    ):
        """
        Retrieve a snapshot by ID.

        This is a convenience wrapper around EventStore.
        """

        if not isinstance(snapshot_id, str):
            raise ValueError(
                "snapshot_id must be a string."
            )

        if not snapshot_id.strip():
            raise ValueError(
                "snapshot_id cannot be empty."
            )

        snapshot = self.store.get_snapshot(
            snapshot_id
        )

        if snapshot is None:
            return None

        if not isinstance(snapshot, Snapshot):
            raise ValueError(
                "Invalid snapshot returned by store."
            )

        return snapshot