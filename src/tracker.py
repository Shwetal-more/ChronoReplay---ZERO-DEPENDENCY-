"""
ChronoReplay automatic workspace tracker.

Connects the filesystem watcher with snapshots,
events, validation and persistent storage.

Only Python standard-library modules are used.
"""

import os
import uuid

from src.event import Event
from src.validator import EventValidator
from src.snapshot import Snapshot
from src.watcher import FileWatcher


class WorkspaceTracker:
    """
    Coordinates automatic file tracking.

    Flow:

        FileWatcher
             ↓
        File change
             ↓
        Snapshot
             ↓
        Event
             ↓
        Validator
             ↓
        Store
    """

    # Files and folders that ChronoReplay itself creates.
    # These must NOT be tracked as user workspace files.
    IGNORED_FILES = {
        "chronoreplay.db",
        "events.db",
    }

    IGNORED_DIRECTORIES = {
        ".git",
        "__pycache__",
    }

    IGNORED_EXTENSIONS = {
        ".db",
        ".sqlite",
        ".sqlite3",
    }

    def __init__(
        self,
        workspace_path,
        store,
        interval=1.0
    ):
        """
        Create a workspace tracker.
        """

        self.workspace_path = os.path.abspath(
            workspace_path
        )

        self.store = store

        self.watcher = FileWatcher(
            self.workspace_path,
            interval
        )

    def _full_path(self, relative_path):
        """
        Convert a workspace-relative path
        into an absolute path.
        """

        return os.path.join(
            self.workspace_path,
            relative_path
        )

    def _is_ignored(self, relative_path):
        """
        Determine whether a workspace path should
        be ignored by ChronoReplay.

        We ignore:
        - ChronoReplay's own database files
        - SQLite files
        - Git metadata
        - Python cache directories
        """

        normalized = relative_path.replace(
            "\\",
            "/"
        )

        filename = os.path.basename(
            normalized
        )

        # Ignore known internal files.
        if filename in self.IGNORED_FILES:
            return True

        # Ignore database files.
        extension = os.path.splitext(
            filename
        )[1].lower()

        if extension in self.IGNORED_EXTENSIONS:
            return True

        # Ignore internal directories.
        parts = normalized.split("/")

        for part in parts:
            if part in self.IGNORED_DIRECTORIES:
                return True

        return False

    def _read_file(self, relative_path):
        """
        Read a text file from the workspace.

        Binary/internal files are rejected instead of
        crashing the tracker.
        """

        if self._is_ignored(relative_path):
            raise ValueError(
                f"Ignored file: {relative_path}"
            )

        full_path = self._full_path(
            relative_path
        )

        try:
            with open(
                full_path,
                "r",
                encoding="utf-8"
            ) as file:

                return file.read()

        except (
            OSError,
            UnicodeDecodeError
        ) as exc:

            raise ValueError(
                f"Unable to read file: {relative_path}"
            ) from exc

    def _create_snapshot(self, relative_path):
        """
        Read the current file contents and create
        a Snapshot object.
        """

        content = self._read_file(
            relative_path
        )

        snapshot_id = str(
            uuid.uuid4()
        )

        return Snapshot.create(
            snapshot_id,
            relative_path,
            content
        )

    def _publish_event(self, event):
        """
        Validate and store an event.
        """

        EventValidator.validate(
            event
        )

        self.store.save(
            event
        )

        return event

    def _handle_created(self, relative_path):
        """
        Handle a newly created file.
        """

        if self._is_ignored(relative_path):
            return None

        snapshot = self._create_snapshot(
            relative_path
        )

        event = Event.create(
            "file.created",
            {
                "file_path": relative_path,
                "snapshot_id": snapshot.snapshot_id,
                "content_hash": snapshot.content_hash,
            }
        )

        return self._publish_event(
            event
        )

    def _handle_modified(self, relative_path):
        """
        Handle a modified file.
        """

        if self._is_ignored(relative_path):
            return None

        snapshot = self._create_snapshot(
            relative_path
        )

        event = Event.create(
            "file.modified",
            {
                "file_path": relative_path,
                "snapshot_id": snapshot.snapshot_id,
                "content_hash": snapshot.content_hash,
            }
        )

        return self._publish_event(
            event
        )

    def _handle_deleted(self, relative_path):
        """
        Handle a deleted file.

        A deleted file cannot be read, so we do not
        create a new snapshot.
        """

        if self._is_ignored(relative_path):
            return None

        event = Event.create(
            "file.deleted",
            {
                "file_path": relative_path,
            }
        )

        return self._publish_event(
            event
        )

    def process_changes(self):
        """
        Detect and process current workspace changes.

        Returns:
            List of generated events.
        """

        changes = self.watcher.detect_changes()

        events = []

        for path in changes["created"]:

            event = self._handle_created(
                path
            )

            if event is not None:
                events.append(event)

        for path in changes["modified"]:

            event = self._handle_modified(
                path
            )

            if event is not None:
                events.append(event)

        for path in changes["deleted"]:

            event = self._handle_deleted(
                path
            )

            if event is not None:
                events.append(event)

        return events

    def initialize(self):
        """
        Record the initial state of the workspace.

        Existing files do not generate events.
        """

        return self.watcher.initialize()