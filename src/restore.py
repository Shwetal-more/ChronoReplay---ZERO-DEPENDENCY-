"""
ChronoReplay version history and restore functionality.

Provides the ability to:
- list historical versions of a file
- retrieve a specific snapshot
- view snapshot contents
- restore a historical snapshot
- recreate deleted files
- generate file.restored events

Only Python standard-library functionality is used.
"""

import os

from src.event import Event
from src.validator import EventValidator
from src.snapshot import Snapshot


class RestoreManager:
    """
    Handles historical file versions and restoration.

    Flow:

        Snapshot
            ↓
        Integrity Check
            ↓
        Restore File
            ↓
        file.restored Event
            ↓
        Validator
            ↓
        EventStore
    """

    def __init__(self, workspace_path, store):
        """
        Create a RestoreManager.

        Args:
            workspace_path:
                Root directory of the workspace.

            store:
                EventStore instance.
        """

        self.workspace_path = os.path.abspath(
            workspace_path
        )

        self.store = store

    # ---------------------------------------------------------
    # PATH UTILITIES
    # ---------------------------------------------------------

    def _full_path(self, relative_path):
        """
        Convert a workspace-relative path into
        an absolute filesystem path.
        """

        return os.path.join(
            self.workspace_path,
            relative_path
        )

    def _validate_relative_path(self, relative_path):
        """
        Validate that a path belongs to the workspace.

        This prevents restoration from escaping the
        workspace directory through paths such as:

            ../../important.txt
        """

        if not isinstance(relative_path, str):
            raise ValueError(
                "file_path must be a string."
            )

        if not relative_path.strip():
            raise ValueError(
                "file_path cannot be empty."
            )

        workspace = os.path.realpath(
            self.workspace_path
        )

        full_path = os.path.realpath(
            self._full_path(relative_path)
        )

        try:
            common = os.path.commonpath(
                [workspace, full_path]
            )
        except ValueError as exc:
            raise ValueError(
                "Invalid file path."
            ) from exc

        if common != workspace:
            raise ValueError(
                "File path must remain inside the workspace."
            )

        return full_path

    # ---------------------------------------------------------
    # VERSION HISTORY
    # ---------------------------------------------------------

    def get_versions(self, file_path):
        """
        Return all snapshots belonging to a file.

        Snapshots are returned in creation order.
        """

        self._validate_relative_path(
            file_path
        )

        return self.store.get_snapshots_for_file(
            file_path
        )

    def get_version(self, snapshot_id):
        """
        Retrieve one historical snapshot.

        Returns:
            Snapshot if found.
            None if not found.
        """

        if not isinstance(snapshot_id, str):
            raise ValueError(
                "snapshot_id must be a string."
            )

        if not snapshot_id.strip():
            raise ValueError(
                "snapshot_id cannot be empty."
            )

        return self.store.get_snapshot(
            snapshot_id
        )

    def view_version(self, snapshot_id):
        """
        Return the contents of a historical version.

        Returns:
            Snapshot content.

        Raises:
            ValueError if the snapshot does not exist.
        """

        snapshot = self.get_version(
            snapshot_id
        )

        if snapshot is None:
            raise ValueError(
                f"Snapshot '{snapshot_id}' was not found."
            )

        if not snapshot.verify_integrity():
            raise ValueError(
                f"Snapshot '{snapshot_id}' failed integrity verification."
            )

        return snapshot.content

    # ---------------------------------------------------------
    # RESTORE
    # ---------------------------------------------------------

    def _merge_current_with_historical(
        self,
        current_content,
        snapshot_content,
        previous_line_count=None,
        selected_line_indexes=None,
    ):
        """
        Merge the current workspace with only the historical lines that are
        missing from the active file, or with a user-selected subset when
        explicitly chosen.
        """
        current_lines = (current_content or "").splitlines()
        historical_lines = snapshot_content.splitlines()

        if previous_line_count is not None:
            if isinstance(previous_line_count, bool) or not isinstance(previous_line_count, int):
                raise ValueError("previous_line_count must be an integer or None.")
            if previous_line_count < 0:
                raise ValueError("previous_line_count must be zero or greater.")
            historical_lines = historical_lines[-previous_line_count:]

        if selected_line_indexes is not None:
            if isinstance(selected_line_indexes, int):
                selected_line_indexes = [selected_line_indexes]
            if not isinstance(selected_line_indexes, (list, tuple)):
                raise ValueError("selected_line_indexes must be a list, tuple, or integer.")
            selected_line_indexes = sorted({idx for idx in selected_line_indexes if isinstance(idx, int)})
            chosen_lines = []
            for idx in selected_line_indexes:
                if 0 <= idx < len(historical_lines):
                    chosen_lines.append(historical_lines[idx])
        else:
            current_counts = {}
            for line in current_lines:
                current_counts[line] = current_counts.get(line, 0) + 1

            historical_counts = {}
            for line in historical_lines:
                historical_counts[line] = historical_counts.get(line, 0) + 1

            chosen_lines = []
            for line in historical_lines:
                if current_counts.get(line, 0) < historical_counts.get(line, 0):
                    chosen_lines.append(line)

        if not chosen_lines:
            return (current_content or "").rstrip("\n")

        current_text = (current_content or "").rstrip("\n")
        if not current_text:
            return "\n".join(chosen_lines)

        return current_text + "\n\n" + "\n".join(chosen_lines)

    def restore(
        self,
        snapshot_id,
        user_id=None,
        merge_with_current=False,
        previous_line_count=None,
        selected_line_indexes=None,
    ):
        """
        Restore a historical snapshot into the workspace.

        The target file is created if it no longer exists.

        A file.restored event is generated after the
        restoration succeeds.

        Args:
            snapshot_id:
                ID of snapshot to restore.
            user_id:
                Optional ID of user performing the restoration.
            merge_with_current:
                When True, preserve the existing current file and append the
                selected historical lines instead of overwriting the file.
            previous_line_count:
                Number of trailing lines from the historical snapshot to keep
                when merging. If None, all historical lines are used.
            selected_line_indexes:
                Optional indexes from the historical snapshot to append when
                merge_with_current is enabled.

        Returns:
            The generated Event object.
        """

        snapshot = self.get_version(
            snapshot_id
        )

        if snapshot is None:
            raise ValueError(
                f"Snapshot '{snapshot_id}' was not found."
            )

        if not snapshot.verify_integrity():
            raise ValueError(
                f"Snapshot '{snapshot_id}' failed integrity verification."
            )

        full_path = self._validate_relative_path(
            snapshot.file_path
        )

        # Create parent directories when restoring
        # a file whose directory was also removed.
        parent_directory = os.path.dirname(
            full_path
        )

        if parent_directory:
            os.makedirs(
                parent_directory,
                exist_ok=True
            )

        restored_content = snapshot.content
        if merge_with_current and os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8", newline="") as file:
                current_content = file.read()
            restored_content = self._merge_current_with_historical(
                current_content,
                snapshot.content,
                previous_line_count=previous_line_count,
                selected_line_indexes=selected_line_indexes,
            )

        try:
            with open(
                full_path,
                "w",
                encoding="utf-8",
                newline=""
            ) as file:

                file.write(
                    restored_content
                )

        except OSError as exc:
            raise ValueError(
                f"Unable to restore file: "
                f"{snapshot.file_path}"
            ) from exc

        # Create the restoration event only after
        # the file has been successfully written.
        event_data = {
            "file_path": snapshot.file_path,
            "snapshot_id": snapshot.snapshot_id,
            "content_hash": snapshot.content_hash,
        }
        if user_id:
            event_data["user_id"] = user_id
        if merge_with_current:
            event_data["merge_with_current"] = True
            event_data["previous_line_count"] = previous_line_count
            if selected_line_indexes is not None:
                event_data["selected_line_indexes"] = list(selected_line_indexes)

        event = Event.create(
            "file.restored",
            event_data
        )

        # Validate before persistence.
        EventValidator.validate(
            event
        )

        # Persist the event.
        self.store.save(
            event
        )

        return event

    def get_version_snippet(self, snapshot_id, num_lines=3):
        """
        Return a summary snippet (starting lines and ending lines)
        for a historical version.
        """
        content = self.view_version(snapshot_id)
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

    # ---------------------------------------------------------
    # RESTORE BY VERSION NUMBER
    # ---------------------------------------------------------

    def restore_version(
        self,
        file_path,
        version_number,
        merge_with_current=False,
        previous_line_count=None,
        selected_line_indexes=None,
    ):
        """
        Restore a file using its position in version history.

        Version numbering is one-based:

            1 = first snapshot
            2 = second snapshot
            3 = third snapshot

        This is useful for a UI displaying:

            #12 CREATED
            #13 MODIFIED
            #14 MODIFIED

        Returns:
            Generated file.restored Event.
        """

        if (
            isinstance(version_number, bool)
            or not isinstance(version_number, int)
        ):
            raise ValueError(
                "version_number must be an integer."
            )

        if version_number <= 0:
            raise ValueError(
                "version_number must be greater than zero."
            )

        # Look up in VersionHistory to respect full event-version sequence
        try:
            from src.history import VersionHistory
            vh = VersionHistory(self.store)
            f_ver = vh.get_version(file_path, version_number)
            if f_ver and f_ver.snapshot_id:
                return self.restore(
                    f_ver.snapshot_id,
                    merge_with_current=merge_with_current,
                    previous_line_count=previous_line_count,
                    selected_line_indexes=selected_line_indexes,
                )
        except Exception:
            pass

        versions = self.get_versions(
            file_path
        )

        if version_number > len(versions):
            raise ValueError(
                f"Version {version_number} does not exist "
                f"for '{file_path}'."
            )

        snapshot = versions[
            version_number - 1
        ]

        return self.restore(
            snapshot.snapshot_id,
            merge_with_current=merge_with_current,
            previous_line_count=previous_line_count,
            selected_line_indexes=selected_line_indexes,
        )

    # ---------------------------------------------------------
    # LATEST VERSION
    # ---------------------------------------------------------

    def get_latest_version(self, file_path):
        """
        Return the newest snapshot for a file.

        Returns:
            Snapshot if history exists.
            None otherwise.
        """

        versions = self.get_versions(
            file_path
        )

        if not versions:
            return None

        return versions[-1]

    # ---------------------------------------------------------
    # CONVENIENCE METHODS
    # ---------------------------------------------------------

    def file_has_history(self, file_path):
        """
        Return True if the file has at least one
        historical snapshot.
        """

        return bool(
            self.get_versions(file_path)
        )

    def version_count(self, file_path):
        """
        Return the number of historical snapshots
        belonging to a file.
        """

        return len(
            self.get_versions(file_path)
        )