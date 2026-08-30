"""
ChronoReplay workspace manager and tracker.

Manages files inside a ChronoReplay workspace, tracks real files,
and creates file events + snapshots.

Only Python standard-library functionality is used.
"""

import hashlib
import os
from pathlib import Path
import uuid

from src.event import Event
from src.snapshot import Snapshot
from src.validator import EventValidator


class WorkspaceManager:
    """
    Manages and tracks files inside a ChronoReplay workspace.
    """

    def __init__(
        self,
        workspace_path,
        store=None
    ):
        """
        Create a workspace manager with optional EventStore.
        """
        self.workspace_path = os.path.abspath(
            str(workspace_path)
        )
        self._path_obj = Path(self.workspace_path).resolve()
        self._path_obj.mkdir(
            parents=True,
            exist_ok=True
        )
        self.store = store

    # =========================================================
    # FILE HASH
    # =========================================================

    @staticmethod
    def _hash(content):
        return hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

    # =========================================================
    # PATH SAFETY
    # =========================================================

    def _safe_path(self, file_path):
        """
        Convert a user-provided path into a safe
        workspace-relative path.

        Prevents accessing files outside the workspace.
        """
        requested_path = (
            self._path_obj / file_path
        ).resolve()

        try:
            requested_path.relative_to(
                self._path_obj
            )
        except ValueError:
            raise ValueError(
                "File path must remain inside the workspace."
            )

        return requested_path

    # =========================================================
    # BASIC FILE OPERATIONS
    # =========================================================

    def create_file(
        self,
        file_path,
        content=""
    ):
        """
        Create a new file in workspace.
        """
        path = self._safe_path(file_path)

        if path.exists():
            raise ValueError("File already exists.")

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        path.write_text(
            content,
            encoding="utf-8"
        )

        return self.create_snapshot(file_path)

    def read_file(self, file_path):
        """
        Read a file from the workspace.
        """
        path = self._safe_path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        return path.read_text(encoding="utf-8")

    def modify_file(
        self,
        file_path,
        content
    ):
        """
        Replace the contents of an existing file.
        """
        path = self._safe_path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        path.write_text(
            content,
            encoding="utf-8"
        )

        return self.create_snapshot(file_path)

    def delete_file(self, file_path):
        """
        Delete a file from the workspace.
        """
        path = self._safe_path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        path.unlink()

    def create_snapshot(self, file_path):
        """
        Create a Snapshot from the current file contents.
        """
        content = self.read_file(file_path)

        snapshot_id = hashlib.sha256(
            (file_path + "\n" + content).encode("utf-8")
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
        if not isinstance(snapshot, Snapshot):
            raise ValueError("snapshot must be a Snapshot.")

        path = self._safe_path(snapshot.file_path)

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
        snapshot: Snapshot,
        user_id: str = None,
    ) -> Event:
        data = {
            "file_path": snapshot.file_path,
            "snapshot_id": snapshot.snapshot_id,
            "content_hash": snapshot.content_hash,
            "workspace_path": self.workspace_path,
        }
        if user_id:
            data["user_id"] = user_id
        return Event.create(
            "file.created",
            data,
        )

    def modify_file_event(
        self,
        snapshot: Snapshot,
        user_id: str = None,
    ) -> Event:
        data = {
            "file_path": snapshot.file_path,
            "snapshot_id": snapshot.snapshot_id,
            "content_hash": snapshot.content_hash,
            "workspace_path": self.workspace_path,
        }
        if user_id:
            data["user_id"] = user_id
        return Event.create(
            "file.modified",
            data,
        )

    def delete_file_event(
        self,
        file_path: str,
        user_id: str = None,
    ) -> Event:
        data = {
            "file_path": file_path,
            "workspace_path": self.workspace_path,
        }
        if user_id:
            data["user_id"] = user_id
        return Event.create(
            "file.deleted",
            data,
        )

    def restore_file_event(
        self,
        snapshot: Snapshot,
        user_id: str = None,
    ) -> Event:
        data = {
            "file_path": snapshot.file_path,
            "snapshot_id": snapshot.snapshot_id,
            "content_hash": snapshot.content_hash,
            "workspace_path": self.workspace_path,
        }
        if user_id:
            data["user_id"] = user_id
        return Event.create(
            "file.restored",
            data,
        )

    # =========================================================
    # SCAN WORKSPACE
    # =========================================================

    def scan(self):
        """
        Scan workspace directory and return relative paths of files.
        Only files inside this workspace directory are scanned.
        """
        files = []
        ignored_dirs = {
            ".git",
            "__pycache__",
            ".pytest_cache",
            ".venv",
            "venv",
            "node_modules",
            "dist",
            "build",
            ".next",
            ".cache",
            ".turbo",
            ".idea",
            ".vscode",
        }

        for root, directories, filenames in os.walk(
            self.workspace_path
        ):
            directories[:] = [
                directory
                for directory in directories
                if directory not in ignored_dirs
                and not directory.startswith(".")
            ]

            for filename in filenames:
                if (
                    filename.startswith(".")
                    or filename.endswith(".pyc")
                    or filename in ("chronoreplay.db", "events.db")
                ):
                    continue

                full_path = os.path.join(
                    root,
                    filename
                )

                relative_path = os.path.relpath(
                    full_path,
                    self.workspace_path
                )

                # Normalize path separators across platforms (Windows / Unix)
                normalized_path = relative_path.replace("\\", "/")
                files.append(
                    normalized_path
                )

        return sorted(files)

    # =========================================================
    # TRACK FILE
    # =========================================================

    def track_file(
        self,
        relative_path,
        user_id=None
    ):
        """
        Track a single file and store snapshot and event if modified.
        """
        if self.store is None:
            raise ValueError("EventStore is required to track files.")

        normalized_rel_path = relative_path.replace("\\", "/")

        full_path = os.path.join(
            self.workspace_path,
            normalized_rel_path
        )

        if not os.path.isfile(full_path):
            raise ValueError(
                f"File does not exist: {normalized_rel_path}"
            )

        with open(
            full_path,
            "r",
            encoding="utf-8"
        ) as file:
            content = file.read()

        content_hash = self._hash(
            content
        )

        history = self.store.get_snapshots_for_file(
            normalized_rel_path
        )

        # -----------------------------------------------------
        # FIRST VERSION
        # -----------------------------------------------------

        if not history:
            snapshot = Snapshot.create(
                snapshot_id=str(uuid.uuid4()),
                file_path=normalized_rel_path,
                content=content,
            )

            self.store.save_snapshot(
                snapshot
            )

            event = self.create_file_event(
                snapshot,
                user_id=user_id
            )

            EventValidator.validate(
                event
            )

            self.store.save(
                event
            )

            return event

        # -----------------------------------------------------
        # CHECK WHETHER MODIFIED
        # -----------------------------------------------------

        latest = history[-1]

        if latest.content_hash == content_hash:
            return None

        snapshot = Snapshot.create(
            snapshot_id=str(uuid.uuid4()),
            file_path=normalized_rel_path,
            content=content,
        )

        self.store.save_snapshot(
            snapshot
        )

        event = self.modify_file_event(
            snapshot,
            user_id=user_id
        )

        EventValidator.validate(
            event
        )

        self.store.save(
            event
        )

        return event

    def get_user_file_activity(self, user_id):
        """
        Return all workspace events and activities performed by a specific user.
        """
        if not self.store:
            return []
        events = self.store.get_events_for_user(user_id)
        file_events = [e for e in events if e.type.startswith("file.")]
        return file_events

    # =========================================================
    # TRACK ENTIRE WORKSPACE
    # =========================================================

    def track_all(self):
        """
        Scan and track all files in workspace.
        """
        return self.scan_and_record_changes()

    def get_workspace_tracked_files(self):
        """
        Return relative file paths that were explicitly recorded in this workspace path,
        or are physically present on disk in this directory.
        """
        tracked = set()
        if self.store:
            for event in self.store.get_all():
                if event.type.startswith("file.") and "file_path" in event.data:
                    ev_ws = event.data.get("workspace_path")
                    norm_path = event.data["file_path"].replace("\\", "/")

                    # If tagged with a workspace path, only include if it matches this workspace
                    if ev_ws is not None:
                        if os.path.abspath(str(ev_ws)) == self.workspace_path:
                            tracked.add(norm_path)
                    else:
                        # Legacy untagged file: only associate with this workspace if physically on disk
                        full_path = os.path.join(self.workspace_path, norm_path)
                        if os.path.isfile(full_path):
                            tracked.add(norm_path)

        return tracked

    def scan_and_record_changes(self):
        """
        Scan workspace, compare with historical snapshots,
        detect created, modified, and deleted files,
        save snapshots & events to chronoreplay.db, and return summary.
        """
        created = 0
        modified = 0
        unchanged = 0
        deleted = 0

        current_files = set(self.scan())

        for file_path in sorted(current_files):
            event = self.track_file(file_path)

            if event is None:
                unchanged += 1
                continue

            if event.type == "file.created":
                created += 1
            elif event.type == "file.modified":
                modified += 1

        # Check for deleted files (files previously tracked in this workspace that are no longer present on disk)
        if self.store:
            workspace_tracked = self.get_workspace_tracked_files()
            for file_path in sorted(workspace_tracked):
                if file_path not in current_files:
                    # Check if already marked deleted
                    all_events = [
                        e for e in self.store.get_events_for_file(file_path)
                        if e.data.get("workspace_path") is None or os.path.abspath(str(e.data.get("workspace_path"))) == self.workspace_path
                    ]
                    if all_events and all_events[-1].type != "file.deleted":
                        del_evt = self.delete_file_event(file_path)
                        EventValidator.validate(del_evt)
                        self.store.save(del_evt)
                        deleted += 1

        return {
            "created": created,
            "modified": modified,
            "deleted": deleted,
            "unchanged": unchanged,
            "total_scanned": len(current_files),
        }

    def get_workspace_files_with_status(self):
        """
        Return list of workspace files with their status.
        Only files belonging to this selected workspace (currently on disk in this folder,
        or previously recorded and deleted from this workspace folder) are returned.
        """
        current_files = set(self.scan())
        tracked_files = self.get_workspace_tracked_files()

        all_paths = sorted(current_files | tracked_files)
        results = []

        for path in all_paths:
            full_path = os.path.join(self.workspace_path, path)
            is_on_disk = os.path.isfile(full_path)

            if self.store:
                history = self.store.get_snapshots_for_file(path)
                events = [
                    e for e in self.store.get_events_for_file(path)
                    if e.data.get("workspace_path") is None or os.path.abspath(str(e.data.get("workspace_path"))) == self.workspace_path
                ]
            else:
                history = []
                events = []

            # If the file is not on disk and has no events in this workspace, skip it
            if not is_on_disk and not events:
                continue

            if not history:
                status = "Untracked" if is_on_disk else "Deleted"
            elif not is_on_disk:
                status = "Deleted"
            else:
                # Compare disk hash with latest snapshot hash
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        curr_content = f.read()
                    curr_hash = self._hash(curr_content)
                    if curr_hash == history[-1].content_hash:
                        if len(history) == 1:
                            status = "Created"
                        else:
                            status = "Unchanged"
                    else:
                        status = "Modified"
                except Exception:
                    status = "Modified"

            results.append({
                "file_path": path,
                "status": status,
                "version_count": len(history),
                "event_count": len(events),
                "is_on_disk": is_on_disk,
            })

        return results
