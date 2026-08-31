#!/usr/bin/env python3
"""
=============================================================================
ChronoReplay — ZERO-DEPENDENCY COMPLETE SINGLE-FILE APPLICATION
=============================================================================
Zero-Dependency Event-Sourced Audit, State Time-Machine & Workspace Recovery Engine.

This single file contains the entire ChronoReplay application:
- Immutable Event Definitions & Validation Engine
- Append-Only SQLite Event Store & SHA-256 Checksums
- Deterministic State Engine & Invariant Diagnostics
- Bidirectional Time Machine Replay & Append-Only Restoration
- Workspace File Snapshotting, difflib Unified Line Diffs & Rollback
- Event Simulator with Automatic User/Order Context Resolution
- Native Dark-Themed Tkinter GUI Dashboard

Standard Library Only (Zero Third-Party Dependencies):
dataclasses, sqlite3, hashlib, difflib, json, uuid, datetime, copy, os, pathlib, time, typing, tkinter

Usage:
    python3 chronoreplay-single.py
    python3 chronoreplay-single.py --cli
=============================================================================
"""

# Global Standard Library Imports
import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:
    tk = None
    filedialog = None
    messagebox = None
    ttk = None
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import uuid



# ===========================================================================
# MODULE: event.py
# ===========================================================================

"""
ChronoReplay event model.

Events are immutable historical facts.
ChronoReplay automatically assigns user IDs and order IDs
when the simulator does not provide them.

Only Python standard-library modules are used.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import uuid


@dataclass
class Event:
    """
    Represents one event in ChronoReplay.
    """

    id: str
    version: int
    type: str
    timestamp: str
    data: dict

    def __post_init__(self):
        self._validate()

    def _validate(self):
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Event id must be a non-empty string.")

        if not isinstance(self.version, int) or self.version < 1:
            raise ValueError("Event version must be a positive integer.")

        if not isinstance(self.type, str) or not self.type.strip():
            raise ValueError("Event type must be a non-empty string.")

        if not isinstance(self.timestamp, str) or not self.timestamp.strip():
            raise ValueError("Event timestamp must be a non-empty string.")

        if not isinstance(self.data, dict):
            raise ValueError("Event data must be a dictionary.")

    # =========================================================
    # ID GENERATORS
    # =========================================================

    @staticmethod
    def generate_user_id(seq: int = None):
        """
        ChronoReplay assigns user IDs.

        Users never need to type a user ID manually.
        """
        if seq is not None and isinstance(seq, int):
            return f"USR-{seq:04d}"
        return "USR-" + uuid.uuid4().hex[:8].upper()

    @staticmethod
    def generate_order_id(seq: int = None):
        """
        ChronoReplay assigns order IDs.

        Users never need to type an order ID manually.
        """
        if seq is not None and isinstance(seq, int):
            return f"ORD-{seq:04d}"
        return "ORD-" + uuid.uuid4().hex[:8].upper()

    @staticmethod
    def generate_event_id():
        """
        Generate a unique event ID.
        """
        return str(uuid.uuid4())

    # =========================================================
    # EVENT CREATION
    # =========================================================

    @classmethod
    def create(
        cls,
        event_type: str,
        data: dict,
        user_id=None,
        order_id=None,
    ) -> "Event":
        """
        Create a new event.

        IDs are automatically assigned.

        Rules:

        user.created
            -> creates a new user automatically

        order.created
            -> creates a new order automatically
            -> attaches it to the supplied/current user

        payment.completed
            -> attaches to the supplied/current user

        Other user-related events
            -> attach to supplied user
        """

        if not isinstance(data, dict):
            raise ValueError("Event data must be a dictionary.")

        data = dict(data)

        if user_id:
            data["user_id"] = user_id
        if order_id:
            data["order_id"] = order_id

        return cls(
            id=cls.generate_event_id(),
            version=1,
            type=event_type,
            timestamp=datetime.now().astimezone().isoformat(),
            data=data,
        )

    # =========================================================
    # SERIALIZATION
    # =========================================================

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            separators=(",", ":"),
            sort_keys=True,
        )

    # =========================================================
    # DESERIALIZATION
    # =========================================================

    @classmethod
    def from_dict(cls, value: dict) -> "Event":

        if not isinstance(value, dict):
            raise ValueError("Input must be a dictionary.")

        required_fields = {
            "id",
            "version",
            "type",
            "timestamp",
            "data",
        }

        missing = required_fields - value.keys()

        if missing:
            raise ValueError(
                f"Missing required fields: {', '.join(sorted(missing))}"
            )

        return cls(
            id=value["id"],
            version=value["version"],
            type=value["type"],
            timestamp=value["timestamp"],
            data=value["data"],
        )

    @classmethod
    def from_json(cls, value: str) -> "Event":

        try:
            data = json.loads(value)

        except json.JSONDecodeError as exc:
            raise ValueError("Invalid event JSON") from exc

        return cls.from_dict(data)

# ===========================================================================
# MODULE: validator.py
# ===========================================================================

"""
Event validator module.

This module checks whether an event follows
the rules defined in the ChronoReplay event schema.

Only Python standard-library functionality is used.
"""



class EventValidator:
    """
    Validates ChronoReplay events.

    The validator checks:

    - whether the event type is supported
    - whether required fields are present
    - whether field values have the correct type
    - whether values are within expected ranges
    """

    supported_event_types = {
        "user.created",
        "profile.updated",
        "status.changed",
        "balance.added",
        "payment.completed",
        "order.created",
        "order.updated",
        "user.deleted",

        # ChronoReplay workspace events
        "file.created",
        "file.modified",
        "file.deleted",
        "file.restored",

        # State recovery events
        "state.restored",
    }

    VALID_STATUS_VALUES = {
        "active",
        "inactive",
        "suspended",
    }

    VALID_PAYMENT_METHODS = {
        "UPI",
        "CARD",
        "CASH",
    }

    VALID_ORDER_STATUSES = {
        "pending",
        "confirmed",
        "shipped",
        "completed",
        "paid",
    }

    @classmethod
    def validate(cls, event: Event) -> None:
        """
        Validate an Event.

        If valid:
            returns None

        If invalid:
            raises ValueError.
        """

        if not isinstance(event, Event):
            raise ValueError(
                "Invalid event object. "
                "Must be an instance of Event class."
            )

        # IMPORTANT:
        # Event uses .type, not .event_type.
        if event.type not in cls.supported_event_types:
            raise ValueError(
                f"Unsupported event type: {event.type}"
            )

        validators = {
            "user.created":
                cls._validate_user_created,

            "profile.updated":
                cls._validate_profile_updated,

            "status.changed":
                cls._validate_status_changed,

            "balance.added":
                cls._validate_balance_added,

            "payment.completed":
                cls._validate_payment_completed,

            "order.created":
                cls._validate_order_created,

            "order.updated":
                cls._validate_order_updated,

            "user.deleted":
                cls._validate_user_deleted,

            # ChronoReplay file events
            "file.created":
                cls._validate_file_created,

            "file.modified":
                cls._validate_file_modified,

            "file.deleted":
                cls._validate_file_deleted,

            "file.restored":
                cls._validate_file_restored,

            # ChronoReplay state recovery
            "state.restored":
                cls._validate_state_restored,
        }

        validators[event.type](
            event.data
        )

    @staticmethod
    def _require_string(
        data: dict,
        field: str
    ) -> None:
        """
        Ensure a field exists and contains
        a non-empty string.
        """

        if field not in data:
            raise ValueError(
                f"missing required field: {field}"
            )

        if not isinstance(
            data[field],
            str
        ):
            raise ValueError(
                f"field {field} must be a string."
            )

        if not data[field].strip():
            raise ValueError(
                f"field {field} cannot be empty."
            )

    @staticmethod
    def _require_number(
        data: dict,
        field: str
    ) -> None:
        """
        Ensure a field exists and contains
        a number.

        bool is excluded because bool is technically
        a subclass of int in Python.
        """

        if field not in data:
            raise ValueError(
                f"missing required field: {field}"
            )

        value = data[field]

        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                (int, float)
            )
        ):
            raise ValueError(
                f"field {field} must be a number."
            )

    @staticmethod
    def _require_integer(
        data: dict,
        field: str
    ) -> None:
        """
        Ensure a field exists and contains
        an integer.
        """

        if field not in data:
            raise ValueError(
                f"missing required field: {field}"
            )

        value = data[field]

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
        ):
            raise ValueError(
                f"field {field} must be an integer."
            )

    @classmethod
    def _validate_user_created(
        cls,
        data: dict
    ) -> None:
        """
        Validate user.created.

        Required:
            user_id -> string
            name    -> string
            email   -> string
            age     -> integer
        """

        cls._require_string(
            data,
            "user_id"
        )

        cls._require_string(
            data,
            "name"
        )

        cls._require_string(
            data,
            "email"
        )

        cls._require_integer(
            data,
            "age"
        )

        if data["age"] < 0:
            raise ValueError(
                "field age must be a non-negative integer."
            )

    @classmethod
    def _validate_profile_updated(
        cls,
        data: dict
    ) -> None:
        """
        Validate profile.updated.

        Required:
            user_id -> string
            name    -> string
            city    -> string
        """

        cls._require_string(
            data,
            "user_id"
        )

        cls._require_string(
            data,
            "name"
        )

        cls._require_string(
            data,
            "city"
        )

    @classmethod
    def _validate_status_changed(
        cls,
        data: dict
    ) -> None:
        """
        Validate status.changed.
        """

        cls._require_string(
            data,
            "user_id"
        )

        cls._require_string(
            data,
            "status"
        )

        if data["status"] not in cls.VALID_STATUS_VALUES:
            raise ValueError(
                f"Invalid status value: "
                f"{data['status']}. "
                f"Must be one of "
                f"{cls.VALID_STATUS_VALUES}"
            )

    @classmethod
    def _validate_balance_added(
        cls,
        data: dict
    ) -> None:
        """
        Validate balance.added.
        """

        cls._require_string(
            data,
            "user_id"
        )

        cls._require_number(
            data,
            "amount"
        )

        if data["amount"] <= 0:
            raise ValueError(
                "Balance amount must be greater than zero"
            )

    @classmethod
    def _validate_payment_completed(
        cls,
        data: dict
    ) -> None:
        """
        Validate payment.completed.
        """

        cls._require_string(
            data,
            "user_id"
        )

        cls._require_number(
            data,
            "amount"
        )

        cls._require_string(
            data,
            "method"
        )

        if data["amount"] <= 0:
            raise ValueError(
                "Payment amount must be greater than zero"
            )

        if data["method"] not in cls.VALID_PAYMENT_METHODS:
            raise ValueError(
                f"Invalid payment method: "
                f"{data['method']}"
            )

        if "order_id" in data and data["order_id"] is not None:
            if not isinstance(data["order_id"], str) or not data["order_id"].strip():
                raise ValueError("field order_id must be a non-empty string if provided.")

    @classmethod
    def _validate_order_created(
        cls,
        data: dict
    ) -> None:
        """
        Validate order.created.
        """

        cls._require_string(
            data,
            "order_id"
        )

        cls._require_string(
            data,
            "user_id"
        )

        cls._require_number(
            data,
            "amount"
        )

        if data["amount"] <= 0:
            raise ValueError(
                "Order amount must be greater than zero"
            )

    @classmethod
    def _validate_order_updated(
        cls,
        data: dict
    ) -> None:
        """
        Validate order.updated.
        """

        cls._require_string(
            data,
            "order_id"
        )

        cls._require_string(
            data,
            "status"
        )

        if data["status"] not in cls.VALID_ORDER_STATUSES:
            raise ValueError(
                f"Invalid order status: "
                f"{data['status']}"
            )

    @classmethod
    def _validate_user_deleted(
        cls,
        data: dict
    ) -> None:
        """
        Validate user.deleted.
        """

        cls._require_string(
            data,
            "user_id"
        )

    # =========================================================
    # CHRONOREPLAY FILE EVENTS
    # =========================================================

    @classmethod
    def _validate_file_created(
        cls,
        data: dict
    ) -> None:
        """
        Validate file.created.

        Required:
            file_path
            snapshot_id
            content_hash
        """

        cls._require_string(
            data,
            "file_path"
        )

        cls._require_string(
            data,
            "snapshot_id"
        )

        cls._require_string(
            data,
            "content_hash"
        )

    @classmethod
    def _validate_file_modified(
        cls,
        data: dict
    ) -> None:
        """
        Validate file.modified.

        Required:
            file_path
            snapshot_id
            content_hash
        """

        cls._require_string(
            data,
            "file_path"
        )

        cls._require_string(
            data,
            "snapshot_id"
        )

        cls._require_string(
            data,
            "content_hash"
        )

    @classmethod
    def _validate_file_deleted(
        cls,
        data: dict
    ) -> None:
        """
        Validate file.deleted.

        Required:
            file_path
        """

        cls._require_string(
            data,
            "file_path"
        )

    @classmethod
    def _validate_file_restored(
        cls,
        data: dict
    ) -> None:
        """
        Validate file.restored.

        Required:
            file_path
            snapshot_id
            content_hash
        """

        cls._require_string(
            data,
            "file_path"
        )

        cls._require_string(
            data,
            "snapshot_id"
        )

        cls._require_string(
            data,
            "content_hash"
        )

    @classmethod
    def _validate_state_restored(
        cls,
        data: dict
    ) -> None:
        """
        Validate state.restored.

        Required:
            source_event_number (int >= 1)
        """
        if "source_event_number" not in data:
            raise ValueError("missing required field: source_event_number")

        val = data["source_event_number"]
        if isinstance(val, bool) or not isinstance(val, int):
            raise ValueError("field source_event_number must be an integer.")

        if val < 1:
            raise ValueError("source_event_number must be at least 1.")

# ===========================================================================
# MODULE: snapshot.py
# ===========================================================================

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

# ===========================================================================
# MODULE: tracker.py
# ===========================================================================

"""
ChronoReplay automatic workspace tracker.

Connects the filesystem watcher with snapshots,
events, validation and persistent storage.

Only Python standard-library modules are used.
"""

import os
import uuid



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

    # Files and folders created internally by ChronoReplay.
    # These should never appear in the user's event history.
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

        Args:
            workspace_path:
                Folder that ChronoReplay should monitor.

            store:
                EventStore instance.

            interval:
                FileWatcher polling interval.
        """

        self.workspace_path = os.path.abspath(
            workspace_path
        )

        self.store = store

        self.watcher = FileWatcher(
            self.workspace_path,
            interval
        )

    # ---------------------------------------------------------
    # PATH UTILITIES
    # ---------------------------------------------------------

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

        Ignored:
        - ChronoReplay database files
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

    # ---------------------------------------------------------
    # FILE READING
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # SNAPSHOTS
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # EVENT PUBLISHING
    # ---------------------------------------------------------

    def _publish_event(self, event):
        """
        Validate and store an event.

        Every event generated by the tracker passes
        through this method.
        """

        # First validate the event.
        EventValidator.validate(
            event
        )

        # Then persist it.
        self.store.save(
            event
        )

        return event

    # ---------------------------------------------------------
    # CREATED
    # ---------------------------------------------------------

    def _handle_created(self, relative_path):
        """
        Handle a newly created file.

        A snapshot is created because the file currently exists.
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

    # ---------------------------------------------------------
    # MODIFIED
    # ---------------------------------------------------------

    def _handle_modified(self, relative_path):
        """
        Handle a modified file.

        The latest contents are captured as a new snapshot.
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

    # ---------------------------------------------------------
    # DELETED
    # ---------------------------------------------------------

    def _handle_deleted(self, relative_path):
        """
        Handle a deleted file.

        The file no longer exists, so we cannot create
        a new snapshot here.

        The previous snapshot remains available in storage
        and can later be used for restoration.
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

    # ---------------------------------------------------------
    # RESTORED
    # ---------------------------------------------------------

    def _handle_restored(
        self,
        relative_path,
        snapshot
    ):
        """
        Create a file.restored event.

        This method is intended to be used when a historical
        snapshot is restored back into the workspace.

        Args:
            relative_path:
                Path of the restored file.

            snapshot:
                Snapshot that was restored.
        """

        if self._is_ignored(relative_path):
            return None

        event = Event.create(
            "file.restored",
            {
                "file_path": relative_path,
                "snapshot_id": snapshot.snapshot_id,
                "content_hash": snapshot.content_hash,
            }
        )

        return self._publish_event(
            event
        )

    # ---------------------------------------------------------
    # PROCESS CHANGES
    # ---------------------------------------------------------

    def process_changes(self):
        """
        Detect and process current workspace changes.

        Returns:
            List of generated events.
        """

        changes = self.watcher.detect_changes()

        events = []

        # -----------------------------
        # CREATED FILES
        # -----------------------------

        for path in changes["created"]:

            event = self._handle_created(
                path
            )

            if event is not None:
                events.append(event)

        # -----------------------------
        # MODIFIED FILES
        # -----------------------------

        for path in changes["modified"]:

            event = self._handle_modified(
                path
            )

            if event is not None:
                events.append(event)

        # -----------------------------
        # DELETED FILES
        # -----------------------------

        for path in changes["deleted"]:

            event = self._handle_deleted(
                path
            )

            if event is not None:
                events.append(event)

        return events

    # ---------------------------------------------------------
    # INITIALIZATION
    # ---------------------------------------------------------

    def initialize(self):
        """
        Record the initial state of the workspace.

        Existing files do not generate events.

        The watcher simply establishes the baseline
        against which future changes will be detected.
        """

        return self.watcher.initialize()

# ===========================================================================
# MODULE: store.py
# ===========================================================================


class _NoCloseConn:
    def __init__(self, conn):
        self._conn = conn
    def close(self):
        pass
    def __getattr__(self, name):
        return getattr(self._conn, name)

"""
SQLite event and snapshot store for ChronoReplay.

This module provides persistent storage for:
- events
- file snapshots

Only Python standard-library modules are used.
"""

import json
import os
import sqlite3



class EventStore:
    """
    Events and snapshots are stored in a SQLite database.

    The class provides methods to:

    Events:
    - create the database
    - save events
    - retrieve events
    - retrieve all events
    - retrieve events by type
    - count events

    Snapshots:
    - save snapshots
    - retrieve snapshots
    - retrieve snapshots for a file
    - retrieve all snapshots

    Storage:
    - clear events and snapshots
    """

    def __init__(
        self,
        database_path: str = "chronoreplay.db"
    ):
        """
        Create an event and snapshot storage.

        Args:
            database_path:
                Location of the SQLite database file.
        """

        self.database_path = database_path

        self._initialize_database()

    def _connect(self):
        if self.database_path == ":memory:":
            if not hasattr(self, "_mem_conn_cache") or self._mem_conn_cache is None:
                self._mem_conn_cache = _NoCloseConn(sqlite3.connect(":memory:"))
            return self._mem_conn_cache
        return sqlite3.connect(self.database_path)
    def _initialize_database(self) -> None:
        """
        Create the events and snapshots tables
        if they do not already exist.
        """
        try:
            connection = self._connect()
            try:
                cursor = connection.cursor()

                # --------------------------------------------------
                # EVENTS TABLE
                # --------------------------------------------------

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        id TEXT PRIMARY KEY,
                        version INTEGER NOT NULL,
                        type TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        data TEXT NOT NULL
                    )
                    """
                )

                # --------------------------------------------------
                # SNAPSHOTS TABLE
                # --------------------------------------------------

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS snapshots (
                        snapshot_id TEXT PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        content_hash TEXT NOT NULL
                    )
                    """
                )

                connection.commit()

            finally:
                connection.close()

        except sqlite3.DatabaseError:
            # If the database file is corrupted or not a valid SQLite database,
            # remove the corrupted file and recreate a clean database.
            if self.database_path != ":memory:" and os.path.exists(self.database_path):
                try:
                    os.remove(self.database_path)
                except OSError:
                    pass

            connection = self._connect()
            try:
                cursor = connection.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        id TEXT PRIMARY KEY,
                        version INTEGER NOT NULL,
                        type TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        data TEXT NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS snapshots (
                        snapshot_id TEXT PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        content_hash TEXT NOT NULL
                    )
                    """
                )
                connection.commit()
            finally:
                connection.close()

    # ==========================================================
    # EVENT STORAGE
    # ==========================================================

    def save(self, event: Event) -> None:
        """
        Save an event into the database.

        If an event with the same ID already exists,
        ValueError is raised.
        """

        if not isinstance(event, Event):
            raise ValueError(
                "Only Event objects can be stored."
            )

        connection = self._connect()

        try:
            cursor = connection.cursor()

            try:

                cursor.execute(
                    """
                    INSERT INTO events
                    (id, version, type, timestamp, data)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        event.id,
                        event.version,
                        event.type,
                        event.timestamp,
                        json.dumps(
                            event.data,
                            separators=(",", ":"),
                            sort_keys=True,
                        ),
                    ),
                )

                connection.commit()

            except sqlite3.IntegrityError as exc:

                raise ValueError(
                    f"Event with id '{event.id}' already exists."
                ) from exc

        finally:
            connection.close()

    def save_event(self, event: Event) -> None:
        """
        Compatibility wrapper for save().
        """

        self.save(event)

    def append(self, event: Event) -> None:
        """
        Alias for save().
        """
        self.save(event)

    def get(self, event_id: str):
        """
        Retrieve one event by its ID.

        Returns:
            Event object if found.
            None if event does not exist.
        """

        connection = self._connect()

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT id, version, type, timestamp, data
                FROM events
                WHERE id = ?
                """,
                (event_id,),
            )

            row = cursor.fetchone()

        finally:
            connection.close()

        if row is None:
            return None

        return self._row_to_event(row)

    def get_event(self, event_id: str):
        """
        Compatibility wrapper for get().
        """

        return self.get(event_id)

    def get_all(self):
        """
        Retrieve all events.

        Events are returned in insertion order.
        """

        connection = self._connect()

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT id, version, type, timestamp, data
                FROM events
                ORDER BY rowid ASC
                """
            )

            rows = cursor.fetchall()

        finally:
            connection.close()

        return [
            self._row_to_event(row)
            for row in rows
        ]

    def get_all_events(self):
        """
        Compatibility wrapper for get_all().
        """

        return self.get_all()

    def get_by_type(self, event_type: str):
        """
        Retrieve all events of a specific type.
        """

        connection = self._connect()

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT id, version, type, timestamp, data
                FROM events
                WHERE type = ?
                ORDER BY rowid ASC
                """,
                (event_type,),
            )

            rows = cursor.fetchall()

        finally:
            connection.close()

        return [
            self._row_to_event(row)
            for row in rows
        ]

    def get_events_by_type(self, event_type: str):
        """
        Compatibility wrapper for get_by_type().
        """

        return self.get_by_type(
            event_type
        )

    def count(self) -> int:
        """
        Return the total number of stored events.
        """

        connection = self._connect()

        try:
            cursor = connection.cursor()

            cursor.execute(
                "SELECT COUNT(*) FROM events"
            )

            result = cursor.fetchone()

        finally:
            connection.close()

        return result[0]

    # ==========================================================
    # SNAPSHOT STORAGE
    # ==========================================================

    def save_snapshot(
        self,
        snapshot: Snapshot
    ) -> None:
        """
        Save a Snapshot into the database.

        A snapshot contains the complete historical
        content of a file.

        If the snapshot ID already exists,
        ValueError is raised.
        """

        if not isinstance(snapshot, Snapshot):
            raise ValueError(
                "Only Snapshot objects can be stored."
            )

        connection = self._connect()

        try:
            cursor = connection.cursor()

            try:

                cursor.execute(
                    """
                    INSERT INTO snapshots
                    (
                        snapshot_id,
                        file_path,
                        content,
                        timestamp,
                        content_hash
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot.snapshot_id,
                        snapshot.file_path,
                        snapshot.content,
                        snapshot.timestamp,
                        snapshot.content_hash,
                    ),
                )

                connection.commit()

            except sqlite3.IntegrityError as exc:

                raise ValueError(
                    "Snapshot with id "
                    f"'{snapshot.snapshot_id}' already exists."
                ) from exc

        finally:
            connection.close()

    def get_snapshot(
        self,
        snapshot_id: str
    ):
        """
        Retrieve one snapshot by its ID.

        Returns:
            Snapshot object if found.
            None if the snapshot does not exist.
        """

        connection = self._connect()

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    snapshot_id,
                    file_path,
                    content,
                    timestamp,
                    content_hash
                FROM snapshots
                WHERE snapshot_id = ?
                """,
                (snapshot_id,),
            )

            row = cursor.fetchone()

        finally:
            connection.close()

        if row is None:
            return None

        return self._row_to_snapshot(row)

    def get_snapshots_for_file(
        self,
        file_path: str
    ):
        """
        Retrieve all snapshots belonging to one file.

        Snapshots are returned in creation order.
        """

        connection = self._connect()

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    snapshot_id,
                    file_path,
                    content,
                    timestamp,
                    content_hash
                FROM snapshots
                WHERE file_path = ?
                ORDER BY rowid ASC
                """,
                (file_path,),
            )

            rows = cursor.fetchall()

        finally:
            connection.close()

        return [
            self._row_to_snapshot(row)
            for row in rows
        ]

    def get_all_snapshots(self):
        """
        Retrieve every stored snapshot.

        Snapshots are returned in creation order.
        """

        connection = self._connect()

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    snapshot_id,
                    file_path,
                    content,
                    timestamp,
                    content_hash
                FROM snapshots
                ORDER BY rowid ASC
                """
            )

            rows = cursor.fetchall()

        finally:
            connection.close()

        return [
            self._row_to_snapshot(row)
            for row in rows
        ]

    # =========================================================
    # USER / ORDER QUERIES
    # =========================================================

    def get_users(self):
        """
        Return all users that appear in event history.
        """

        users = {}

        for event in self.get_all():

            user_id = event.data.get("user_id")

            if user_id:
                users[user_id] = True

        return sorted(users.keys())

    def get_orders(self):
        """
        Return all orders that appear in event history.
        """

        orders = {}

        for event in self.get_all():

            if event.type == "order.created":

                order_id = event.data.get("order_id")

                if order_id:
                    orders[order_id] = event

        return list(orders.values())

    def get_events_for_user(
        self,
        user_id
    ):
        """
        Return every event belonging to a user.
        """

        return [
            event
            for event in self.get_all()
            if event.data.get("user_id") == user_id
        ]

    def get_events_for_order(
        self,
        order_id
    ):
        """
        Return every event belonging to an order.
        """

        return [
            event
            for event in self.get_all()
            if event.data.get("order_id") == order_id
        ]

    def get_events_for_file(
        self,
        file_path: str
    ):
        """
        Return every file-related event belonging to a file.
        """

        return [
            event
            for event in self.get_all()
            if event.type.startswith("file.")
            and event.data.get("file_path") == file_path
        ]

    def get_all_tracked_files(self):
        """
        Return distinct relative file paths that have been tracked in snapshots or events.
        """

        files = set()

        # From snapshots
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT DISTINCT file_path FROM snapshots")
            rows = cursor.fetchall()
            for row in rows:
                if row[0]:
                    files.add(row[0])
        finally:
            connection.close()

        # From events
        for event in self.get_all():
            if event.type.startswith("file.") and "file_path" in event.data:
                files.add(event.data["file_path"])

        return sorted(files)

    # ==========================================================
    # CLEAR & ROLLBACK
    # ==========================================================

    def delete_events_after(self, target_event_id: str) -> int:
        """
        Delete all events inserted after the specified event ID.
        Returns the number of deleted events.
        """
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT rowid FROM events WHERE id = ?", (target_event_id,))
            row = cursor.fetchone()
            if not row:
                return 0
            target_rowid = row[0]
            cursor.execute("DELETE FROM events WHERE rowid > ?", (target_rowid,))
            deleted = cursor.rowcount
            connection.commit()
            return deleted
        finally:
            connection.close()

    def clear(self) -> None:
        """
        Delete all events and snapshots.

        Mainly useful for testing and development.
        """

        connection = self._connect()

        try:
            cursor = connection.cursor()

            cursor.execute(
                "DELETE FROM events"
            )

            cursor.execute(
                "DELETE FROM snapshots"
            )

            connection.commit()

        finally:
            connection.close()

    # ==========================================================
    # INTERNAL CONVERSION METHODS
    # ==========================================================

    def _row_to_event(
        self,
        row
    ) -> Event:
        """
        Convert a SQLite row into an Event.
        """

        event_id = row[0]
        version = row[1]
        event_type = row[2]
        timestamp = row[3]
        data_json = row[4]

        data = json.loads(
            data_json
        )

        return Event(
            id=event_id,
            version=version,
            type=event_type,
            timestamp=timestamp,
            data=data,
        )

    def _row_to_snapshot(
        self,
        row
    ) -> Snapshot:
        """
        Convert a SQLite row into a Snapshot.
        """

        return Snapshot(
            snapshot_id=row[0],
            file_path=row[1],
            content=row[2],
            timestamp=row[3],
            content_hash=row[4],
        )

# ===========================================================================
# MODULE: state.py
# ===========================================================================

"""
ChronoReplay state reconstruction engine.

The state is NEVER stored as the source of truth.

It is reconstructed by replaying events.
"""

from copy import deepcopy


class StateEngine:

    def __init__(self):
        self.state = {
            "users": {},
            "orders": {},
            "payments": [],
            "files": {},
        }
        self._snapshots = []
        self._event_id_to_snapshot = {}
        self._diagnostics = []
        self._event_count = 0

    # =========================================================
    # APPLY EVENT
    # =========================================================

    def apply(self, event: Event):

        if not isinstance(event, Event):
            raise ValueError(
                "StateEngine can only apply Event objects."
            )

        event_type = event.type
        data = event.data

        if event_type == "user.created":
            self._user_created(data)

        elif event_type == "profile.updated":
            self._profile_updated(data)

        elif event_type == "status.changed":
            self._status_changed(data)

        elif event_type == "balance.added":
            self._balance_added(data)

        elif event_type == "payment.completed":
            self._payment_completed(data)

        elif event_type == "order.created":
            self._order_created(data)

        elif event_type == "order.updated":
            self._order_updated(data)

        elif event_type == "user.deleted":
            self._user_deleted(data)

        # State recovery events
        elif event_type == "state.restored":
            self._apply_state_restored(data)

        # File events do not modify core application state
        elif event_type == "file.created":
            self._file_created(data)

        elif event_type == "file.modified":
            self._file_modified(data)

        elif event_type == "file.deleted":
            self._file_deleted(data)

        elif event_type == "file.restored":
            self._file_restored(data)

        else:
            raise ValueError(
                f"Unsupported event type: {event_type}"
            )

        self._event_count += 1
        current_snapshot = deepcopy(self.state)
        self._snapshots.append(current_snapshot)
        if hasattr(event, "id") and event.id:
            self._event_id_to_snapshot[event.id] = current_snapshot

    # =========================================================
    # USER CREATED
    # =========================================================

    def _user_created(self, data):

        user_id = data["user_id"]

        self.state["users"][user_id] = {
            "user_id": user_id,
            "name": data.get("name", ""),
            "email": data.get("email", ""),
            "age": data.get("age", 0),
            "status": "active",
            "balance": 0.0,
            "deleted": False,
        }

    # =========================================================
    # PROFILE
    # =========================================================

    def _profile_updated(self, data):

        user = self._get_user(data["user_id"])

        user["name"] = data["name"]
        user["city"] = data.get("city", "")

    # =========================================================
    # STATUS
    # =========================================================

    def _status_changed(self, data):

        user = self._get_user(data["user_id"])

        user["status"] = data["status"]

    # =========================================================
    # BALANCE
    # =========================================================

    def _balance_added(self, data):

        user = self._get_user(data["user_id"])

        user["balance"] += float(data["amount"])

    # =========================================================
    # PAYMENT
    # =========================================================

    def _payment_completed(self, data):

        user = self._get_user(data["user_id"])

        amount = float(data["amount"])

        # Auto-resolve target order if not explicitly provided
        order_id = data.get("order_id")
        if not order_id:
            for oid, ord_info in self.state["orders"].items():
                if ord_info.get("user_id") == data["user_id"] and ord_info.get("status") in ("pending", "created"):
                    order_id = oid
                    break

        # Check balance invariant: if balance before payment was less than amount, flag invalid state
        is_valid = user["balance"] >= amount
        if not is_valid:
            self._diagnostics.append({
                "event_index": self._event_count + 1,
                "type": "payment.completed",
                "is_valid": False,
                "reason": "Payment cannot be completed because the available balance is insufficient.",
                "user_id": data["user_id"],
                "order_id": order_id,
                "amount": amount,
                "balance_before": user["balance"],
                "deficit": amount - user["balance"],
            })
        else:
            self._diagnostics.append({
                "event_index": self._event_count + 1,
                "type": "payment.completed",
                "is_valid": True,
                "reason": None,
                "user_id": data["user_id"],
                "order_id": order_id,
                "amount": amount,
            })

        # If payment is valid, deduct from balance and update order
        if is_valid:
            user["balance"] -= amount
        else:
            # When payment is invalid (insufficient funds), balance must NOT drop into negative.
            # Balance is preserved and kept at >= 0.0.
            user["balance"] = max(0.0, user["balance"])

        payment_entry = {
            "user_id": data["user_id"],
            "amount": amount,
            "method": data.get("method", "UPI"),
            "status": "success" if is_valid else "failed_insufficient_funds",
        }

        if order_id:
            payment_entry["order_id"] = order_id
            if order_id in self.state["orders"]:
                order = self.state["orders"][order_id]
                if is_valid:
                    order["paid_amount"] = order.get("paid_amount", 0.0) + amount
                    if order["paid_amount"] >= order["amount"]:
                        order["status"] = "paid"

        self.state["payments"].append(payment_entry)

    # =========================================================
    # ORDER CREATED
    # =========================================================

    def _order_created(self, data):

        user = self._get_user(data["user_id"])

        order_id = data["order_id"]

        self.state["orders"][order_id] = {
            "order_id": order_id,
            "user_id": user["user_id"],
            "amount": float(data["amount"]),
            "paid_amount": 0.0,
            "status": "pending",
        }

    # =========================================================
    # ORDER UPDATED
    # =========================================================

    def _order_updated(self, data):

        order_id = data["order_id"]

        if order_id not in self.state["orders"]:
            raise ValueError(
                f"Order '{order_id}' does not exist."
            )

        self.state["orders"][order_id]["status"] = data["status"]

    # =========================================================
    # USER DELETED
    # =========================================================

    def _user_deleted(self, data):
        user_id = data.get("user_id")
        if user_id in self.state["users"]:
            del self.state["users"][user_id]

    # =========================================================
    # FILE EVENTS
    # =========================================================

    def _file_created(self, data):
        file_path = data["file_path"]
        self.state["files"][file_path] = {
            "file_path": file_path,
            "snapshot_id": data.get("snapshot_id"),
            "content_hash": data.get("content_hash"),
            "exists": True,
        }

    def _file_modified(self, data):
        file_path = data["file_path"]
        self.state["files"][file_path] = {
            "file_path": file_path,
            "snapshot_id": data.get("snapshot_id"),
            "content_hash": data.get("content_hash"),
            "exists": True,
        }

    def _file_deleted(self, data):
        file_path = data["file_path"]
        if file_path in self.state["files"]:
            self.state["files"][file_path]["exists"] = False
        else:
            self.state["files"][file_path] = {
                "file_path": file_path,
                "snapshot_id": None,
                "content_hash": None,
                "exists": False,
            }

    def _file_restored(self, data):
        file_path = data["file_path"]
        self.state["files"][file_path] = {
            "file_path": file_path,
            "snapshot_id": data.get("snapshot_id"),
            "content_hash": data.get("content_hash"),
            "exists": True,
        }

    def _apply_state_restored(self, data: dict) -> None:
        source_event_id = data.get("source_event_id")
        if source_event_id and source_event_id in self._event_id_to_snapshot:
            self.state = deepcopy(self._event_id_to_snapshot[source_event_id])
            return

        source_event_number = data.get("source_event_number")
        if source_event_number is not None:
            if not isinstance(source_event_number, int):
                raise ValueError("source_event_number must be an integer.")

            if source_event_number < 1:
                raise ValueError("source_event_number must be at least 1.")

            if source_event_number > len(self._snapshots):
                raise ValueError("Cannot restore to a future or unavailable event.")

            self.state = deepcopy(self._snapshots[source_event_number - 1])
        else:
            raise ValueError("source_event_id or source_event_number required.")

    # =========================================================
    # HELPERS
    # =========================================================

    def _get_user(self, user_id):

        if user_id not in self.state["users"]:
            raise ValueError(
                f"User '{user_id}' does not exist."
            )

        return self.state["users"][user_id]

    # =========================================================
    # STATE
    # =========================================================

    def get_state(self):

        return {
            "users": {
                key: dict(value)
                for key, value in self.state["users"].items()
            },
            "orders": {
                key: dict(value)
                for key, value in self.state["orders"].items()
            },
            "payments": list(self.state.get("payments", [])),
            "files": {
                key: dict(value)
                for key, value in self.state.get("files", {}).items()
            },
        }

    # =========================================================
    # USER STATE
    # =========================================================

    def get_user(self, user_id):

        return dict(
            self._get_user(user_id)
        )

    # =========================================================
    # ORDER STATE
    # =========================================================

    def get_order(self, order_id):

        if order_id not in self.state["orders"]:
            raise ValueError(
                f"Order '{order_id}' does not exist."
            )

        return dict(
            self.state["orders"][order_id]
        )

    # =========================================================
    # SNAPSHOTS & COUNTS
    # =========================================================

    def get_snapshot(self, event_number: int) -> dict:
        if event_number < 1:
            raise ValueError("Event number must be at least 1.")

        if event_number > len(self._snapshots):
            raise ValueError("Requested event number does not exist.")

        return deepcopy(self._snapshots[event_number - 1])

    def event_count(self) -> int:
        return self._event_count

    def get_diagnostics(self) -> list:
        return list(self._diagnostics)

    def get_event_validity(self, event_number: int) -> dict:
        for diag in self._diagnostics:
            if diag.get("event_index") == event_number:
                return diag
        return {"event_index": event_number, "is_valid": True, "reason": None}

    def reset(self) -> None:
        self.state = {
            "users": {},
            "orders": {},
            "payments": [],
            "files": {},
        }
        self._snapshots = []
        self._diagnostics = []
        self._event_count = 0

# ===========================================================================
# MODULE: replay.py
# ===========================================================================

"""
ChronoReplay replay and time-machine engine.
"""



class ReplayEngine:

    def __init__(self, store: EventStore):

        if not isinstance(store, EventStore):
            raise ValueError(
                "ReplayEngine requires an EventStore."
            )

        self.store = store

    # =========================================================
    # FULL REPLAY
    # =========================================================

    def replay_all(self) -> dict:

        events = self.store.get_all()

        return self._replay_events(events)

    # =========================================================
    # REPLAY UNTIL EVENT
    # =========================================================

    def replay_until(
        self,
        event_number: int
    ) -> dict:

        if (
            isinstance(event_number, bool)
            or not isinstance(event_number, int)
        ):
            raise ValueError(
                "Event number must be an integer."
            )

        if event_number < 1:
            raise ValueError(
                "Event number must be at least 1."
            )

        events = self.store.get_all()

        if event_number > len(events):
            raise ValueError(
                "Requested event number does not exist."
            )

        return self._replay_events(
            events[:event_number]
        )

    # =========================================================
    # REPLAY EVENT
    # =========================================================

    def replay_event(
        self,
        event_id: str
    ) -> dict:

        events = self.store.get_all()

        for index, event in enumerate(events):

            if event.id == event_id:

                return self._replay_events(
                    events[:index + 1]
                )

        raise ValueError(
            f"Event '{event_id}' does not exist."
        )

    def replay_until_event_id(
        self,
        event_id: str
    ) -> dict:
        """Replay all historical events up to and including event_id."""
        return self.replay_event(event_id)

    def replay_before_event_id(
        self,
        event_id: str
    ) -> dict:
        """Replay all historical events strictly before event_id."""
        events = self.store.get_all()
        for index, event in enumerate(events):
            if event.id == event_id:
                if index == 0:
                    return StateEngine().get_state()
                return self._replay_events(events[:index])

        raise ValueError(
            f"Event '{event_id}' does not exist."
        )

    def replay_events_list(
        self,
        events: list
    ) -> dict:
        """Replay an explicit list of events."""
        return self._replay_events(events)

    def replay_events_with_engine(
        self,
        events: list
    ):
        """Replay an explicit list of events returning (state, engine)."""
        engine = StateEngine()
        for event in events:
            engine.apply(event)
        return engine.get_state(), engine

    # =========================================================
    # REPLAY USER
    # =========================================================

    def replay_user(
        self,
        user_id: str
    ) -> dict:

        events = self.store.get_all()

        selected = []

        for event in events:

            if event.data.get("user_id") == user_id:
                selected.append(event)

        return self._replay_events(selected)

    # =========================================================
    # HISTORY
    # =========================================================

    def get_history(self) -> list:
        return self.store.get_all()

    def history_count(self) -> int:
        return self.store.count()

    # =========================================================
    # EVENT DETAILS
    # =========================================================

    def get_event_number(
        self,
        event_id: str
    ):

        events = self.store.get_all()

        for index, event in enumerate(events):

            if event.id == event_id:
                return index + 1

        return None

    # =========================================================
    # USER TIMELINE
    # =========================================================

    def get_user_timeline(
        self,
        user_id
    ):

        events = self.store.get_events_for_user(
            user_id
        )

        timeline = []

        for number, event in enumerate(events, start=1):

            timeline.append({
                "number": number,
                "event_id": event.id,
                "type": event.type,
                "timestamp": event.timestamp,
                "data": event.data,
            })

        return timeline

    # =========================================================
    # ORDER TIMELINE
    # =========================================================

    def get_order_timeline(
        self,
        order_id
    ):

        events = self.store.get_events_for_order(
            order_id
        )

        timeline = []

        for number, event in enumerate(events, start=1):

            timeline.append({
                "number": number,
                "event_id": event.id,
                "type": event.type,
                "timestamp": event.timestamp,
                "data": event.data,
            })

        return timeline

    # =========================================================
    # STATE AT EVENT
    # =========================================================

    def state_at_event(
        self,
        event_number
    ):

        return self.replay_until(
            event_number
        )

    # =========================================================
    # STATE BEFORE EVENT
    # =========================================================

    def state_before_event(
        self,
        event_number
    ):

        if event_number <= 1:

            return StateEngine().get_state()

        return self.replay_until(
            event_number - 1
        )

    # =========================================================
    # REPLAY WITH ENGINE / DIAGNOSTICS
    # =========================================================

    def replay_with_engine(self, event_number: int = None):
        """
        Replay up to event_number (or all events) and return (state, engine).
        """
        events = self.store.get_all()
        if event_number is not None:
            if event_number < 1 or event_number > len(events):
                raise ValueError("Requested event number out of range.")
            events = events[:event_number]

        engine = StateEngine()
        for event in events:
            engine.apply(event)

        return engine.get_state(), engine

    def get_diagnostics_for_event(self, event_number: int) -> dict:
        """
        Check if event at event_number produced an invalid state.
        """
        _, engine = self.replay_with_engine(event_number)
        return engine.get_event_validity(event_number)

    def get_diagnostics_for_event_id(self, event_id: str) -> dict:
        """
        Check if the event with event_id produced an invalid state during historical replay.
        """
        events = self.store.get_all()
        engine = StateEngine()
        for index, event in enumerate(events, start=1):
            engine.apply(event)
            if event.id == event_id:
                return engine.get_event_validity(index)
        return {"event_index": 0, "is_valid": True}

    def get_all_diagnostics(self) -> list:
        """
        Return all diagnostic items from replaying the entire history.
        """
        _, engine = self.replay_with_engine()
        return engine.get_diagnostics()

    # =========================================================
    # REPLAY
    # =========================================================

    @staticmethod
    def _replay_events(
        events: list
    ) -> dict:

        engine = StateEngine()

        for event in events:
            engine.apply(event)

        return engine.get_state()

# ===========================================================================
# MODULE: history.py
# ===========================================================================

"""
ChronoReplay version history.

Provides a high-level API for viewing the historical
versions of workspace files.

This module does not create its own database.
It uses EventStore's existing events and snapshots.

Only Python standard-library functionality is used.
"""

import os
from dataclasses import dataclass
from typing import Optional



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

    def list_files(self, workspace_path: Optional[str] = None):
        """
        Return all workspace files that have appeared
        in the event history (optionally filtered by workspace_path).

        Deleted files are included because they are still
        part of the historical record.
        """

        files = set()

        events = self.store.get_all_events()

        for event in events:

            if event.type not in self.FILE_EVENT_TYPES:
                continue

            if workspace_path is not None:
                ev_ws = event.data.get("workspace_path")
                if ev_ws is not None and os.path.abspath(str(ev_ws)) != os.path.abspath(workspace_path):
                    continue

            file_path = event.data.get("file_path")

            if file_path:
                files.add(file_path)

        return sorted(files)

    # =========================================================
    # FILE HISTORY
    # =========================================================

    def get_file_history(self, file_path, workspace_path: Optional[str] = None):
        """
        Return the complete version history of one file.
        Optionally filtered by workspace_path.

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

            if workspace_path is not None:
                ev_ws = event.data.get("workspace_path")
                if ev_ws is not None and os.path.abspath(str(ev_ws)) != os.path.abspath(workspace_path):
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

# ===========================================================================
# MODULE: restore.py
# ===========================================================================

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

    # ---------------------------------------------------------
    # PARTIAL & NON-DESTRUCTIVE RESTORATION HELPERS
    # ---------------------------------------------------------

    def restore_selected_lines(
        self,
        snapshot_id: str,
        line_numbers: list,
        placement: str = "append",
        user_id: str = None
    ) -> Event:
        """
        Extract specific 1-based line numbers from a snapshot and merge them
        into the active workspace file without overwriting existing content.
        """
        snapshot = self.get_version(snapshot_id)
        if snapshot is None:
            raise ValueError(f"Snapshot '{snapshot_id}' was not found.")

        if not snapshot.verify_integrity():
            raise ValueError(f"Snapshot '{snapshot_id}' failed integrity verification.")

        full_path = self._validate_relative_path(snapshot.file_path)
        snapshot_lines = snapshot.content.splitlines()

        extracted_lines = []
        for line_no in line_numbers:
            if 1 <= line_no <= len(snapshot_lines):
                extracted_lines.append(snapshot_lines[line_no - 1])

        extracted_text = "\n".join(extracted_lines)
        current_text = ""
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8", newline="") as f:
                current_text = f.read()

        if placement == "prepend":
            new_content = extracted_text + ("\n" if extracted_text else "") + current_text
        else:  # append
            sep = "\n" if (current_text and not current_text.endswith("\n")) else ""
            new_content = current_text + (sep if current_text else "") + extracted_text
            if not new_content.endswith("\n"):
                new_content += "\n"

        parent_dir = os.path.dirname(full_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        with open(full_path, "w", encoding="utf-8", newline="") as f:
            f.write(new_content)

        event_data = {
            "file_path": snapshot.file_path,
            "snapshot_id": snapshot.snapshot_id,
            "content_hash": snapshot.content_hash,
            "restored_lines": list(line_numbers),
            "placement": placement,
        }
        if user_id:
            event_data["user_id"] = user_id

        event = Event.create("file.restored", event_data)
        EventValidator.validate(event)
        self.store.save(event)
        return event

    def restore_keep_both(
        self,
        snapshot_id: str,
        mode: str = "combine_sections",
        new_file_path: str = None,
        user_id: str = None
    ) -> Event:
        """
        Non-destructively preserve both active workspace state and historical snapshot.

        Modes:
            - 'combine_sections': Appends historical version in a clearly delineated section.
            - 'new_file': Writes historical version into a separate backup file path.
        """
        snapshot = self.get_version(snapshot_id)
        if snapshot is None:
            raise ValueError(f"Snapshot '{snapshot_id}' was not found.")

        if not snapshot.verify_integrity():
            raise ValueError(f"Snapshot '{snapshot_id}' failed integrity verification.")

        if mode == "new_file":
            target_rel_path = new_file_path or f"{snapshot.file_path}.restored"
            target_full_path = self._validate_relative_path(target_rel_path)

            parent_dir = os.path.dirname(target_full_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            with open(target_full_path, "w", encoding="utf-8", newline="") as f:
                f.write(snapshot.content)

            # Generate and save snapshot for the new file
            new_snap = Snapshot.create(
                snapshot_id=os.urandom(16).hex(),
                file_path=target_rel_path,
                content=snapshot.content
            )
            self.store.save_snapshot(new_snap)

            event_data = {
                "file_path": target_rel_path,
                "snapshot_id": new_snap.snapshot_id,
                "content_hash": new_snap.content_hash,
            }
            if user_id:
                event_data["user_id"] = user_id

            event = Event.create("file.created", event_data)
            EventValidator.validate(event)
            self.store.save(event)
            return event

        else:  # combine_sections
            full_path = self._validate_relative_path(snapshot.file_path)
            current_text = ""
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8", newline="") as f:
                    current_text = f.read()

            combined = (
                "// ==========================================\n"
                "// CURRENT WORKING STATE\n"
                "// ==========================================\n"
                f"{current_text.rstrip()}\n\n"
                "// ==========================================\n"
                "// RESTORED HISTORICAL VERSION\n"
                "// ==========================================\n"
                f"{snapshot.content}\n"
            )

            parent_dir = os.path.dirname(full_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            with open(full_path, "w", encoding="utf-8", newline="") as f:
                f.write(combined)

            event_data = {
                "file_path": snapshot.file_path,
                "snapshot_id": snapshot.snapshot_id,
                "content_hash": snapshot.content_hash,
                "mode": "combine_sections",
            }
            if user_id:
                event_data["user_id"] = user_id

            event = Event.create("file.restored", event_data)
            EventValidator.validate(event)
            self.store.save(event)
            return event

    # ---------------------------------------------------------
    # APPLICATION STATE RESTORATION (APPEND-ONLY)
    # ---------------------------------------------------------


    def restore_state_snapshot(
        self,
        source_event_number: int,
        reason: str = None
    ) -> Event:
        """
        Create and append a 'state.restored' event targeting an earlier state snapshot.

        This sets the application's head state back to the specified event number
        while strictly preserving all intervening historical events in the ledger.

        Args:
            source_event_number: One-based event index to restore from.
            reason: Optional explanation string for audit trail.

        Returns:
            The newly created and persisted file/state restoration Event.
        """
        if (
            isinstance(source_event_number, bool)
            or not isinstance(source_event_number, int)
        ):
            raise ValueError(
                "source_event_number must be an integer."
            )

        if source_event_number < 1:
            raise ValueError(
                "source_event_number must be at least 1."
            )

        total_events = self.store.count()
        if source_event_number > total_events:
            raise ValueError(
                f"Cannot restore to event #{source_event_number}; only {total_events} events exist."
            )

        data = {
            "source_event_number": source_event_number
        }
        if reason:
            data["reason"] = str(reason)

        event = Event.create(
            "state.restored",
            data
        )

        EventValidator.validate(event)
        self.store.save(event)

        return event

# ===========================================================================
# MODULE: watcher.py
# ===========================================================================

"""
ChronoReplay file watcher.

Detects file creation, modification and deletion
using Python standard-library functionality.

No third-party dependencies are used.
"""

import os
import time


class FileWatcher:
    """
    Watches a directory for file changes.

    The watcher takes periodic snapshots of the directory
    and compares them with the previous scan.
    """

    def __init__(self, workspace_path, interval=1.0):
        """
        Create a file watcher.

        workspace_path:
            Directory to monitor.

        interval:
            Time between scans in seconds.
        """

        self.workspace_path = os.path.abspath(
            workspace_path
        )

        self.interval = interval

        self.previous_state = {}

    def scan(self):
        """
        Scan the workspace and return the current
        state of tracked files.

        Returns:

        {
            "relative/path.py": {
                "size": 123,
                "mtime": 123456789
            }
        }
        """

        current_state = {}

        for root, directories, files in os.walk(
            self.workspace_path
        ):

            # Ignore hidden directories.
            directories[:] = [
                directory
                for directory in directories
                if not directory.startswith(".")
            ]

            for filename in files:

                # Ignore hidden files.
                if filename.startswith("."):
                    continue

                full_path = os.path.join(
                    root,
                    filename
                )

                relative_path = os.path.relpath(
                    full_path,
                    self.workspace_path
                )

                try:

                    stat = os.stat(
                        full_path
                    )

                except OSError:

                    continue

                current_state[relative_path] = {
                    "size": stat.st_size,
                    "mtime": stat.st_mtime_ns,
                }

        return current_state

    def initialize(self):
        """
        Record the initial state of the workspace.

        The first scan does not generate events.
        """

        self.previous_state = self.scan()

        return self.previous_state

    def detect_changes(self):
        """
        Compare the current workspace state with
        the previous state.

        Returns:

        {
            "created": [...],
            "modified": [...],
            "deleted": [...]
        }
        """

        current_state = self.scan()

        previous_files = set(
            self.previous_state
        )

        current_files = set(
            current_state
        )

        created = sorted(
            current_files - previous_files
        )

        deleted = sorted(
            previous_files - current_files
        )

        modified = sorted(
            path
            for path in (
                current_files & previous_files
            )
            if (
                current_state[path]["size"]
                != self.previous_state[path]["size"]
                or
                current_state[path]["mtime"]
                != self.previous_state[path]["mtime"]
            )
        )

        self.previous_state = current_state

        return {
            "created": created,
            "modified": modified,
            "deleted": deleted,
        }

    def watch(self):
        """
        Continuously watch the workspace.

        Yields a dictionary whenever a change
        is detected.
        """

        self.initialize()

        while True:

            changes = self.detect_changes()

            if (
                changes["created"]
                or changes["modified"]
                or changes["deleted"]
            ):
                yield changes

            time.sleep(
                self.interval
            )

# ===========================================================================
# MODULE: workspace.py
# ===========================================================================

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

# ===========================================================================
# MODULE: simulator.py
# ===========================================================================

"""
ChronoReplay Event Simulator.

Creates realistic event sequences while automatically
managing user IDs and order IDs.
"""



class EventSimulator:

    def __init__(self, store: EventStore):

        self.store = store

        # Current active user selected by simulator.
        self.current_user_id = None
        self.current_user_name = None
        self.current_user_email = None

        # Last order created for the current user.
        self.current_order_id = None
        self.current_order_amount = None

        # Initialize from existing store state if any
        self._sync_active_user()

    def _sync_active_user(self):
        """Find the latest active non-deleted user if none is active."""
        if self.current_user_id is None:
            active_users = [u for u in self.get_all_users() if u.get("status") != "deleted"]
            if active_users:
                last_active = active_users[-1]
                self.current_user_id = last_active["user_id"]
                self.current_user_name = last_active.get("name", "")
                self.current_user_email = last_active.get("email", "")
            else:
                self.current_user_id = None
                self.current_user_name = None
                self.current_user_email = None

    def get_current_user(self):
        """Return details of currently active non-deleted user or None."""
        if not self.current_user_id:
            return None
        for u in self.get_all_users():
            if u["user_id"] == self.current_user_id and u.get("status") != "deleted":
                return {
                    "user_id": u["user_id"],
                    "name": u.get("name") or self.current_user_name or "Unknown",
                    "email": u.get("email") or self.current_user_email or "",
                    "balance": u.get("balance", 0.0),
                }
        active_users = [u for u in self.get_all_users() if u.get("status") != "deleted"]
        if active_users:
            self.current_user_id = active_users[0]["user_id"]
            self.current_user_name = active_users[0].get("name", "")
            self.current_user_email = active_users[0].get("email", "")
            return {
                "user_id": self.current_user_id,
                "name": self.current_user_name or "Unknown",
                "email": self.current_user_email or "",
                "balance": active_users[0].get("balance", 0.0),
            }
        self.current_user_id = None
        self.current_user_name = None
        self.current_user_email = None
        return None

    def _next_user_seq(self):
        """Calculate next sequential user number."""
        user_events = [e for e in self.store.get_all() if e.type == "user.created"]
        return len(user_events) + 1

    def _next_order_seq(self):
        """Calculate next sequential order number."""
        order_events = [e for e in self.store.get_all() if e.type == "order.created"]
        return len(order_events) + 1

    # =========================================================
    # INTERNAL SAVE
    # =========================================================

    def _save(
        self,
        event_type,
        data
    ):
        data = dict(data)

        if event_type == "user.created":
            if "user_id" not in data:
                data["user_id"] = Event.generate_user_id(self._next_user_seq())
        elif "user_id" not in data and self.current_user_id:
            data["user_id"] = self.current_user_id

        if event_type == "order.created":
            if "order_id" not in data:
                data["order_id"] = Event.generate_order_id(self._next_order_seq())

        if event_type == "payment.completed":
            if "order_id" not in data and self.current_order_id:
                data["order_id"] = self.current_order_id

        event = Event.create(
            event_type,
            data,
        )

        EventValidator.validate(event)

        self.store.save(event)

        # Automatically remember newly generated user.
        if "user_id" in event.data and (event.type == "user.created" or self.current_user_id is None):
            self.current_user_id = event.data["user_id"]
            if "name" in event.data:
                self.current_user_name = event.data["name"]
            if "email" in event.data:
                self.current_user_email = event.data["email"]

        # Automatically remember newly generated order.
        if event.type == "order.created":
            self.current_order_id = event.data["order_id"]
            self.current_order_amount = event.data.get("amount")

        return event

    # =========================================================
    # CREATE USER
    # =========================================================

    def get_all_users(self):
        """Reconstruct and return list of all users from the store with active balance."""
        users = {}
        for event in self.store.get_all():
            if event.type == "user.created" and "user_id" in event.data:
                uid = event.data["user_id"]
                users[uid] = {
                    "user_id": uid,
                    "name": event.data.get("name", "Unknown"),
                    "email": event.data.get("email", ""),
                    "age": event.data.get("age", 0),
                    "status": "active",
                    "balance": 0.0,
                }
            elif event.type == "profile.updated" and "user_id" in event.data:
                uid = event.data["user_id"]
                if uid in users:
                    users[uid]["name"] = event.data.get("name", users[uid]["name"])
            elif event.type == "status.changed" and "user_id" in event.data:
                uid = event.data["user_id"]
                if uid in users:
                    users[uid]["status"] = event.data.get("status", users[uid]["status"])
            elif event.type == "balance.added" and "user_id" in event.data:
                uid = event.data["user_id"]
                if uid in users:
                    users[uid]["balance"] += float(event.data.get("amount", 0.0))
            elif event.type == "payment.completed" and "user_id" in event.data:
                uid = event.data["user_id"]
                if uid in users:
                    amt = float(event.data.get("amount", 0.0))
                    if users[uid]["balance"] >= amt:
                        users[uid]["balance"] -= amt
            elif event.type == "user.deleted" and "user_id" in event.data:
                uid = event.data["user_id"]
                if uid in users:
                    users[uid]["status"] = "deleted"
        return list(users.values())

    def get_active_users(self):
        """Return only active (non-deleted) users."""
        return [u for u in self.get_all_users() if u.get("status") != "deleted"]

    def get_ex_users(self):
        """Return ex-users (deleted users)."""
        return [u for u in self.get_all_users() if u.get("status") == "deleted"]

    def switch_user(self, user_id):
        """Switch active user by ID."""
        for u in self.get_all_users():
            if u["user_id"] == user_id:
                self.current_user_id = u["user_id"]
                self.current_user_name = u["name"]
                self.current_user_email = u["email"]
                self.current_order_id = None
                return u
        raise ValueError(f"User {user_id} not found.")

    def create_user(
        self,
        name,
        email,
        age
    ):
        seq = self._next_user_seq()
        user_id = Event.generate_user_id(seq)

        event = self._save(
            "user.created",
            {
                "user_id": user_id,
                "name": name,
                "email": email,
                "age": int(age),
            }
        )

        self.current_user_id = user_id
        self.current_user_name = name
        self.current_user_email = email
        self.current_order_id = None
        self.current_order_amount = None

        return event

    # =========================================================
    # SELECT USER
    # =========================================================

    def select_user(
        self,
        user_id,
        name=None,
        email=None
    ):
        self.current_user_id = user_id
        self.current_user_name = name
        self.current_user_email = email
        self.current_order_id = None
        self.current_order_amount = None

    # =========================================================
    # ADD BALANCE
    # =========================================================

    def add_balance(
        self,
        amount
    ):
        if self.current_user_id is None:
            self.create_user(
                "Rahul",
                "rahul@gmail.com",
                25
            )

        return self._save(
            "balance.added",
            {
                "user_id": self.current_user_id,
                "amount": float(amount),
            }
        )

    def get_user_balance(self, user_id=None):
        """Calculate current user balance from stored events."""
        uid = user_id or self.current_user_id
        if not uid:
            return 0.0
        balance = 0.0
        for ev in self.store.get_all():
            if ev.data.get("user_id") == uid:
                if ev.type == "balance.added":
                    balance += float(ev.data.get("amount", 0.0))
                elif ev.type == "payment.completed":
                    amt = float(ev.data.get("amount", 0.0))
                    if balance >= amt:
                        balance -= amt
        return balance

    def get_user_orders(self, user_id=None):
        """Reconstruct list of all orders for user with payment amounts and statuses."""
        uid = user_id or self.current_user_id
        if not uid:
            return []
        orders = {}
        for ev in self.store.get_all():
            if ev.type == "order.created" and ev.data.get("user_id") == uid:
                oid = ev.data.get("order_id")
                orders[oid] = {
                    "order_id": oid,
                    "user_id": uid,
                    "amount": float(ev.data.get("amount", 0.0)),
                    "paid_amount": 0.0,
                    "status": "pending",
                }
            elif ev.type == "payment.completed" and ev.data.get("user_id") == uid:
                oid = ev.data.get("order_id")
                if oid and oid in orders:
                    amt = float(ev.data.get("amount", 0.0))
                    orders[oid]["paid_amount"] += amt
                    if orders[oid]["paid_amount"] >= orders[oid]["amount"]:
                        orders[oid]["status"] = "paid"
            elif ev.type == "order.updated":
                oid = ev.data.get("order_id")
                if oid and oid in orders:
                    orders[oid]["status"] = ev.data.get("status", orders[oid]["status"])
        return list(orders.values())

    def get_user_pending_orders(self, user_id=None):
        """Return list of pending orders that still have a remaining balance to be paid."""
        orders = self.get_user_orders(user_id)
        return [o for o in orders if o.get("status") in ("pending", "created") and (o.get("amount", 0.0) - o.get("paid_amount", 0.0)) > 0]

    # =========================================================
    # CREATE ORDER
    # =========================================================

    def create_order(
        self,
        amount
    ):
        if self.current_user_id is None:
            self.create_user(
                "Rahul",
                "rahul@gmail.com",
                25
            )

        order_id = Event.generate_order_id(self._next_order_seq())

        event = self._save(
            "order.created",
            {
                "user_id": self.current_user_id,
                "order_id": order_id,
                "amount": float(amount),
            }
        )
        self.current_order_id = order_id
        self.current_order_amount = float(amount)
        return event

    # =========================================================
    # PAYMENT
    # =========================================================

    def complete_payment(
        self,
        amount,
        method="UPI",
        order_id=None
    ):
        if self.current_user_id is None:
            raise ValueError(
                "No user selected. Please create or select a user first."
            )

        target_order = order_id or self.current_order_id
        if not target_order:
            for ev in reversed(self.store.get_all()):
                if ev.type == "order.created" and ev.data.get("user_id") == self.current_user_id:
                    target_order = ev.data.get("order_id")
                    break

        if not target_order:
            raise ValueError(
                "No order found for this user. You cannot complete a payment without creating an order first. Please create an order first."
            )

        data = {
            "user_id": self.current_user_id,
            "amount": float(amount),
            "method": method,
            "order_id": target_order,
        }

        return self._save(
            "payment.completed",
            data
        )

    # =========================================================
    # ORDER STATUS
    # =========================================================

    def update_order(
        self,
        status,
        order_id=None
    ):
        target_order = order_id or self.current_order_id
        if target_order is None:
            raise ValueError(
                "No order has been created yet."
            )

        return self._save(
            "order.updated",
            {
                "order_id": target_order,
                "status": status,
            }
        )

    # =========================================================
    # PROFILE
    # =========================================================

    def update_profile(
        self,
        name,
        city="Mumbai"
    ):
        if self.current_user_id is None:
            raise ValueError(
                "No user is selected."
            )

        event = self._save(
            "profile.updated",
            {
                "user_id": self.current_user_id,
                "name": name,
                "city": city,
            }
        )
        self.current_user_name = name
        return event

    # =========================================================
    # STATUS
    # =========================================================

    def change_status(
        self,
        status
    ):
        if self.current_user_id is None:
            raise ValueError(
                "No user is selected."
            )

        return self._save(
            "status.changed",
            {
                "user_id": self.current_user_id,
                "status": status,
            }
        )

    # =========================================================
    # USER DELETED
    # =========================================================

    def delete_user(self, user_id=None):
        target_uid = user_id or self.current_user_id
        if target_uid is None:
            raise ValueError("No user is selected.")

        event = self._save(
            "user.deleted",
            {
                "user_id": target_uid,
            }
        )

        # If the deleted user was the active user, auto-switch to another existing active user
        if self.current_user_id == target_uid:
            remaining_users = [
                u for u in self.get_all_users()
                if u.get("status") != "deleted" and u.get("user_id") != target_uid
            ]
            if remaining_users:
                self.current_user_id = remaining_users[0]["user_id"]
                self.current_user_name = remaining_users[0]["name"]
                self.current_user_email = remaining_users[0]["email"]
            else:
                self.current_user_id = None
                self.current_user_name = None
                self.current_user_email = None
            self.current_order_id = None
            self.current_order_amount = None
        return event

# ===========================================================================
# MODULE: relay.py
# ===========================================================================

"""
Event relay for ChronoReplay.

The EventRelay distributes validated events to registered
subscriber functions.

Only Python standard-library functionality is used.
"""



class EventRelay:
    """
    Distributes events to registered subscribers.

    A subscriber is simply a callable that accepts one Event.

    Example:

        def listener(event):
            print(event.type)

        relay = EventRelay()
        relay.subscribe(listener)
        relay.publish(event)
    """

    def __init__(self):
        """
        Create an empty event relay.
        """

        # A list of functions that want to receive events.
        self._subscribers = []

    def subscribe(self, subscriber) -> None:
        """
        Register a subscriber.

        The subscriber must be callable.
        """

        if not callable(subscriber):
            raise ValueError(
                "Subscriber must be callable."
            )

        # Avoid registering the same subscriber twice.
        if subscriber not in self._subscribers:
            self._subscribers.append(subscriber)

    def unsubscribe(self, subscriber) -> None:
        """
        Remove a subscriber.

        If the subscriber is not registered, nothing happens.
        """

        if subscriber in self._subscribers:
            self._subscribers.remove(subscriber)

    def subscriber_count(self) -> int:
        """
        Return the number of registered subscribers.
        """

        return len(self._subscribers)

    def publish(self, event: Event) -> int:
        """
        Validate and publish an event.

        Every registered subscriber receives the event.

        Returns:
            Number of subscribers that received the event.
        """

        # Make sure we received an Event object.
        if not isinstance(event, Event):
            raise ValueError(
                "Only Event objects can be published."
            )

        # Validate the event before distributing it.
        EventValidator.validate(event)

        # Send the event to every subscriber.
        for subscriber in self._subscribers:
            subscriber(event)

        return len(self._subscribers)

    def clear_subscribers(self) -> None:
        """
        Remove all registered subscribers.
        """

        self._subscribers.clear()

# ===========================================================================
# MODULE: chrono.py
# ===========================================================================


"""
This file is ChronoReplay's main orchestration engine.
It connects the following components:
- Event creation
- Event validation  
- Event relay
- Event storage

It basically says that when user wants to create an event, chrono.py will tell event.py to create it, validator.py to validate it, store.py to store it, and relay.py to notify subscribers.

By  using only Python standard-library modules, ChronoReplay ensures that it can run in any standard Python environment without requiring additional dependencies.
"""



class ChronoReplay:
    """
    This is class is main chronoreplay engine.
    The event creation, validation, storage, and notification are all coordinated by this class.
    It is the main entry point for users to interact with ChronoReplay.
    """

    def __init__(self, database_path="chronoreplay.db"):
        """
        This creates a ChronoReplay instance automatically when a chronoreplay object is formed.
        Parameters:
            database_path:
                Location of the SQLite database.
                This is where the whole data of application is saved.
        """

        # This creates event storage system of application.
        # This means store the create event object inside of chronoreplay instance.
        self.store = EventStore(database_path)

        # This creates event notification system of application.
        self.relay = EventRelay()

    def publish_event(self, event_type, data):
        """
        Most important function of ChronoReplay.
        It handles the entire event creation, validation, storage, and notification process.

        Flow:

        event_type + data
                ↓
             Event
                ↓
           Validation
                ↓
             SQLite
                ↓
             Relay
        """

        # This Create a actual Event object.
        event = Event.create( # new object of Event class is created.
            event_type,
            data,
        )

        # Validate the event before storing it.
        EventValidator.validate(event)

        # Store the event.
        #
        # EventStore uses save(), not save_event().
        self.store.save(event)

        # Notify all subscribers.
        self.relay.publish(event)

        # Return the created event.
        return event

    def get_history(self):
        """
        Return all stored events.
        """

        # EventStore uses get_all().
        return self.store.get_all()

    def get_event(self, event_id):
        """
        Retrieve one event by ID.
        """

        # EventStore uses get().
        return self.store.get(event_id)

    def count_events(self):
        """
        Return the total number of stored events.
        """

        return self.store.count()

    def clear_history(self):
        """
        Remove all events from the store.
        """

        self.store.clear()

    def subscribe(self, callback):
        """
        Subscribe a callback to future events.
        """

        self.relay.subscribe(callback)

    def unsubscribe(self, callback):
        """
        Remove a callback from the subscribers.
        """

        self.relay.unsubscribe(callback)

    def rewind(self, event_number: int) -> dict:
        """
        Non-destructively inspect application state at an earlier point in time.

        Rewinds the replayed state view to `event_number` without deleting or
        modifying any subsequent events in the EventStore.

        Parameters:
            event_number: The 1-based event number to inspect up to.

        Returns:
            dict: The reconstructed application state as of event_number.
        """
        replayer = ReplayEngine(self.store)
        return replayer.replay_until(event_number)

    def restore_state(self, source_event_number: int, reason: str = None) -> Event:
        """
        Append-only state restoration.

        Takes historical state from `source_event_number` and makes it the active
        production state by appending a new 'state.restored' event to the ledger.
        Zero past events are erased or overwritten.

        Parameters:
            source_event_number: The 1-based event number whose state is restored.
            reason: Optional explanation string for the restoration audit trail.

        Returns:
            Event: The newly created and stored 'state.restored' event.
        """
        data = {
            "source_event_number": source_event_number
        }
        if reason:
            data["reason"] = str(reason)

        return self.publish_event("state.restored", data)

    def get_current_state(self) -> dict:
        """Return the fully reduced current state from all stored events."""
        replayer = ReplayEngine(self.store)
        return replayer.replay_all()


# ===========================================================================
# MODULE: ui.py
# ===========================================================================

"""
ChronoReplay graphical user interface.

Architecture:
- Event Simulator: Generate, validate, and append structured business events.
  Automatic ID generation for user_id and order_id without manual inputs.
- Event History & Time Machine: Chronological business event stream with user separation
  and storage filtering, centralized Time Machine playback, invariant diagnostics,
  and state reconstruction. Excludes file workspace events.
- Workspace & File Recovery: Dedicated directory browser, scanner, version history,
  diff inspection, and non-destructive point-in-time file restoration.

Only Python standard-library modules are used.
"""

import os
import difflib
from datetime import datetime
from copy import deepcopy



class ChronoReplayUI:
    """
    Main ChronoReplay application: Local event-sourced debugging & recovery platform.
    """

    # =========================================================
    # COLORS & PALETTE
    # =========================================================

    BG_COLOR = "#0f172a"
    PANEL_COLOR = "#111c2e"
    CARD_COLOR = "#172338"
    INPUT_COLOR = "#0b1220"
    BORDER_COLOR = "#263650"

    TEXT_COLOR = "#f8fafc"
    MUTED_COLOR = "#94a3b8"

    ACCENT_COLOR = "#38bdf8"
    SUCCESS_COLOR = "#22c55e"
    ERROR_COLOR = "#ef4444"
    WARNING_COLOR = "#f59e0b"

    BUTTON_COLOR = "#263650"
    BUTTON_ACTIVE = "#334766"

    # =========================================================
    # BUSINESS EVENT DEFINITIONS
    # =========================================================

    EVENT_OPTIONS = [
        ("User Created", "user.created"),
        ("Profile Updated", "profile.updated"),
        ("Status Changed", "status.changed"),
        ("Balance Added", "balance.added"),
        ("Order Created", "order.created"),
        ("Payment Completed", "payment.completed"),
        ("Order Updated", "order.updated"),
        ("User Deleted", "user.deleted"),
    ]

    LABEL_TO_TYPE = {label: etype for label, etype in EVENT_OPTIONS}
    TYPE_TO_LABEL = {etype: label for label, etype in EVENT_OPTIONS}

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(self, root, database_path=None):
        self.root = root
        self.root.title("ChronoReplay — Event Debugging & Workspace Recovery")
        self.root.geometry("1200x800")
        self.root.minsize(960, 640)
        self.root.configure(bg=self.BG_COLOR)

        self.selected_event_label_var = tk.StringVar(value="User Created")
        self.status_var = tk.StringVar(value="Ready")
        self.workspace_path_var = tk.StringVar(value=os.path.abspath("."))
        self.selected_workspace_file = tk.StringVar()

        # User & Date filters in Event History
        self.history_user_filter_var = tk.StringVar(value="ALL")
        self.history_date_filter_var = tk.StringVar(value="ALL")

        # Initialize event engine & stores
        self.main_db_path = database_path or os.path.join(
            os.path.expanduser("~"),
            ".chronoreplay",
            "chronoreplay.db"
            )
        os.makedirs(os.path.dirname(self.main_db_path), exist_ok=True)
        self.store = EventStore(self.main_db_path)
        self.version_history = VersionHistory(self.store)
        self.replay_engine = ReplayEngine(self.store)
        self.simulator = EventSimulator(self.store)

        # Initialize workspace engine
        self._sync_workspace_path(self.workspace_path_var.get())

        # Dynamic form field variables
        self.field_vars = {}

        self._configure_styles()
        self._build_header()
        self._build_navigation()
        self._build_scrollable_main()

        self.show_dashboard()

    def _sync_workspace_path(self, target_path=None):
        """Synchronize active workspace directory for file tracking."""
        if target_path is None:
            target_path = self.workspace_path_var.get()
        abs_path = os.path.abspath(str(target_path).strip())
        self.workspace_path = abs_path
        self.workspace_path_var.set(abs_path)

        self.restore_manager = RestoreManager(abs_path, self.store)
        self.workspace_manager = WorkspaceManager(abs_path, self.store)

    # =========================================================
    # UI COMPONENT HELPERS (REDUCING REPETITION & BOILERPLATE)
    # =========================================================

    def make_label(
        self, parent, text="", fg=None, bg=None, font=None, bold=False, size=10, **kwargs
    ):
        """Standardized label factory with theme defaults."""
        fg = fg or self.TEXT_COLOR
        if bg is None:
            try:
                bg = parent.cget("bg")
            except Exception:
                bg = self.BG_COLOR
        font = font or ("Segoe UI", size, "bold" if bold else "normal")
        return tk.Label(parent, text=text, fg=fg, bg=bg, font=font, **kwargs)

    def make_button(
        self,
        parent,
        text="",
        command=None,
        bg=None,
        fg=None,
        active_bg=None,
        active_fg=None,
        font=None,
        bold=True,
        size=9,
        padx=12,
        pady=5,
        cursor="hand2",
        **kwargs,
    ):
        """Standardized button factory with dark-theme defaults."""
        bg = bg or self.BUTTON_COLOR
        fg = fg or self.TEXT_COLOR
        active_bg = active_bg or self.BUTTON_ACTIVE
        active_fg = active_fg or fg
        font = font or ("Segoe UI", size, "bold" if bold else "normal")

        opts = {
            "text": text,
            "command": command,
            "bg": bg,
            "fg": fg,
            "activebackground": active_bg,
            "activeforeground": active_fg,
            "font": font,
            "padx": padx,
            "pady": pady,
            "relief": "flat",
            "bd": 0,
            "cursor": cursor,
        }
        opts.update(kwargs)
        return tk.Button(parent, **opts)

    def make_accent_button(
        self, parent, text="", command=None, font=None, bold=True, size=9, padx=14, pady=6, **kwargs
    ):
        """Standardized prominent accent-colored action button."""
        return self.make_button(
            parent,
            text=text,
            command=command,
            bg=self.ACCENT_COLOR,
            fg="#07111f",
            active_bg="#7dd3fc",
            active_fg="#07111f",
            font=font,
            bold=bold,
            size=size,
            padx=padx,
            pady=pady,
            **kwargs,
        )

    def make_card(
        self, parent, bg=None, highlightbackground=None, highlightthickness=1, **kwargs
    ):
        """Standardized container card with consistent border and dark background."""
        return tk.Frame(
            parent,
            bg=bg or self.CARD_COLOR,
            highlightbackground=highlightbackground or self.BORDER_COLOR,
            highlightthickness=highlightthickness,
            **kwargs,
        )

    def make_entry(self, parent, textvariable=None, bg=None, fg=None, font=None, **kwargs):
        """Standardized styled text entry."""
        opts = {
            "bg": bg or self.INPUT_COLOR,
            "fg": fg or self.TEXT_COLOR,
            "insertbackground": fg or self.TEXT_COLOR,
            "relief": "flat",
            "font": font or ("Segoe UI", 10),
        }
        if textvariable is not None:
            opts["textvariable"] = textvariable
        opts.update(kwargs)
        return tk.Entry(parent, **opts)

    def make_dropdown(
        self,
        parent,
        values=None,
        textvariable=None,
        default=None,
        command=None,
        width=None,
        font=None,
        style="Chrono.TCombobox",
        **kwargs,
    ):
        """High-reliability dark-themed dropdown selector."""
        values = values or []
        if textvariable is None:
            textvariable = tk.StringVar(value=default or (values[0] if values else ""))
        elif default and not textvariable.get():
            textvariable.set(default)

        combo_opts = {
            "values": values,
            "textvariable": textvariable,
            "state": "readonly",
            "style": style,
            "font": font or ("Segoe UI", 9),
        }
        if width is not None:
            combo_opts["width"] = width
        combo_opts.update(kwargs)

        combo = ttk.Combobox(parent, **combo_opts)

        # Open popdown on entry click
        combo.bind("<Button-1>", lambda e: combo.event_generate("<Down>"))

        if command:
            combo.bind(
                "<<ComboboxSelected>>",
                lambda e: self.root.after_idle(lambda: command(textvariable.get())),
            )

        return combo

    # =========================================================
    # STYLES & THEMING
    # =========================================================

    def _configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Global listbox palette for Combobox popdowns
        for pat in ("*TCombobox*Listbox.", "*ComboboxPopdown*Listbox.", "*Listbox."):
            self.root.option_add(f"{pat}background", self.INPUT_COLOR)
            self.root.option_add(f"{pat}foreground", self.TEXT_COLOR)
            self.root.option_add(f"{pat}selectBackground", self.BUTTON_ACTIVE)
            self.root.option_add(f"{pat}selectForeground", self.ACCENT_COLOR)

        # Button styles
        style.configure(
            "Chrono.TButton",
            background=self.BUTTON_COLOR,
            foreground=self.TEXT_COLOR,
            borderwidth=0,
            padding=(18, 10),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Chrono.TButton",
            background=[("active", self.BUTTON_ACTIVE), ("pressed", self.CARD_COLOR)],
            foreground=[("active", self.TEXT_COLOR)],
        )

        style.configure(
            "Accent.TButton",
            background=self.ACCENT_COLOR,
            foreground="#07111f",
            borderwidth=0,
            padding=(18, 10),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#7dd3fc"), ("pressed", "#0284c7")],
            foreground=[("active", "#07111f")],
        )

        # Combobox dark style
        style.configure(
            "Chrono.TCombobox",
            fieldbackground=self.INPUT_COLOR,
            background=self.BUTTON_COLOR,
            foreground=self.TEXT_COLOR,
            darkcolor=self.BORDER_COLOR,
            lightcolor=self.BORDER_COLOR,
            arrowcolor=self.ACCENT_COLOR,
            bordercolor=self.BORDER_COLOR,
            borderwidth=1,
            padding=(8, 6),
            font=("Segoe UI", 9),
        )
        style.map(
            "Chrono.TCombobox",
            fieldbackground=[("readonly", self.INPUT_COLOR), ("active", self.INPUT_COLOR)],
            background=[("active", self.BUTTON_ACTIVE), ("readonly", self.BUTTON_COLOR)],
            foreground=[("readonly", self.TEXT_COLOR), ("disabled", self.MUTED_COLOR)],
            arrowcolor=[("active", "#7dd3fc"), ("disabled", self.MUTED_COLOR)],
        )

        style.configure(
            "Chrono.Vertical.TScrollbar",
            background=self.BUTTON_COLOR,
            troughcolor=self.BG_COLOR,
            bordercolor=self.BG_COLOR,
            arrowcolor=self.TEXT_COLOR,
            width=14,
        )

    # =========================================================
    # HEADER & NAVIGATION
    # =========================================================

    def _build_header(self):
        header = tk.Frame(self.root, bg=self.PANEL_COLOR, height=72)
        header.pack(fill="x")
        header.pack_propagate(False)

        self.make_label(
            header, text="⏱  CHRONOREPLAY", bg=self.PANEL_COLOR, size=20, bold=True
        ).pack(side="left", padx=26)

        self.make_label(
            header,
            text="LOCAL EVENT-SOURCED DEBUGGING PLATFORM",
            bg=self.PANEL_COLOR,
            fg=self.MUTED_COLOR,
            size=9,
            bold=True,
        ).pack(side="left")

        status_frame = tk.Frame(header, bg=self.PANEL_COLOR)
        status_frame.pack(side="right", padx=26)

        self.make_label(
            status_frame, text="●", bg=self.PANEL_COLOR, fg=self.SUCCESS_COLOR, size=13
        ).pack(side="left", padx=(0, 6))

        self.make_label(
            status_frame, text="SYSTEM READY", bg=self.PANEL_COLOR, size=10, bold=True
        ).pack(side="left")

    def _build_navigation(self):
        navigation = tk.Frame(self.root, bg=self.BG_COLOR, height=60)
        navigation.pack(fill="x", padx=20, pady=(10, 0))
        navigation.pack_propagate(False)

        for text, cmd in [
            ("EVENT SIMULATOR", self.show_dashboard),
            ("EVENT HISTORY & TIME MACHINE", self.show_event_history),
            ("WORKSPACE & FILE RECOVERY", self.show_workspace),
        ]:
            ttk.Button(navigation, text=text, style="Chrono.TButton", command=cmd).pack(
                side="left", padx=4
            )

    # =========================================================
    # SCROLLABLE MAIN CONTAINER
    # =========================================================

    def _build_scrollable_main(self):
        outer = tk.Frame(self.root, bg=self.BG_COLOR)
        outer.pack(fill="both", expand=True, padx=20, pady=10)

        self.canvas = tk.Canvas(outer, bg=self.BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            outer, orient="vertical", command=self.canvas.yview, style="Chrono.Vertical.TScrollbar"
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.main_container = tk.Frame(self.canvas, bg=self.BG_COLOR)
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.main_container, anchor="nw"
        )

        self.main_container.bind(
            "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.bind(
            "<Configure>", lambda e: self.canvas.itemconfigure(self.canvas_window, width=e.width)
        )

        def _scroll(delta):
            self.canvas.yview_scroll(int(delta), "units")

        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: not isinstance(e.widget, (tk.Text, tk.Listbox)) and _scroll(-1 * (e.delta / 120)),
        )
        self.canvas.bind_all(
            "<Button-4>",
            lambda e: not isinstance(e.widget, (tk.Text, tk.Listbox)) and _scroll(-3),
        )
        self.canvas.bind_all(
            "<Button-5>",
            lambda e: not isinstance(e.widget, (tk.Text, tk.Listbox)) and _scroll(3),
        )

    def _clear_main_area(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()
        self.canvas.yview_moveto(0)

    # =========================================================
    # 1. EVENT SIMULATOR VIEW
    # =========================================================

    def show_dashboard(self):
        self._clear_main_area()

        self.make_label(self.main_container, text="EVENT SIMULATOR", size=22, bold=True).pack(
            anchor="w", pady=(10, 2)
        )
        self.make_label(
            self.main_container,
            text="Simulate business transactions with automatic internal ID generation. ChronoReplay assigns user IDs and order IDs automatically.",
            fg=self.MUTED_COLOR,
            size=11,
        ).pack(anchor="w", pady=(0, 18))

        self._build_active_user_banner()
        self._build_simulator_card()
        self._build_history_preview()

    def _build_active_user_banner(self):
        """Display current active user details, user switcher, and wallet balance."""
        current_user = self.simulator.get_current_user()
        active_users = self.simulator.get_active_users()

        banner_frame = self.make_card(self.main_container)
        banner_frame.pack(fill="x", pady=(0, 16))

        if current_user:
            engine = self.replay_engine.replay_with_engine()[1]
            state = engine.get_state()
            balance = state.get("users", {}).get(current_user["user_id"], {}).get("balance", 0.0)

            left_box = tk.Frame(banner_frame, bg=self.CARD_COLOR)
            left_box.pack(side="left", padx=20, pady=14)

            self.make_label(
                left_box, text="👤 CURRENT ACTIVE USER", fg=self.ACCENT_COLOR, size=9, bold=True
            ).pack(anchor="w")

            user_label = f"{current_user['user_id']}  ─  {current_user['name']} ({current_user['email']})"
            self.make_label(left_box, text=user_label, size=13, bold=True).pack(
                anchor="w", pady=(2, 4)
            )

            if len(active_users) > 1:
                switcher_box = tk.Frame(left_box, bg=self.CARD_COLOR)
                switcher_box.pack(anchor="w", pady=(2, 0))

                self.make_label(
                    switcher_box, text="Switch User Context:", fg=self.MUTED_COLOR, size=8, bold=True
                ).pack(side="left", padx=(0, 6))

                user_options = [f"{u['user_id']} : {u['name']}" for u in active_users]
                self.user_switch_var = tk.StringVar(
                    value=f"{current_user['user_id']} : {current_user['name']}"
                )

                self.make_dropdown(
                    switcher_box,
                    values=user_options,
                    textvariable=self.user_switch_var,
                    command=lambda val: self._on_user_switched(),
                    font=("Segoe UI", 8),
                    width=28,
                ).pack(side="left")

            right_box = tk.Frame(banner_frame, bg=self.CARD_COLOR)
            right_box.pack(side="right", padx=20, pady=14)

            self.make_label(
                right_box, text="WALLET BALANCE", fg=self.MUTED_COLOR, size=9, bold=True
            ).pack(anchor="e")

            bal_color = self.SUCCESS_COLOR if balance >= 0 else self.ERROR_COLOR
            self.make_label(
                right_box, text=f"₹{balance:.2f}", fg=bal_color, size=14, bold=True
            ).pack(anchor="e")

        else:
            no_user_box = tk.Frame(banner_frame, bg=self.CARD_COLOR)
            no_user_box.pack(fill="x", padx=20, pady=14)

            self.make_label(
                no_user_box, text="⚠  NO USER EXISTS", fg=self.WARNING_COLOR, size=11, bold=True
            ).pack(side="left")
            self.make_label(
                no_user_box,
                text="— Create a user first before recording orders or payment events.",
                fg=self.MUTED_COLOR,
                size=10,
            ).pack(side="left", padx=8)

            self.make_accent_button(
                no_user_box,
                text="CREATE USER",
                command=self._switch_to_create_user,
                padx=12,
                pady=4,
            ).pack(side="right")

    def _on_user_switched(self, event=None):
        val = getattr(self, "user_switch_var", None)
        if val:
            user_id = val.get().split(":")[0].strip()
            self.simulator.switch_user(user_id)
            self._show_status(f"Switched active user context to {user_id}", success=True)
            self.show_dashboard()

    def _switch_to_create_user(self):
        self.selected_event_label_var.set("User Created")
        self._render_current_event_form()

    def _build_simulator_card(self):
        card = self.make_card(self.main_container)
        card.pack(fill="x", pady=(0, 20))

        self.make_label(card, text="SIMULATE EVENT", fg=self.ACCENT_COLOR, size=15, bold=True).pack(
            anchor="w", padx=24, pady=(20, 4)
        )
        self.make_label(
            card,
            text="Select an event to dispatch. IDs are assigned automatically by ChronoReplay.",
            fg=self.MUTED_COLOR,
            size=10,
        ).pack(anchor="w", padx=24, pady=(0, 16))

        self.make_label(card, text="SELECT EVENT", fg=self.MUTED_COLOR, size=9, bold=True).pack(
            anchor="w", padx=24, pady=(0, 6)
        )

        options = [label for label, _ in self.EVENT_OPTIONS]
        self.event_dropdown = self.make_dropdown(
            card,
            values=options,
            textvariable=self.selected_event_label_var,
            command=lambda val: self._render_current_event_form(),
            font=("Segoe UI", 10),
        )
        self.event_dropdown.pack(fill="x", padx=24, pady=(0, 16))

        self.form_container = tk.Frame(card, bg=self.CARD_COLOR)
        self.form_container.pack(fill="x", padx=24, pady=(0, 16))

        bottom_bar = tk.Frame(card, bg=self.CARD_COLOR)
        bottom_bar.pack(fill="x", padx=24, pady=(0, 20))

        self.status_banner = self.make_card(bottom_bar, bg=self.INPUT_COLOR)
        self.status_banner.pack(fill="x", expand=True)

        self.status_icon_label = self.make_label(
            self.status_banner, text="●", bg=self.INPUT_COLOR, fg=self.MUTED_COLOR, size=11, bold=True
        )
        self.status_icon_label.pack(side="left", padx=(10, 6), pady=8)

        self.status_label = self.make_label(
            self.status_banner,
            textvariable=self.status_var,
            bg=self.INPUT_COLOR,
            fg=self.MUTED_COLOR,
            anchor="w",
            size=9,
            bold=True,
        )
        self.status_label.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=8)

        self._render_current_event_form()

    def _render_current_event_form(self):
        """Render dynamic fields for selected event type."""
        for widget in self.form_container.winfo_children():
            widget.destroy()

        self.field_vars = {}
        selected_label = self.selected_event_label_var.get()
        event_type = self.LABEL_TO_TYPE.get(selected_label, "user.created")
        current_user = self.simulator.get_current_user()

        if event_type == "user.created":
            self._render_create_user_form()
        elif not current_user:
            self._render_no_user_warning()
        else:
            self._render_user_bound_event_form(event_type, current_user)

    def _render_create_user_form(self):
        """Form for creating new user."""
        form_frame = tk.Frame(self.form_container, bg=self.CARD_COLOR)
        form_frame.pack(fill="x")

        self._create_form_row(form_frame, 0, "Name", "name", default="Rahul")
        self._create_form_row(form_frame, 1, "Email", "email", default="rahul@gmail.com")
        self._create_form_row(form_frame, 2, "Age", "age", default="25", is_number=True)

        btn_row = tk.Frame(form_frame, bg=self.CARD_COLOR)
        btn_row.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12, 0))

        ttk.Button(
            btn_row,
            text="CREATE USER",
            style="Accent.TButton",
            command=self._handle_create_user_submit,
        ).pack()

    def _render_no_user_warning(self):
        """Warning when no user exists."""
        warn_card = self.make_card(
            self.form_container, bg=self.INPUT_COLOR, highlightbackground=self.WARNING_COLOR
        )
        warn_card.pack(fill="x", pady=10)

        inner = tk.Frame(warn_card, bg=self.INPUT_COLOR)
        inner.pack(fill="x", padx=16, pady=14)

        self.make_label(
            inner, text="⚠  No user exists.", bg=self.INPUT_COLOR, fg=self.WARNING_COLOR, size=12, bold=True
        ).pack(anchor="w")
        self.make_label(
            inner,
            text="Create a user first before recording this event.",
            bg=self.INPUT_COLOR,
            size=10,
        ).pack(anchor="w", pady=(2, 10))

        self.make_accent_button(
            inner, text="Create User", command=self._switch_to_create_user, padx=16, pady=6
        ).pack(anchor="w")

    def _render_user_bound_event_form(self, event_type, current_user):
        """Render event form dynamically with active user context."""
        form_frame = tk.Frame(self.form_container, bg=self.CARD_COLOR)
        form_frame.pack(fill="x")

        user_info_frame = self.make_card(form_frame, bg=self.INPUT_COLOR)
        user_info_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        self.make_label(
            user_info_frame,
            text=f"Active User Context: {current_user['user_id']} ─ {current_user['name']}",
            bg=self.INPUT_COLOR,
            fg=self.ACCENT_COLOR,
            size=10,
            bold=True,
        ).pack(side="left", padx=12, pady=8)

        # Form configuration map: event_type -> (fields, btn_text, submit_cmd)
        form_configs = {
            "balance.added": (
                [("row", "Amount (₹)", "amount", "500.0", True)],
                "ADD BALANCE",
                self._handle_add_balance_submit,
            ),
            "order.created": (
                [("row", "Order Amount (₹)", "amount", "200.0", True)],
                "CREATE ORDER",
                self._handle_create_order_submit,
            ),
            "payment.completed": (
                [
                    ("row", "Amount (₹)", "amount", "200.0", True),
                    ("dropdown", "Payment Method", "method", ["UPI", "CARD", "NETBANKING", "CASH"], "UPI"),
                ],
                "RECORD PAYMENT",
                self._handle_complete_payment_submit,
            ),
            "profile.updated": (
                [
                    ("row", "Name", "name", current_user["name"], False),
                    ("row", "City", "city", "Mumbai", False),
                ],
                "UPDATE PROFILE",
                self._handle_update_profile_submit,
            ),
            "status.changed": (
                [("dropdown", "Status", "status", ["active", "suspended", "verified", "inactive"], "active")],
                "CHANGE STATUS",
                self._handle_change_status_submit,
            ),
            "order.updated": (
                [
                    (
                        "dropdown",
                        "Order Status",
                        "status",
                        ["pending", "paid", "shipped", "completed", "cancelled"],
                        "paid",
                    )
                ],
                "UPDATE ORDER",
                self._handle_update_order_submit,
            ),
            "user.deleted": (
                [
                    (
                        "dropdown",
                        "Select User to Delete",
                        "user_id",
                        [
                            f"{u['user_id']} : {u['name']} (Balance: ₹{u.get('balance', 0.0):.2f})"
                            for u in self.simulator.get_active_users()
                        ] or [f"{current_user['user_id']} : {current_user['name']}"],
                        f"{current_user['user_id']} : {current_user['name']} (Balance: ₹{current_user.get('balance', 0.0):.2f})",
                    )
                ],
                "DELETE SELECTED USER",
                self._handle_delete_user_submit,
            ),
        }

        if event_type == "payment.completed":
            user_orders = self.simulator.get_user_orders(current_user["user_id"])
            user_balance = self.simulator.get_user_balance(current_user["user_id"])
            if not user_orders:
                no_order_card = self.make_card(
                    form_frame, bg=self.INPUT_COLOR, highlightbackground=self.WARNING_COLOR
                )
                no_order_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))

                inner = tk.Frame(no_order_card, bg=self.INPUT_COLOR)
                inner.pack(fill="x", padx=16, pady=12)

                self.make_label(
                    inner,
                    text="⚠  NO ORDER FOUND FOR USER",
                    bg=self.INPUT_COLOR,
                    fg=self.WARNING_COLOR,
                    size=10,
                    bold=True,
                ).pack(anchor="w")
                self.make_label(
                    inner,
                    text="Payments cannot be completed without an order. Please create an order first.",
                    bg=self.INPUT_COLOR,
                    size=9,
                ).pack(anchor="w", pady=(2, 8))

                self.make_accent_button(
                    inner,
                    text="CREATE ORDER",
                    command=lambda: (
                        self.selected_event_label_var.set("Order Created"),
                        self._render_current_event_form(),
                    ),
                    padx=14,
                    pady=4,
                ).pack(anchor="w")
                return

            if user_balance <= 0:
                no_bal_card = self.make_card(
                    form_frame, bg=self.INPUT_COLOR, highlightbackground=self.WARNING_COLOR
                )
                no_bal_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))

                inner = tk.Frame(no_bal_card, bg=self.INPUT_COLOR)
                inner.pack(fill="x", padx=16, pady=12)

                self.make_label(
                    inner,
                    text=f"⚠  NO BALANCE AVAILABLE (Current: ₹{user_balance:.2f})",
                    bg=self.INPUT_COLOR,
                    fg=self.WARNING_COLOR,
                    size=10,
                    bold=True,
                ).pack(anchor="w")
                self.make_label(
                    inner,
                    text="Payments cannot be completed without available balance. Please add balance first.",
                    bg=self.INPUT_COLOR,
                    size=9,
                ).pack(anchor="w", pady=(2, 8))

                self.make_accent_button(
                    inner,
                    text="ADD BALANCE (₹500)",
                    command=lambda: (
                        self.selected_event_label_var.set("Balance Added"),
                        self._render_current_event_form(),
                    ),
                    padx=14,
                    pady=4,
                ).pack(anchor="w")
                return

            pending_orders = [o for o in user_orders if o.get("status") in ("pending", "created")]
            order_opts = []
            for o in user_orders:
                remaining = max(0.0, o["amount"] - o.get("paid_amount", 0.0))
                order_opts.append(f"{o['order_id']} : ₹{o['amount']:.2f} (Status: {o['status'].upper()}, Due: ₹{remaining:.2f})")

            default_order = order_opts[0]
            default_amount = "200.0"
            if pending_orders:
                p_ord = pending_orders[0]
                p_rem = max(0.0, p_ord["amount"] - p_ord.get("paid_amount", 0.0))
                default_order = next((opt for opt in order_opts if opt.startswith(p_ord["order_id"])), order_opts[0])
                default_amount = f"{p_rem:.2f}" if p_rem > 0 else f"{p_ord['amount']:.2f}"

            form_configs["payment.completed"] = (
                [
                    ("dropdown", "Select Order to Pay", "order_id", order_opts, default_order),
                    ("row", "Amount (₹)", "amount", default_amount, True),
                    ("dropdown", "Payment Method", "method", ["UPI", "CARD", "NETBANKING", "CASH"], "UPI"),
                ],
                "RECORD PAYMENT",
                self._handle_complete_payment_submit,
            )

        fields, btn_text, btn_cmd = form_configs.get(event_type, ([], "DISPATCH EVENT", lambda: None))

        row_idx = 1
        for field in fields:
            if field[0] == "row":
                _, label_text, var_key, default_val, is_num = field
                self._create_form_row(form_frame, row_idx, label_text, var_key, default_val, is_num)
            elif field[0] == "dropdown":
                _, label_text, var_key, opts, default_val = field
                self._create_form_dropdown(form_frame, row_idx, label_text, var_key, opts, default_val)
            row_idx += 1

        if event_type == "user.deleted":
            self.make_label(
                form_frame,
                text="This will mark the current user as deleted in the event stream.",
                fg=self.MUTED_COLOR,
                size=9,
            ).grid(row=row_idx, column=0, columnspan=2, sticky="w", pady=(0, 10))
            row_idx += 1

        btn_row = tk.Frame(form_frame, bg=self.CARD_COLOR)
        btn_row.grid(row=row_idx, column=0, columnspan=2, sticky="e", pady=(12, 0))

        ttk.Button(btn_row, text=btn_text, style="Accent.TButton", command=btn_cmd).pack()

    def _create_form_row(self, parent, row, label_text, var_key, default="", is_number=False):
        self.make_label(parent, text=label_text, size=9, bold=True).grid(
            row=row, column=0, sticky="w", padx=(0, 14), pady=6
        )
        var = tk.StringVar(value=str(default))
        self.field_vars[var_key] = (var, "number" if is_number else "text")

        border = tk.Frame(parent, bg=self.BORDER_COLOR)
        border.grid(row=row, column=1, sticky="ew", pady=6)
        parent.columnconfigure(1, weight=1)

        self.make_entry(border, textvariable=var, font=("Segoe UI", 9)).pack(
            fill="both", expand=True, padx=1, pady=1, ipady=5
        )

    def _create_form_dropdown(self, parent, row, label_text, var_key, options, default=""):
        self.make_label(parent, text=label_text, size=9, bold=True).grid(
            row=row, column=0, sticky="w", padx=(0, 14), pady=6
        )
        var = tk.StringVar(value=default or (options[0] if options else ""))
        self.field_vars[var_key] = (var, "dropdown")

        combo = self.make_dropdown(parent, values=options, textvariable=var, font=("Segoe UI", 9))
        combo.grid(row=row, column=1, sticky="ew", pady=6)
        parent.columnconfigure(1, weight=1)

    # ---------------------------------------------------------
    # Form submission handlers
    # ---------------------------------------------------------

    def _get_event_local_date(self, event):
        """Extract standardized YYYY-MM-DD local date string from event timestamp."""
        ts = getattr(event, "timestamp", "")
        if not ts:
            return ""
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is not None:
                return dt.astimezone().strftime("%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return ts.split("T")[0].split(" ")[0]

    def _get_event_local_time(self, event):
        """Extract standardized HH:MM:SS local time string from event timestamp."""
        ts = getattr(event, "timestamp", "")
        if not ts:
            return ""
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is not None:
                return dt.astimezone().strftime("%H:%M:%S")
            return dt.strftime("%H:%M:%S")
        except Exception:
            if "T" in ts:
                return ts.split("T")[1].split(".")[0].split("+")[0]
            return ts

    def _handle_create_user_submit(self):
        try:
            name = self.field_vars["name"][0].get().strip()
            email = self.field_vars["email"][0].get().strip()
            age_str = self.field_vars["age"][0].get().strip()
            if not name or not email or not age_str:
                raise ValueError("Name, email, and age are required.")
            event = self.simulator.create_user(name, email, int(age_str))
            self.history_user_filter_var.set("ALL")
            self.history_date_filter_var.set("ALL")
            self._show_status(f"User created successfully — User ID: {event.data['user_id']}", success=True)
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_add_balance_submit(self):
        try:
            amount = float(self.field_vars["amount"][0].get().strip())
            event = self.simulator.add_balance(amount)
            self.history_date_filter_var.set("ALL")
            self._show_status(
                f"Balance added: ₹{amount:.2f} for user {event.data['user_id']}", success=True
            )
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_create_order_submit(self):
        try:
            amount = float(self.field_vars["amount"][0].get().strip())
            event = self.simulator.create_order(amount)
            self.history_date_filter_var.set("ALL")
            self._show_status(
                f"Order created successfully — Order ID: {event.data['order_id']} (₹{amount:.2f})",
                success=True,
            )
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_complete_payment_submit(self):
        try:
            amount = float(self.field_vars["amount"][0].get().strip())
            method = self.field_vars["method"][0].get().strip()
            order_id = None
            if "order_id" in self.field_vars:
                raw_order = self.field_vars["order_id"][0].get().strip()
                if ":" in raw_order:
                    order_id = raw_order.split(":")[0].strip()
                elif raw_order:
                    order_id = raw_order

            self.simulator.complete_payment(amount, method, order_id=order_id)
            self.history_date_filter_var.set("ALL")

            diag = self.replay_engine.get_diagnostics_for_event(len(self.store.get_all()))
            if not diag.get("is_valid", True):
                self._show_status(
                    f"PAYMENT RECORDED WITH INVALID STATE WARNING: {diag.get('reason')}", success=False
                )
            else:
                self._show_status(
                    f"Payment completed: ₹{amount:.2f} for {order_id or 'Order'} via {method}", success=True
                )
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_update_profile_submit(self):
        try:
            name = self.field_vars["name"][0].get().strip()
            city = self.field_vars["city"][0].get().strip()
            self.simulator.update_profile(name, city)
            self._show_status(f"Profile updated: {name}, {city}", success=True)
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_change_status_submit(self):
        try:
            status = self.field_vars["status"][0].get().strip()
            self.simulator.change_status(status)
            self._show_status(f"Status changed to: {status}", success=True)
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_update_order_submit(self):
        try:
            status = self.field_vars["status"][0].get().strip()
            self.simulator.update_order(status)
            self._show_status(f"Order updated to: {status}", success=True)
            self.show_dashboard()
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _handle_delete_user_submit(self):
        try:
            target_uid = None
            if "user_id" in self.field_vars:
                raw_user = self.field_vars["user_id"][0].get().strip()
                if ":" in raw_user:
                    target_uid = raw_user.split(":")[0].strip()
                elif raw_user:
                    target_uid = raw_user

            event = self.simulator.delete_user(user_id=target_uid)
            self.show_dashboard()
            self._show_status(f"Selected user '{event.data['user_id']}' marked as deleted. Other users remain unaffected.", success=True)
        except Exception as exc:
            self._show_status(f"ERROR: {exc}", success=False)

    def _show_status(self, message, success=True):
        if hasattr(self, "status_var"):
            try:
                self.status_var.set(message)
            except Exception:
                pass
        if hasattr(self, "status_label"):
            try:
                color = self.SUCCESS_COLOR if success else self.ERROR_COLOR
                self.status_label.configure(fg=color)
                if hasattr(self, "status_icon_label"):
                    self.status_icon_label.configure(text="✓" if success else "⚠", fg=color)
                if hasattr(self, "status_banner"):
                    self.status_banner.configure(highlightbackground=color)
            except Exception:
                pass

    def _build_history_preview(self):
        """Preview recent business events at the bottom of the simulator."""
        card = self.make_card(self.main_container)
        card.pack(fill="both", expand=True, pady=(0, 24))

        self.make_label(card, text="RECENT EVENT STREAM", fg=self.ACCENT_COLOR, size=15, bold=True).pack(
            anchor="w", padx=24, pady=(20, 6)
        )

        business_events = self._get_business_events()
        if not business_events:
            self.make_label(
                card,
                text="No business events recorded in store. Dispatch an event to begin.",
                fg=self.MUTED_COLOR,
                size=10,
            ).pack(anchor="w", padx=24, pady=(0, 20))
            return

        preview_table = tk.Frame(card, bg=self.CARD_COLOR)
        preview_table.pack(fill="x", padx=24, pady=(0, 20))

        hdr = tk.Frame(preview_table, bg=self.CARD_COLOR)
        hdr.pack(fill="x", pady=(0, 6))
        for col, (title, width) in enumerate(
            [("#", 6), ("USER", 18), ("EVENT", 20), ("DETAILS", 36), ("TIME", 16)]
        ):
            self.make_label(
                hdr, text=title, width=width, anchor="w", fg=self.MUTED_COLOR, size=9, bold=True
            ).grid(row=0, column=col, padx=4)

        recent = business_events[-6:]
        start_idx = len(business_events) - len(recent) + 1

        for i, event in enumerate(recent, start=start_idx):
            row = self.make_card(preview_table, bg=self.INPUT_COLOR)
            row.pack(fill="x", pady=2)

            ts = self._get_event_local_time(event)
            user_badge = event.data.get("user_id", "System")
            if "name" in event.data and event.type == "user.created":
                user_badge = f"{user_badge} ({event.data['name']})"

            details = [
                f"{k}: ₹{event.data[k]}" if k == "amount" else f"{k}: {event.data[k]}"
                for k in ["amount", "order_id", "status", "name"]
                if k in event.data
            ]
            detail_str = " | ".join(details) or str(event.data)

            for text, width, fg, bold in [
                (f"#{i}", 6, self.MUTED_COLOR, True),
                (user_badge, 18, self.ACCENT_COLOR, True),
                (event.type, 20, self.TEXT_COLOR, True),
                (detail_str, 36, self.MUTED_COLOR, False),
                (ts, 16, self.MUTED_COLOR, False),
            ]:
                self.make_label(
                    row,
                    text=text,
                    width=width,
                    anchor="w",
                    bg=self.INPUT_COLOR,
                    fg=fg,
                    size=8 if width == 16 else 9,
                    bold=bold,
                ).pack(side="left", padx=(8 if width == 6 else 4), pady=6)

    # =========================================================
    # 2. EVENT HISTORY & TIME MACHINE VIEW
    # =========================================================

    def _get_business_events(self):
        """Return all business events (excluding workspace file.* events)."""
        return [e for e in self.store.get_all() if not e.type.startswith("file.")]

    def _get_event_friendly_impact(self, event, state_before=None, state_after=None):
        """Generate human-readable impact explanation for an event."""
        etype = event.type
        data = event.data
        uid = data.get("user_id", "System")

        if etype == "user.created":
            return f"Registered user '{data.get('name', 'User')}' ({data.get('email', '')}, age {data.get('age', '')}). Initial wallet: ₹0.00."

        if etype == "balance.added":
            amt = data.get("amount", 0.0)
            bal_before = state_before.get("users", {}).get(uid, {}).get("balance") if state_before else None
            bal_after = state_after.get("users", {}).get(uid, {}).get("balance") if state_after else None

            if bal_before is not None and bal_after is not None:
                if bal_before < 0:
                    return f"Topped up ₹{amt:.2f} for {uid}. Balance changed from -₹{abs(bal_before):.2f} ➔ ₹{bal_after:.2f} (cleared ₹{abs(bal_before):.2f} overdraft deficit)."
                return f"Topped up ₹{amt:.2f} for {uid}. Balance changed from ₹{bal_before:.2f} ➔ ₹{bal_after:.2f}."
            elif bal_after is not None:
                return f"Topped up ₹{amt:.2f} into wallet for {uid}. Resulting balance: ₹{bal_after:.2f}."
            return f"Topped up ₹{amt:.2f} into wallet for {uid}."

        if etype == "order.created":
            return f"Created order {data.get('order_id', 'Order')} for ₹{data.get('amount', 0.0):.2f} (pending) for {uid}."

        if etype == "payment.completed":
            amt = data.get("amount", 0.0)
            method = data.get("method", "UPI")
            bal_before = state_before.get("users", {}).get(uid, {}).get("balance") if state_before else None
            bal_after = state_after.get("users", {}).get(uid, {}).get("balance") if state_after else None

            if bal_before is not None and bal_after is not None:
                if bal_after < 0:
                    return f"Paid ₹{amt:.2f} via {method} for {uid}. Balance changed from ₹{bal_before:.2f} ➔ -₹{abs(bal_after):.2f} (overdrawn by ₹{abs(bal_after):.2f})."
                return f"Paid ₹{amt:.2f} via {method} for {uid}. Balance changed from ₹{bal_before:.2f} ➔ ₹{bal_after:.2f}."
            return f"Processed payment of ₹{amt:.2f} via {method} for {uid}."

        if etype == "profile.updated":
            return f"Updated profile for {uid}: Name='{data.get('name', '')}', City='{data.get('city', '')}'."
        if etype == "status.changed":
            return f"Changed account status for {uid} to '{data.get('status', 'active')}'."
        if etype == "order.updated":
            return f"Updated order {data.get('order_id', 'active order')} status to '{data.get('status', 'paid')}'."
        if etype == "state.restored":
            return f"Restored historical application state from Step #{data.get('source_event_number', '?')}."
        if etype == "user.deleted":
            return f"Marked user {uid} as deleted in the immutable ledger."

        return f"Dispatched {etype} with data: {data}"

    def show_event_history(self):
        self._clear_main_area()

        self.make_label(
            self.main_container, text="EVENT HISTORY & TIME MACHINE", size=22, bold=True
        ).pack(anchor="w", pady=(10, 2))
        self.make_label(
            self.main_container,
            text="Immutable chronological transaction ledger. Filter by user or launch Time Machine above to step through historical state.",
            fg=self.MUTED_COLOR,
            size=11,
        ).pack(anchor="w", pady=(0, 14))

        # How it works card
        explainer_card = self.make_card(self.main_container, highlightbackground=self.ACCENT_COLOR)
        explainer_card.pack(fill="x", pady=(0, 16))

        ex_inner = tk.Frame(explainer_card, bg=self.CARD_COLOR)
        ex_inner.pack(fill="x", padx=20, pady=12)

        self.make_label(
            ex_inner,
            text="💡  HOW EVENT HISTORY & TIME MACHINE WORK",
            fg=self.ACCENT_COLOR,
            size=11,
            bold=True,
        ).pack(anchor="w", pady=(0, 4))
        self.make_label(
            ex_inner,
            text="• Ledger: Every action (user creation, wallet top-up, order, payment) is recorded as a permanent event step.\n"
            "• Time Travel: Click 'LAUNCH TIME MACHINE (STEP-BY-STEP REPLAY)' above to step back in time and inspect live balances & orders.\n"
            "• Invariant Diagnostics: Automatically checks if any action broke business rules (e.g. negative balances or overspending).",
            size=9,
            justify="left",
        ).pack(anchor="w")

        business_events = self._get_business_events()
        if not business_events:
            card = self.make_card(self.main_container)
            card.pack(fill="both", expand=True, pady=(0, 24))
            self.make_label(
                card,
                text="No business events recorded yet. Go to 'EVENT SIMULATOR' to create users, top-up wallets, or place orders.",
                fg=self.MUTED_COLOR,
                size=11,
            ).pack(pady=40)
            return

        all_users = self.simulator.get_all_users()
        active_users = self.simulator.get_active_users()
        ex_users = self.simulator.get_ex_users()
        ex_uids = {u["user_id"] for u in ex_users}
        active_user = self.history_user_filter_var.get()
        active_date = self.history_date_filter_var.get()

        # Filter card
        filter_card = self.make_card(self.main_container)
        filter_card.pack(fill="x", pady=(0, 14))

        filter_panel = tk.Frame(filter_card, bg=self.CARD_COLOR)
        filter_panel.pack(fill="x", padx=20, pady=12)

        # Row 1: Select user filter
        user_row = tk.Frame(filter_panel, bg=self.CARD_COLOR)
        user_row.pack(fill="x", pady=(0, 8))

        self.make_label(
            user_row, text="👤 1. SELECT USER:", fg=self.ACCENT_COLOR, size=10, bold=True, width=18, anchor="w"
        ).pack(side="left", padx=(0, 8))

        user_btn_specs = [("ALL USERS", "ALL")] + [(f"{u['user_id']} ({u['name']})", u["user_id"]) for u in active_users]
        if ex_users:
            ex_event_count = len([e for e in business_events if e.data.get("user_id") in ex_uids])
            user_btn_specs.append((f"📁 OTHER (Ex-Users: {len(ex_users)} | {ex_event_count} Evt)", "EX_USERS"))

        for label, val in user_btn_specs:
            is_act = active_user == val
            self.make_button(
                user_row,
                text=label,
                bg=self.ACCENT_COLOR if is_act else self.BUTTON_COLOR,
                fg="#07111f" if is_act else self.TEXT_COLOR,
                padx=10,
                pady=4,
                command=lambda t=val: self._set_user_filter(t),
            ).pack(side="left", padx=3)

        # Row 2: Select date filter
        date_row = tk.Frame(filter_panel, bg=self.CARD_COLOR)
        date_row.pack(fill="x", pady=(4, 6))

        self.make_label(
            date_row, text="📅 2. SELECT DATE:", fg=self.ACCENT_COLOR, size=10, bold=True, width=18, anchor="w"
        ).pack(side="left", padx=(0, 8))

        events_for_user = [
            e for e in business_events
            if active_user == "ALL"
            or (active_user == "EX_USERS" and e.data.get("user_id") in ex_uids)
            or e.data.get("user_id") == active_user
        ]
        date_counts = {}
        for e in events_for_user:
            d_str = self._get_event_local_date(e)
            date_counts[d_str] = date_counts.get(d_str, 0) + 1

        if active_date != "ALL" and active_date not in date_counts:
            active_date = "ALL"
            self.history_date_filter_var.set("ALL")

        date_btn_specs = [(f"ALL DATES ({len(events_for_user)})", "ALL")] + [
            (f"📅 {d} ({date_counts[d]})", d) for d in sorted(date_counts.keys(), reverse=True)
        ]
        for label, val in date_btn_specs:
            is_act = active_date == val
            self.make_button(
                date_row,
                text=label,
                bg=self.ACCENT_COLOR if is_act else self.BUTTON_COLOR,
                fg="#07111f" if is_act else self.TEXT_COLOR,
                padx=10,
                pady=4,
                command=lambda t=val: self._set_date_filter(t),
            ).pack(side="left", padx=3)

        # Row 3: Active Filters & Reset Button
        if active_user != "ALL" or active_date != "ALL":
            summary_row = tk.Frame(filter_panel, bg=self.CARD_COLOR)
            summary_row.pack(fill="x", pady=(8, 0))

            f_texts = []
            if active_user != "ALL":
                u_obj = next((u for u in all_users if u["user_id"] == active_user), None)
                f_texts.append(f"User: {active_user} ({u_obj['name']})" if u_obj else f"User: {active_user}")
            if active_date != "ALL":
                f_texts.append(f"Date: {active_date}")

            self.make_label(
                summary_row,
                text="🔎 Active Filters: " + "  |  ".join(f_texts),
                fg=self.SUCCESS_COLOR,
                size=9,
                bold=True,
            ).pack(side="left", padx=(4, 12))

            self.make_button(
                summary_row,
                text="🔄 RESET ALL FILTERS",
                bg="#334155",
                active_bg="#475569",
                padx=10,
                pady=3,
                size=8,
                command=self._reset_history_filters,
            ).pack(side="left")

        # User Storage Summary Box
        if active_user != "ALL":
            user_info = next((u for u in all_users if u["user_id"] == active_user), None)
            if user_info:
                state = self.replay_engine.replay_with_engine()[1].get_state()
                bal = state.get("users", {}).get(active_user, {}).get("balance", 0.0)
                u_events = [e for e in business_events if e.data.get("user_id") == active_user]
                u_orders = [o for o in state.get("orders", {}).values() if o.get("user_id") == active_user]

                user_summary_box = self.make_card(self.main_container, bg=self.INPUT_COLOR)
                user_summary_box.pack(fill="x", pady=(0, 14))

                sum_inner = tk.Frame(user_summary_box, bg=self.INPUT_COLOR)
                sum_inner.pack(fill="x", padx=18, pady=10)

                self.make_label(
                    sum_inner,
                    text=f"📂 USER CONTEXT: {user_info['user_id']} ({user_info['name']})",
                    bg=self.INPUT_COLOR,
                    fg=self.ACCENT_COLOR,
                    size=11,
                    bold=True,
                ).pack(side="left")

                bal_color = self.SUCCESS_COLOR if bal >= 0 else self.ERROR_COLOR
                self.make_label(
                    sum_inner,
                    text=f"Email: {user_info['email']}  |  Total User Events: {len(u_events)}  |  Orders: {len(u_orders)}  |  Wallet Balance: ₹{bal:.2f}",
                    bg=self.INPUT_COLOR,
                    fg=bal_color if bal < 0 else self.TEXT_COLOR,
                    size=10,
                    bold=True,
                ).pack(side="right")

        # Main Timeline Card
        card = self.make_card(self.main_container)
        card.pack(fill="both", expand=True, pady=(0, 24))

        top_timeline_bar = tk.Frame(card, bg=self.CARD_COLOR)
        top_timeline_bar.pack(fill="x", padx=20, pady=(18, 10))

        self.make_label(
            top_timeline_bar, text="CHRONOLOGICAL EVENT STREAM", fg=self.ACCENT_COLOR, size=14, bold=True
        ).pack(side="left")

        user_tm_label = f"FOR {active_user}" if active_user != "ALL" else "ALL USERS"
        self.make_accent_button(
            top_timeline_bar,
            text=f"⏱  LAUNCH TIME MACHINE ({user_tm_label})",
            padx=18,
            pady=8,
            size=10,
            command=lambda: self.show_time_machine(user_id=active_user),
        ).pack(side="right")

        # Header columns
        header = tk.Frame(card, bg=self.CARD_COLOR)
        header.pack(fill="x", padx=20, pady=(4, 6))

        for col, (text, width) in enumerate(
            [
                ("STEP", 6),
                ("USER", 16),
                ("EVENT TYPE", 18),
                ("ACTION & IMPACT", 34),
                ("TIME", 12),
                ("ACTIONS", 22),
            ]
        ):
            self.make_label(
                header, text=text, width=width, anchor="w", fg=self.MUTED_COLOR, size=9, bold=True
            ).grid(row=0, column=col, padx=4, pady=4)

        invalid_map = {d["event_index"]: d for d in self.replay_engine.get_all_diagnostics() if not d.get("is_valid")}

        state_engine = StateEngine()
        step_states = {}
        for idx, ev in enumerate(business_events, start=1):
            s_before = deepcopy(state_engine.get_state())
            state_engine.apply(ev)
            s_after = deepcopy(state_engine.get_state())
            step_states[idx] = (s_before, s_after)

        displayed_events = [
            (idx, e)
            for idx, e in enumerate(business_events, start=1)
            if (
                active_user == "ALL"
                or (active_user == "EX_USERS" and e.data.get("user_id") in ex_uids)
                or e.data.get("user_id") == active_user
            )
            and (active_date == "ALL" or self._get_event_local_date(e) == active_date)
        ]

        if not displayed_events:
            self.make_label(
                card, text="No events found for the selected filter.", fg=self.MUTED_COLOR, size=10
            ).pack(pady=20)
            return

        for index, event in displayed_events:
            is_invalid = index in invalid_map
            row_border = self.ERROR_COLOR if is_invalid else self.BORDER_COLOR
            row_bg = "#1f1422" if is_invalid else self.CARD_COLOR

            row = self.make_card(card, bg=row_bg, highlightbackground=row_border)
            row.pack(fill="x", padx=20, pady=3)

            ts = self._get_event_local_time(event)
            raw_uid = event.data.get("user_id", "System")
            is_ex = raw_uid in ex_uids
            ex_obj = next((u for u in ex_users if u["user_id"] == raw_uid), None)

            if is_ex:
                user_display = f"Ex-User: {ex_obj['name'] if ex_obj else raw_uid} ({raw_uid})"
            elif "name" in event.data and event.type == "user.created":
                user_display = f"{raw_uid} ({event.data['name']})"
            else:
                user_display = raw_uid

            s_before, s_after = step_states.get(index, (None, None))
            impact_text = self._get_event_friendly_impact(event, s_before, s_after)
            if is_invalid:
                impact_text = "❌ INVALID: " + impact_text

            for text, width, fg, bold in [
                (f"#{index}", 6, self.MUTED_COLOR, True),
                (user_display, 16, self.ACCENT_COLOR, True),
                (event.type, 18, self.ERROR_COLOR if is_invalid else self.TEXT_COLOR, True),
                (impact_text, 34, self.ERROR_COLOR if is_invalid else self.TEXT_COLOR, is_invalid),
                (ts, 12, self.MUTED_COLOR, False),
            ]:
                self.make_label(
                    row,
                    text=text,
                    width=width,
                    anchor="w",
                    bg=row_bg,
                    fg=fg,
                    size=10 if width == 18 else 9,
                    bold=bold,
                ).pack(side="left", padx=(8 if width == 6 else 4), pady=8)

            action_box = tk.Frame(row, bg=row_bg)
            action_box.pack(side="right", padx=10, pady=6)

            self.make_accent_button(
                action_box,
                text="⏱ REPLAY",
                padx=8,
                pady=4,
                size=8,
                command=lambda e=event: self.show_time_machine(target_event_id=e.id, user_id=active_user),
            ).pack(side="left", padx=(0, 6))

            self.make_button(
                action_box,
                text="🔍 PAYLOAD",
                padx=8,
                pady=4,
                size=8,
                command=lambda e=event, n=index: self.view_event(e, n),
            ).pack(side="left")

    def _set_user_filter(self, user_filter):
        self.history_user_filter_var.set(user_filter)
        self.history_date_filter_var.set("ALL")
        self.show_event_history()

    def _set_date_filter(self, date_filter):
        self.history_date_filter_var.set(date_filter)
        self.show_event_history()

    def _reset_history_filters(self):
        self.history_user_filter_var.set("ALL")
        self.history_date_filter_var.set("ALL")
        self.show_event_history()

    def view_event(self, event, event_number=None):
        data_text = "\n".join(f"  {k}: {v}" for k, v in event.data.items())
        header = f"Event #{event_number}" if event_number else "Event Metadata"
        messagebox.showinfo(
            header,
            f"Event ID: {event.id}\nType: {event.type}\nVersion: {event.version}\nTimestamp: {event.timestamp}\n\nPayload Data:\n{data_text}",
        )

    # =========================================================
    # TIME MACHINE VIEW (STEP-BY-STEP REPLAY)
    # =========================================================

    def show_time_machine(self, event_number=None, user_id=None, target_event_id=None):
        self._clear_main_area()
        all_business_events = self._get_business_events()
        if not all_business_events:
            self.show_event_history()
            return

        all_users = self.simulator.get_all_users()
        active_users = self.simulator.get_active_users()
        ex_users = self.simulator.get_ex_users()
        ex_uids = {u["user_id"] for u in ex_users}
        valid_uids = [u["user_id"] for u in all_users]

        user_id = user_id or self.history_user_filter_var.get()
        if user_id not in ["ALL", "EX_USERS"] + valid_uids:
            user_id = "ALL"

        if user_id == "EX_USERS":
            scoped_events = [e for e in all_business_events if e.data.get("user_id") in ex_uids] or all_business_events
        elif user_id != "ALL":
            scoped_events = [e for e in all_business_events if e.data.get("user_id") == user_id] or all_business_events
        else:
            scoped_events = all_business_events

        total_scoped_events = len(scoped_events)

        if target_event_id:
            matched_idx = next((i for i, e in enumerate(scoped_events, 1) if e.id == target_event_id), None)
            if matched_idx is not None:
                step_index, target_event = matched_idx, scoped_events[matched_idx - 1]
            else:
                all_idx = next((i for i, e in enumerate(all_business_events, 1) if e.id == target_event_id), None)
                if all_idx is not None:
                    user_id = "ALL"
                    scoped_events = all_business_events
                    total_scoped_events = len(scoped_events)
                    step_index, target_event = all_idx, scoped_events[all_idx - 1]
                else:
                    step_index, target_event = total_scoped_events, scoped_events[-1]
        elif event_number is not None:
            step_index = max(1, min(event_number, total_scoped_events))
            target_event = scoped_events[step_index - 1]
        else:
            step_index = total_scoped_events
            target_event = scoped_events[-1]

        state_at_step = self.replay_engine.replay_until_event_id(target_event.id)
        state_before = self.replay_engine.replay_before_event_id(target_event.id)
        abs_index = next((i for i, e in enumerate(all_business_events, 1) if e.id == target_event.id), step_index)

        self.make_label(self.main_container, text="TIME MACHINE", size=22, bold=True).pack(
            anchor="w", pady=(10, 2)
        )
        self.make_label(
            self.main_container,
            text="Interactive step-by-step state replayer. Rebuilds the exact state of users, wallets, and orders as they existed at this precise moment in time.",
            fg=self.MUTED_COLOR,
            size=11,
        ).pack(anchor="w", pady=(0, 14))

        # Scope selector
        user_selector_card = self.make_card(self.main_container)
        user_selector_card.pack(fill="x", pady=(0, 14))

        user_sel_inner = tk.Frame(user_selector_card, bg=self.CARD_COLOR)
        user_sel_inner.pack(fill="x", padx=20, pady=10)

        self.make_label(
            user_sel_inner, text="👤 SELECT TIMELINE USER:", fg=self.ACCENT_COLOR, size=10, bold=True, width=22, anchor="w"
        ).pack(side="left", padx=(0, 8))

        tm_scope_specs = [(f"ALL USERS ({len(all_business_events)})", "ALL")] + [
            (
                f"{u['user_id']} ({u['name']}) [{len([e for e in all_business_events if e.data.get('user_id') == u['user_id']])}]",
                u["user_id"],
            )
            for u in active_users
        ]
        if ex_users:
            ex_event_count = len([e for e in all_business_events if e.data.get("user_id") in ex_uids])
            tm_scope_specs.append((f"📁 OTHER (Ex-Users: {len(ex_users)} | {ex_event_count} Evt)", "EX_USERS"))

        for label, val in tm_scope_specs:
            is_act = user_id == val
            self.make_button(
                user_sel_inner,
                text=label,
                bg=self.ACCENT_COLOR if is_act else self.BUTTON_COLOR,
                fg="#07111f" if is_act else self.TEXT_COLOR,
                padx=10,
                pady=4,
                command=lambda t=val: self.show_time_machine(user_id=t),
            ).pack(side="left", padx=3)

        # Controls & Playback Card
        nav_card = self.make_card(self.main_container)
        nav_card.pack(fill="x", pady=(0, 16))

        top_info = tk.Frame(nav_card, bg=self.CARD_COLOR)
        top_info.pack(fill="x", padx=24, pady=(16, 10))

        u_name_str = ""
        if user_id == "EX_USERS":
            replay_heading = f"📁 EX-USERS / OTHER ─ STEP #{step_index} OF {total_scoped_events} : {target_event.type.upper()}"
        elif user_id != "ALL":
            u_obj = next((u for u in all_users if u["user_id"] == user_id), None)
            u_name_str = f" ({u_obj['name']})" if u_obj else ""
            replay_heading = f"👤 USER {user_id}{u_name_str} ─ STEP #{step_index} OF {total_scoped_events} : {target_event.type.upper()}"
        else:
            replay_heading = f"🌐 GLOBAL STEP #{step_index} OF {total_scoped_events} : {target_event.type.upper()}"

        self.make_label(top_info, text=replay_heading, fg=self.ACCENT_COLOR, size=13, bold=True).pack(side="left")
        self.make_button(top_info, text="📋 BACK TO TIMELINE", padx=12, pady=4, command=self.show_event_history).pack(side="right")

        # Step Progress Dots
        timeline_bar = tk.Frame(nav_card, bg=self.INPUT_COLOR)
        timeline_bar.pack(fill="x", padx=24, pady=(0, 14), ipady=6)

        window_start = max(1, step_index - 3)
        window_end = min(total_scoped_events, step_index + 3)
        timeline_steps = [
            f"● Step #{i} ({scoped_events[i-1].type.split('.')[-1]})"
            if i == step_index
            else f"Step #{i} ({scoped_events[i-1].type.split('.')[-1]})"
            for i in range(window_start, window_end + 1)
        ]
        step_display = ("… ─── " if window_start > 1 else "") + " ─── ".join(timeline_steps) + (" ─── …" if window_end < total_scoped_events else "")
        self.make_label(timeline_bar, text=step_display, bg=self.INPUT_COLOR, fg=self.ACCENT_COLOR, size=10, bold=True).pack(pady=4)

        # Player buttons
        controls_frame = tk.Frame(nav_card, bg=self.CARD_COLOR)
        controls_frame.pack(fill="x", padx=24, pady=(0, 18))

        nav_buttons = [
            ("⏮ First (#1)", 1, step_index > 1),
            ("◀ Previous", max(1, step_index - 1), step_index > 1),
            ("Next ▶", min(total_scoped_events, step_index + 1), step_index < total_scoped_events),
            (f"Latest (#{total_scoped_events}) ⏭", total_scoped_events, step_index < total_scoped_events),
        ]
        for btn_text, target_step, enabled in nav_buttons:
            b = self.make_button(
                controls_frame,
                text=btn_text,
                padx=12,
                pady=6,
                cursor="hand2" if enabled else "arrow",
                command=lambda s=target_step: self.show_time_machine(s, user_id=user_id),
            )
            b.pack(side="left", padx=(0, 16 if "Latest" in btn_text else 6))
            if not enabled:
                b.configure(state="disabled", bg=self.INPUT_COLOR, fg=self.MUTED_COLOR)

        # Jump dropdown
        jump_frame = tk.Frame(controls_frame, bg=self.CARD_COLOR)
        jump_frame.pack(side="left")
        self.make_label(jump_frame, text="Jump To:", fg=self.MUTED_COLOR, size=9, bold=True).pack(side="left", padx=(0, 6))

        jump_options = [f"Step #{idx}: {ev.type}" for idx, ev in enumerate(scoped_events, 1)]
        jump_var = tk.StringVar(value=f"Step #{step_index}: {target_event.type}")
        self.make_dropdown(
            jump_frame,
            values=jump_options,
            textvariable=jump_var,
            command=lambda val: self.show_time_machine(
                int(val.split(":")[0].replace("Step #", "").strip()), user_id=user_id
            ),
            font=("Segoe UI", 9),
            width=24,
        ).pack(side="left")

        # Action Buttons
        if step_index < total_scoped_events:
            action_btn_box = tk.Frame(controls_frame, bg=self.CARD_COLOR)
            action_btn_box.pack(side="right")

            self.make_accent_button(
                action_btn_box,
                text=f"⏪ REWIND TO STEP #{step_index}",
                padx=12,
                pady=6,
                command=lambda: self._rewind_to_event(target_event.id, user_id),
            ).pack(side="left", padx=(0, 6))

            self.make_button(
                action_btn_box,
                text="🔄 RESTORE (APPEND-ONLY)",
                bg="#0284c7",
                fg="#ffffff",
                active_bg="#38bdf8",
                active_fg="#07111f",
                padx=12,
                pady=6,
                command=lambda: self._restore_state_from_event(target_event.id, abs_index),
            ).pack(side="left")
        else:
            self.make_accent_button(
                controls_frame, text="⚡ SIMULATE NEW EVENT", padx=14, pady=6, command=self.show_dashboard
            ).pack(side="right")

        # What Changed card
        impact_card = self.make_card(self.main_container, bg=self.INPUT_COLOR)
        impact_card.pack(fill="x", pady=(0, 16))

        imp_inner = tk.Frame(impact_card, bg=self.INPUT_COLOR)
        imp_inner.pack(fill="x", padx=20, pady=12)

        self.make_label(
            imp_inner, text="⚡  WHAT CHANGED AT THIS STEP", bg=self.INPUT_COLOR, fg=self.ACCENT_COLOR, size=10, bold=True
        ).pack(anchor="w")

        friendly_impact = self._get_event_friendly_impact(target_event, state_before, state_at_step)
        self.make_label(
            imp_inner,
            text=f"Event #{abs_index} ({target_event.type}): {friendly_impact}",
            bg=self.INPUT_COLOR,
            size=11,
            wraplength=1050,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        # Diagnostics card
        diag = self.replay_engine.get_diagnostics_for_event_id(target_event.id)
        if not diag.get("is_valid", True):
            warn_card = self.make_card(
                self.main_container, bg="#260f1b", highlightbackground=self.ERROR_COLOR, highlightthickness=2
            )
            warn_card.pack(fill="x", pady=(0, 16))

            w_inner = tk.Frame(warn_card, bg="#260f1b")
            w_inner.pack(fill="x", padx=20, pady=14)

            self.make_label(
                w_inner, text="❌  SYSTEM INVARIANT VIOLATION DETECTED", bg="#260f1b", fg=self.ERROR_COLOR, size=13, bold=True
            ).pack(anchor="w")

            reason_str = diag.get("reason", "Invariant violated.")
            if "deficit" in diag:
                reason_str += f" (Deficit: ₹{diag['deficit']:.2f}, Balance before: ₹{diag['balance_before']:.2f})"

            self.make_label(
                w_inner,
                text=f"This event resulted in an invalid state: {reason_str}\nChronoReplay identified this invariant violation deterministically during state replay.",
                bg="#260f1b",
                fg="#fca5a5",
                size=10,
                justify="left",
            ).pack(anchor="w", pady=(4, 0))
        else:
            ok_card = self.make_card(self.main_container, highlightbackground=self.SUCCESS_COLOR)
            ok_card.pack(fill="x", pady=(0, 16))

            ok_inner = tk.Frame(ok_card, bg=self.CARD_COLOR)
            ok_inner.pack(fill="x", padx=20, pady=8)

            self.make_label(
                ok_inner,
                text="✓  SYSTEM STATE INTEGRITY: VALID (All wallet invariants & order consistency rules passed at this step)",
                fg=self.SUCCESS_COLOR,
                size=10,
                bold=True,
            ).pack(side="left")

        # Visual Dashboard Cards
        users = state_at_step.get("users", {})
        orders = state_at_step.get("orders", {})
        payments = state_at_step.get("payments", [])

        display_orders = {oid: o for oid, o in orders.items() if o.get("user_id") == user_id} if user_id != "ALL" else orders
        display_payments = [p for p in payments if p.get("user_id") == user_id] if user_id != "ALL" else payments

        state_dashboard = tk.Frame(self.main_container, bg=self.BG_COLOR)
        state_dashboard.pack(fill="x", pady=(0, 16))

        # Left Column: User Wallets
        left_col = self.make_card(state_dashboard)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 8))

        wallets_title = f"👤 USER WALLETS ({len(users)})" if user_id == "ALL" else f"👤 USER WALLET: {user_id}"
        self.make_label(left_col, text=wallets_title, fg=self.ACCENT_COLOR, size=12, bold=True).pack(
            anchor="w", padx=16, pady=(14, 10)
        )

        if users:
            sorted_uids = list(users.keys())
            if user_id != "ALL" and user_id in users:
                sorted_uids.remove(user_id)
                sorted_uids.insert(0, user_id)

            for uid in sorted_uids:
                user = users[uid]
                is_del = user.get("status") == "deleted" or user.get("deleted")
                is_scoped = user_id != "ALL" and uid == user_id
                card_bg = "#1a131b" if is_del else ("#132338" if is_scoped else self.INPUT_COLOR)
                border_col = "#f59e0b" if is_del else (self.ACCENT_COLOR if is_scoped else self.BORDER_COLOR)
                u_card = self.make_card(left_col, bg=card_bg, highlightbackground=border_col)
                u_card.pack(fill="x", padx=14, pady=4)

                u_top = tk.Frame(u_card, bg=card_bg)
                u_top.pack(fill="x", padx=12, pady=(8, 4))

                scope_badge = " [SELECTED] " if is_scoped else ""
                name_prefix = "Ex-User: " if is_del else ""
                name_color = "#fca5a5" if is_del else (self.ACCENT_COLOR if is_scoped else self.TEXT_COLOR)
                self.make_label(
                    u_top,
                    text=f"{name_prefix}{user.get('name', 'User')} ({uid}){scope_badge}",
                    bg=card_bg,
                    fg=name_color,
                    size=11,
                    bold=True,
                ).pack(side="left")

                bal = user.get("balance", 0.0)
                self.make_label(
                    u_top,
                    text=f"₹{bal:.2f}",
                    bg=card_bg,
                    fg=self.MUTED_COLOR if is_del else (self.SUCCESS_COLOR if bal >= 0 else self.ERROR_COLOR),
                    size=13,
                    bold=True,
                ).pack(side="right")

                u_bot = tk.Frame(u_card, bg=card_bg)
                u_bot.pack(fill="x", padx=12, pady=(0, 8))
                status_txt = "DELETED (EX-USER)" if is_del else user.get("status", "active").upper()
                self.make_label(
                    u_bot,
                    text=f"Email: {user.get('email', 'N/A')}  •  Status: {status_txt}",
                    bg=card_bg,
                    fg="#f59e0b" if is_del else self.MUTED_COLOR,
                    size=9,
                ).pack(side="left")
        else:
            self.make_label(left_col, text="No users created as of this step.", fg=self.MUTED_COLOR, size=10).pack(padx=16, pady=20)

        # Right Column: Orders & Payments
        right_col = self.make_card(state_dashboard)
        right_col.pack(side="left", fill="both", expand=True, padx=(8, 0))

        orders_title = (
            f"📦 ORDERS ({len(display_orders)}) & PAYMENTS ({len(display_payments)})"
            if user_id == "ALL"
            else f"📦 {user_id} ORDERS ({len(display_orders)}) & PAYMENTS ({len(display_payments)})"
        )
        self.make_label(right_col, text=orders_title, fg=self.ACCENT_COLOR, size=12, bold=True).pack(
            anchor="w", padx=16, pady=(14, 10)
        )

        if display_orders:
            for oid, order in display_orders.items():
                o_card = self.make_card(right_col, bg=self.INPUT_COLOR)
                o_card.pack(fill="x", padx=14, pady=4)

                o_top = tk.Frame(o_card, bg=self.INPUT_COLOR)
                o_top.pack(fill="x", padx=12, pady=(8, 4))

                self.make_label(o_top, text=f"Order {oid} ({order.get('user_id', '')})", bg=self.INPUT_COLOR, size=10, bold=True).pack(side="left")

                amt = order.get("amount", 0.0)
                st = order.get("status", "pending").upper()
                st_color = self.SUCCESS_COLOR if st in ["PAID", "COMPLETED"] else self.WARNING_COLOR
                self.make_label(o_top, text=f"₹{amt:.2f}  [{st}]", bg=self.INPUT_COLOR, fg=st_color, size=10, bold=True).pack(side="right")
        else:
            self.make_label(right_col, text="No orders recorded as of this step.", fg=self.MUTED_COLOR, size=10).pack(padx=16, pady=20)

        # Raw State Inspection Text Area
        raw_card = self.make_card(self.main_container)
        raw_card.pack(fill="both", expand=True, pady=(0, 24))

        raw_top = tk.Frame(raw_card, bg=self.CARD_COLOR)
        raw_top.pack(fill="x", padx=20, pady=(14, 6))

        user_focus_str = f" ─ FOCUSED USER: {user_id}" if user_id != "ALL" else ""
        self.make_label(
            raw_top,
            text=f"🔍 COMPLETE RECONSTRUCTED STATE SNAPSHOT (STEP #{abs_index}){user_focus_str}",
            fg=self.MUTED_COLOR,
            size=10,
            bold=True,
        ).pack(side="left")

        state_frame = tk.Frame(raw_card, bg=self.INPUT_COLOR)
        state_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        scroll = tk.Scrollbar(state_frame, bg=self.INPUT_COLOR)
        scroll.pack(side="right", fill="y")

        self.replay_state_text = tk.Text(
            state_frame,
            bg=self.INPUT_COLOR,
            fg=self.TEXT_COLOR,
            insertbackground=self.TEXT_COLOR,
            relief="flat",
            font=("Consolas", 9),
            wrap="word",
            height=14,
            yscrollcommand=scroll.set,
        )
        self.replay_state_text.pack(fill="both", expand=True, padx=(10, 0), pady=8)
        scroll.config(command=self.replay_state_text.yview)

        self._display_replay_state(state_at_step, abs_index, selected_user_id=user_id)

    def _display_replay_state(self, state, event_number, selected_user_id="ALL"):
        self.replay_state_text.configure(state="normal")
        self.replay_state_text.delete("1.0", "end")

        users = state.get("users", {})
        orders = state.get("orders", {})
        payments = state.get("payments", [])

        total_balance = sum(u.get("balance", 0) for u in users.values())
        scope_info = f"  |  Focused User: {selected_user_id}" if selected_user_id != "ALL" else ""
        summary = (
            f"STATE SNAPSHOT #{event_number}  |  Users: {len(users)}  |  Orders: {len(orders)}  |  "
            f"Payments: {len(payments)}  |  Total System Wallet Balance: ₹{total_balance:.2f}{scope_info}\n"
            + "=" * 76
            + "\n\n"
        )
        self.replay_state_text.insert("end", summary)

        # Focused User Highlight
        if selected_user_id != "ALL" and selected_user_id in users:
            sel_u = users[selected_user_id]
            sel_bal = sel_u.get("balance", 0.0)
            sel_orders = [o for o in orders.values() if o.get("user_id") == selected_user_id]
            sel_pmts = [p for p in payments if p.get("user_id") == selected_user_id]
            self.replay_state_text.insert(
                "end",
                f"🎯 FOCUSED USER SNAPSHOT: {sel_u.get('name', 'User')} ({selected_user_id})\n"
                f"────────────────────────────────────────────────────────────────────────────\n"
                f"  • Name   : {sel_u.get('name', '')}\n"
                f"  • Email  : {sel_u.get('email', '')}\n"
                f"  • Status : {sel_u.get('status', 'active').upper()}\n"
                f"  • Balance: ₹{sel_bal:.2f}\n"
                f"  • Orders : {len(sel_orders)} order(s)\n"
                f"  • Payments: {len(sel_pmts)} transaction(s)\n\n",
            )

        self.replay_state_text.insert(
            "end", "USERS & WALLETS\n────────────────────────────────────────────────────────────────────────────\n"
        )
        if users:
            sorted_uids = list(users.keys())
            if selected_user_id != "ALL" and selected_user_id in users:
                sorted_uids.remove(selected_user_id)
                sorted_uids.insert(0, selected_user_id)

            for uid in sorted_uids:
                u = users[uid]
                tag = "  [★ SELECTED USER]" if (selected_user_id != "ALL" and uid == selected_user_id) else ""
                self.replay_state_text.insert(
                    "end",
                    f"  • User: {u.get('name', '')} ({uid}){tag}\n"
                    f"    Email  : {u.get('email', '')}\n"
                    f"    Status : {u.get('status', 'active')}\n"
                    f"    Balance: ₹{u.get('balance', 0):.2f}\n\n",
                )
        else:
            self.replay_state_text.insert("end", "  No users in state.\n\n")

        self.replay_state_text.insert(
            "end", "ORDERS\n────────────────────────────────────────────────────────────────────────────\n"
        )
        if orders:
            sorted_orders = list(orders.items())
            if selected_user_id != "ALL":
                user_ords = [o for o in sorted_orders if o[1].get("user_id") == selected_user_id]
                other_ords = [o for o in sorted_orders if o[1].get("user_id") != selected_user_id]
                sorted_orders = user_ords + other_ords

            for oid, order in sorted_orders:
                is_u = selected_user_id != "ALL" and order.get("user_id") == selected_user_id
                tag = "  [★ SELECTED USER ORDER]" if is_u else ""
                self.replay_state_text.insert(
                    "end",
                    f"  • Order ID: {oid}{tag}\n"
                    f"    User   : {order.get('user_id', '')}\n"
                    f"    Amount : ₹{order.get('amount', 0):.2f}\n"
                    f"    Payment: ₹{order.get('paid_amount', 0.0):.2f}\n"
                    f"    Status : {order.get('status', 'pending')}\n\n",
                )
        else:
            self.replay_state_text.insert("end", "  No orders in state.\n\n")

        self.replay_state_text.insert(
            "end", "PAYMENTS\n────────────────────────────────────────────────────────────────────────────\n"
        )
        if payments:
            sorted_payments = list(payments)
            if selected_user_id != "ALL":
                user_pmts = [p for p in sorted_payments if p.get("user_id") == selected_user_id]
                other_pmts = [p for p in sorted_payments if p.get("user_id") != selected_user_id]
                sorted_payments = user_pmts + other_pmts

            for p in sorted_payments:
                is_u = selected_user_id != "ALL" and p.get("user_id") == selected_user_id
                tag = "  [★ SELECTED USER]" if is_u else ""
                ord_info = f" (Order: {p.get('order_id')})" if p.get("order_id") else ""
                self.replay_state_text.insert(
                    "end",
                    f"  • Payment: ₹{p.get('amount', 0):.2f} via {p.get('method', 'UPI')} (User: {p.get('user_id')}){ord_info} [{p.get('status', 'success').upper()}]{tag}\n",
                )
        else:
            self.replay_state_text.insert("end", "  No payments recorded.\n")

        self.replay_state_text.configure(state="disabled")

    def _rewind_to_event(self, target_event_id, user_id=None):
        target_event = self.store.get(target_event_id)
        if not target_event:
            return

        confirm = messagebox.askyesno(
            "Time Machine — Rewind",
            f"Are you sure you want to rewind the application state to event '{target_event.type}'?\n\n"
            f"The application state will be reconstructed exactly as it was at this point in time.\n\n"
            f"No events will be deleted. All subsequent events will remain safely stored in the Event Store.",
        )
        if confirm:
            state = self.replay_engine.replay_until_event_id(target_event.id)
            users = state.get("users", {})
            if users:
                target_uid = user_id if (user_id and user_id in users) else list(users.keys())[-1]
                u = users[target_uid]
                self.simulator.select_user(target_uid, u.get("name"), u.get("email"))

            messagebox.showinfo(
                "Time Machine — Rewind",
                f"Application state rewound to event '{target_event.type}'.\n\n"
                f"All events remain safely stored in the Event Store.\n"
                f"State reconstruction and simulator context updated.",
            )
            self.show_time_machine(target_event_id=target_event.id, user_id=user_id)

    def _restore_state_from_event(self, target_event_id, abs_step_number=None):
        target_event = self.store.get(target_event_id)
        if not target_event:
            return

        confirm = messagebox.askyesno(
            "Time Machine — Restore State",
            f"Are you sure you want to restore the application state from event '{target_event.type}'?\n\n"
            f"This will bring this historical state forward as the active state by appending an immutable 'state.restored' event to the Event Store.\n\n"
            f"No events will be deleted. All previous events remain safely stored in the Event Store.",
        )
        if confirm:
            all_store_events = self.store.get_all()
            exact_store_index = next(
                (i for i, e in enumerate(all_store_events, 1) if e.id == target_event.id),
                abs_step_number or 1,
            )

            target_uid = target_event.data.get("user_id", "System")
            restored_event = Event.create(
                event_type="state.restored",
                data={
                    "source_event_number": exact_store_index,
                    "source_event_id": target_event.id,
                    "source_event_type": target_event.type,
                    "user_id": target_uid,
                },
            )
            self.store.append(restored_event)

            state = self.replay_engine.replay_all()
            users = state.get("users", {})
            if target_uid in users:
                u = users[target_uid]
                self.simulator.select_user(target_uid, u.get("name"), u.get("email"))
                self.history_user_filter_var.set(target_uid)
            elif users:
                last_user_id = list(users.keys())[-1]
                last_user = users[last_user_id]
                self.simulator.select_user(last_user_id, last_user.get("name"), last_user.get("email"))
                self.history_user_filter_var.set(last_user_id)

            self.history_date_filter_var.set("ALL")

            messagebox.showinfo(
                "State Restored (Append-Only)",
                f"Successfully restored state from event '{target_event.type}'.\n\n"
                f"A new 'state.restored' event has been appended to the ledger.\n"
                f"The complete event history remains 100% immutable and intact.",
            )
            self.show_event_history()

    def _delete_events_permanently(self, target_event_id, user_id=None):
        target_event = self.store.get(target_event_id)
        if not target_event:
            return

        confirm = messagebox.askyesno(
            "Delete Events",
            f"This action will permanently remove all subsequent events after '{target_event.type}' from the Event Store.\n"
            f"This cannot be undone.\n\n"
            f"Are you sure you want to permanently delete all subsequent events?",
        )
        if confirm:
            deleted_count = self.store.delete_events_after(target_event.id)
            state = self.replay_engine.replay_until_event_id(target_event.id)
            users = state.get("users", {})
            if users:
                last_user_id = list(users.keys())[-1]
                last_user = users[last_user_id]
                self.simulator.select_user(last_user_id, last_user.get("name"), last_user.get("email"))
            messagebox.showinfo(
                "Events Deleted",
                f"Permanently removed {deleted_count} event(s) from the event store.",
            )
            self.show_dashboard()

    # =========================================================
    # 3. WORKSPACE & FILE RECOVERY VIEW
    # =========================================================

    def show_workspace(self):
        self._clear_main_area()

        self.make_label(
            self.main_container, text="WORKSPACE & FILE RECOVERY", size=22, bold=True
        ).pack(anchor="w", pady=(10, 2))
        self.make_label(
            self.main_container,
            text="File time machine with non-destructive restoration. Scan workspace to detect and record changes, inspect version history, and restore physical files.",
            fg=self.MUTED_COLOR,
            size=11,
        ).pack(anchor="w", pady=(0, 18))

        # Active workspace bar
        dir_card = self.make_card(self.main_container)
        dir_card.pack(fill="x", pady=(0, 18))

        self.make_label(
            dir_card, text="ACTIVE WORKSPACE DIRECTORY", fg=self.ACCENT_COLOR, size=14, bold=True
        ).pack(anchor="w", padx=24, pady=(18, 4))

        selector_frame = tk.Frame(dir_card, bg=self.CARD_COLOR)
        selector_frame.pack(fill="x", padx=24, pady=(0, 16))

        border = tk.Frame(selector_frame, bg=self.BORDER_COLOR)
        border.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.make_entry(border, textvariable=self.workspace_path_var).pack(
            fill="both", expand=True, padx=1, pady=1, ipady=5
        )

        self.make_button(
            selector_frame, text="SELECT WORKSPACE", padx=16, pady=6, command=self._browse_workspace_folder
        ).pack(side="left", padx=(0, 8))

        self.make_accent_button(
            selector_frame, text="SCAN WORKSPACE", padx=18, pady=6, command=self.scan_workspace
        ).pack(side="left", padx=(0, 8))

        self.make_button(
            selector_frame, text="REFRESH", padx=14, pady=6, command=self._populate_workspace_files
        ).pack(side="left")

        # Two-column layout
        columns_frame = tk.Frame(self.main_container, bg=self.BG_COLOR)
        columns_frame.pack(fill="both", expand=True, pady=(0, 24))

        left_card = self.make_card(columns_frame)
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.make_label(left_card, text="WORKSPACE FILES", fg=self.ACCENT_COLOR, size=13, bold=True).pack(
            anchor="w", padx=18, pady=(16, 4)
        )

        folder_name = os.path.basename(self.workspace_path_var.get()) or "workspace"
        self.make_label(left_card, text=f"📁 {folder_name}", size=11, bold=True).pack(
            anchor="w", padx=18, pady=(0, 10)
        )

        files_listbox_frame = tk.Frame(left_card, bg=self.INPUT_COLOR)
        files_listbox_frame.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        self.files_listbox = tk.Listbox(
            files_listbox_frame,
            bg=self.INPUT_COLOR,
            fg=self.TEXT_COLOR,
            selectbackground=self.BUTTON_ACTIVE,
            relief="flat",
            bd=0,
            font=("Consolas", 10),
        )
        self.files_listbox.pack(fill="both", expand=True, padx=8, pady=8)
        self.files_listbox.bind("<<ListboxSelect>>", self._on_workspace_file_selected)

        self.right_card = self.make_card(columns_frame)
        self.right_card.pack(side="right", fill="both", expand=True, padx=(10, 0))

        self.version_history_title = self.make_label(
            self.right_card, text="VERSION HISTORY", fg=self.ACCENT_COLOR, size=13, bold=True
        )
        self.version_history_title.pack(anchor="w", padx=18, pady=(16, 4))

        self.version_container = tk.Frame(self.right_card, bg=self.CARD_COLOR)
        self.version_container.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        self._populate_workspace_files()
        self._start_workspace_auto_watcher()

    def _start_workspace_auto_watcher(self):
        """Periodically check for filesystem changes in the workspace."""
        if hasattr(self, "_watcher_job") and self._watcher_job:
            try:
                self.root.after_cancel(self._watcher_job)
            except Exception:
                pass

        def _auto_sync_tick():
            try:
                if hasattr(self, "files_listbox") and self.files_listbox.winfo_exists():
                    summary = self.workspace_manager.scan_and_record_changes()
                    if summary.get("created", 0) > 0 or summary.get("modified", 0) > 0 or summary.get("deleted", 0) > 0:
                        self._populate_workspace_files()
                        if self.selected_workspace_file.get():
                            self._on_workspace_file_selected()
            except Exception:
                pass
            finally:
                self._watcher_job = self.root.after(1500, _auto_sync_tick)

        self._watcher_job = self.root.after(1500, _auto_sync_tick)

    def _browse_workspace_folder(self):
        folder = filedialog.askdirectory(initialdir=self.workspace_path_var.get())
        if folder:
            self._sync_workspace_path(folder)
            self.show_workspace()

    def scan_workspace(self):
        try:
            self._sync_workspace_path(self.workspace_path_var.get())
            summary = self.workspace_manager.scan_and_record_changes()
            self._populate_workspace_files()
            msg = (
                f"Scan Complete: {summary['total_scanned']} files scanned.\n"
                f"({summary['created']} Created, {summary['modified']} Modified, "
                f"{summary['unchanged']} Unchanged, {summary['deleted']} Deleted)"
            )
            messagebox.showinfo("Workspace Scan", msg)
            return summary
        except Exception as exc:
            messagebox.showerror("Scan Error", str(exc))

    def _populate_workspace_files(self):
        """Populate workspace files list with status indicators."""
        self.files_listbox.delete(0, "end")

        current_path = os.path.abspath(str(self.workspace_path_var.get()).strip())
        if current_path != self.workspace_manager.workspace_path:
            self._sync_workspace_path(current_path)

        file_statuses = self.workspace_manager.get_workspace_files_with_status()
        if not file_statuses:
            self.files_listbox.insert("end", "  (No files found. Click SCAN WORKSPACE)")
            return

        for item in file_statuses:
            path = item["file_path"]
            status = item["status"]
            icon = "📄" if item["is_on_disk"] else "🗑"
            self.files_listbox.insert("end", f"  {icon} {path}  [{status}]")

    def _on_workspace_file_selected(self, event=None):
        selection = self.files_listbox.curselection()
        if not selection:
            return

        raw_value = self.files_listbox.get(selection[0])
        clean_path = raw_value.replace("📄", "").replace("🗑", "").split("[")[0].strip()
        self.selected_workspace_file.set(clean_path)

        for widget in self.version_container.winfo_children():
            widget.destroy()

        self.version_history_title.configure(text=f"VERSION HISTORY: {clean_path}")

        try:
            history = self.version_history.get_file_history(clean_path, self.workspace_path)
        except ValueError as exc:
            self.make_label(self.version_container, text=str(exc), fg=self.ERROR_COLOR, size=10).pack(pady=20)
            return

        if not history:
            self.make_label(
                self.version_container,
                text="No historical versions recorded. Click [SCAN WORKSPACE] to track changes.",
                fg=self.MUTED_COLOR,
                size=10,
            ).pack(pady=20)
            return

        for version in history:
            row = self.make_card(self.version_container, bg=self.INPUT_COLOR)
            row.pack(fill="x", pady=3)

            ts = version.timestamp.split("T")[1].split("+")[0] if "T" in version.timestamp else version.timestamp

            if version.is_deleted():
                action_text, action_color = "DELETED", self.ERROR_COLOR
            elif version.event_type == "file.restored":
                action_text, action_color = "RESTORED", self.SUCCESS_COLOR
            elif version.event_type == "file.created":
                action_text, action_color = "CREATED", self.ACCENT_COLOR
            else:
                action_text, action_color = "MODIFIED", self.WARNING_COLOR

            info_frame = tk.Frame(row, bg=self.INPUT_COLOR)
            info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=8)

            self.make_label(
                info_frame,
                text=f"VERSION #{version.version}  •  {action_text}",
                bg=self.INPUT_COLOR,
                fg=action_color,
                size=9,
                bold=True,
            ).pack(anchor="w")

            self.make_label(
                info_frame,
                text=f"Time: {ts} | Snapshot: {version.snapshot_id or 'Deleted'}",
                bg=self.INPUT_COLOR,
                fg=self.MUTED_COLOR,
                size=8,
            ).pack(anchor="w", pady=(2, 0))

            if version.snapshot_id:
                self.make_accent_button(
                    row,
                    text="RESTORE",
                    padx=10,
                    pady=4,
                    size=8,
                    command=lambda v=version, p=clean_path: self._restore_file_version(p, v),
                ).pack(side="right", padx=(4, 8), pady=6)

                self.make_button(
                    row,
                    text="VIEW",
                    padx=10,
                    pady=4,
                    size=8,
                    command=lambda v=version: self._view_file_version(v),
                ).pack(side="right", padx=4, pady=6)

    def _view_file_version(self, version):
        curr = self.version_history.get_content(version.file_path, version.version) or ""
        prev = self.version_history.get_content(version.file_path, version.version - 1) or "" if version.version > 1 else ""

        diff = list(
            difflib.unified_diff(
                prev.splitlines(),
                curr.splitlines(),
                fromfile=f"v{version.version-1}" if version.version > 1 else "initial",
                tofile=f"v{version.version}",
                lineterm="",
            )
        )
        change_text = "\n".join(diff) if diff else (curr if curr else "(Empty or no changes)")

        viewer = tk.Toplevel(self.root)
        viewer.title(f"Changes in v{version.version}: {version.file_path}")
        viewer.geometry("560x360")
        viewer.configure(bg=self.BG_COLOR)

        self.make_label(
            viewer,
            text=f"CHANGE IN v{version.version} • {version.file_path}",
            bg=self.BG_COLOR,
            fg=self.ACCENT_COLOR,
            size=11,
            bold=True,
        ).pack(anchor="w", padx=16, pady=(12, 4))

        self.make_label(
            viewer,
            text=f"Event: {version.event_type} | Time: {version.timestamp[:19] if version.timestamp else 'N/A'}",
            bg=self.BG_COLOR,
            fg=self.MUTED_COLOR,
            size=8,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        text_area = tk.Text(
            viewer,
            bg=self.INPUT_COLOR,
            fg=self.TEXT_COLOR,
            font=("Consolas", 9),
            relief="flat",
            wrap="none",
        )
        text_area.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        text_area.insert("1.0", change_text)
        text_area.configure(state="disabled")

    def _restore_file_version(self, file_path, version):
        confirm = messagebox.askyesnocancel(
            "Confirm File Restore",
            f"Restore {file_path} to Version #{version.version}?\n\n"
            f"Snapshot ID: {version.snapshot_id or 'N/A'}\n"
            "• Yes = overwrite the current file with the historical version\n"
            "• No = keep the current file and restore only missing historical lines\n"
            "• Cancel = do nothing",
        )
        if confirm is None:
            return

        merge_with_current = not confirm
        selected_line_indexes = None
        if merge_with_current:
            try:
                current_content = self.version_history.get_content(file_path, self.version_history.get_version_index(file_path, version.version) if hasattr(self.version_history, "get_version_index") else version.version) or ""
                historical_content = self.version_history.get_content(file_path, version.version) or ""
                if historical_content:
                    lines = historical_content.splitlines()
                    if len(lines) > 1:
                        selector = tk.Toplevel(self.root)
                        selector.title(f"Select lines to restore from {file_path}")
                        selector.geometry("420x320")
                        selector.configure(bg=self.BG_COLOR)

                        self.make_label(
                            selector,
                            text=f"Choose lines from Version #{version.version} to restore",
                            bg=self.BG_COLOR,
                            fg=self.ACCENT_COLOR,
                            size=10,
                            bold=True,
                        ).pack(anchor="w", padx=12, pady=(10, 4))

                        listbox = tk.Listbox(
                            selector,
                            bg=self.INPUT_COLOR,
                            fg=self.TEXT_COLOR,
                            selectbackground=self.BUTTON_ACTIVE,
                            relief="flat",
                            bd=0,
                            font=("Consolas", 9),
                            selectmode="extended",
                        )
                        listbox.pack(fill="both", expand=True, padx=12, pady=(0, 8))

                        for idx, line in enumerate(lines, start=1):
                            if not line.strip():
                                listbox.insert("end", f"{idx}: <blank>")
                            else:
                                listbox.insert("end", f"{idx}: {line}")

                        selection_result = {"value": None}

                        def _apply_selection():
                            selection = listbox.curselection()
                            selection_result["value"] = [int(item) - 1 for item in selection]
                            selector.destroy()

                        def _cancel_selection():
                            selection_result["value"] = []
                            selector.destroy()

                        btn_row = tk.Frame(selector, bg=self.BG_COLOR)
                        btn_row.pack(fill="x", padx=12, pady=(0, 12))
                        self.make_button(btn_row, text="RESTORE SELECTED", padx=12, pady=5, command=_apply_selection).pack(side="right")
                        self.make_button(btn_row, text="AUTO MISSING LINES", padx=12, pady=5, command=_cancel_selection).pack(side="right", padx=(0, 8))

                        selector.transient(self.root)
                        selector.grab_set()
                        self.root.wait_window(selector)
                        selected_line_indexes = selection_result["value"]
                        if selected_line_indexes is None:
                            selected_line_indexes = []
            except Exception:
                selected_line_indexes = None

        try:
            if version.snapshot_id:
                self.restore_manager.restore(
                    version.snapshot_id,
                    merge_with_current=merge_with_current,
                    previous_line_count=None,
                    selected_line_indexes=selected_line_indexes,
                )
            else:
                self.restore_manager.restore_version(
                    file_path,
                    version.version,
                    merge_with_current=merge_with_current,
                    previous_line_count=None,
                    selected_line_indexes=selected_line_indexes,
                )

            self.workspace_manager.scan_and_record_changes()

            restored_content = self.version_history.get_content(file_path, version.version)
            line_count = len(restored_content.splitlines()) if restored_content else 0

            action_text = "fully replaced the current file" if not merge_with_current else "kept the current file and restored only the missing or selected historical lines"
            messagebox.showinfo(
                "File Restored Successfully",
                f"✓ {file_path} has been restored to Version #{version.version}!\n\n"
                f"• Restored Lines: {line_count}\n"
                f"• Target File: {os.path.join(self.restore_manager.workspace_path, file_path)}\n\n"
                f"The file {action_text} on disk.",
            )
            self._populate_workspace_files()
            self._on_workspace_file_selected()
        except Exception as exc:
            messagebox.showerror("Restore Failed", str(exc))

    # Compatibility helper methods
    def refresh_history(self):
        if hasattr(self, "_refresh_history_preview"):
            self._refresh_history_preview()

    def refresh_workspace_files(self):
        self._populate_workspace_files()


def main():
    root = tk.Tk()
    ChronoReplayUI(root)
    root.mainloop()




# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

def start_application():
    if "--test" in sys.argv or "--cli" in sys.argv:
        print("=" * 70)
        print("🚀 ChronoReplay Single-File Standalone CLI Self-Test")
        print("=" * 70)
        engine = ChronoReplay(":memory:")
        e1 = engine.publish_event("user.created", {"user_id": "USR-0001", "name": "Rahul Verma", "email": "rahul@example.com", "age": 28})
        e2 = engine.publish_event("balance.added", {"user_id": "USR-0001", "amount": 500.0})
        e3 = engine.publish_event("order.created", {"order_id": "ORD-0001", "user_id": "USR-0001", "amount": 200.0})
        e4 = engine.publish_event("payment.completed", {"order_id": "ORD-0001", "user_id": "USR-0001", "amount": 200.0, "method": "UPI"})
        st = engine.get_current_state()
        assert st["users"]["USR-0001"]["balance"] == 300.0
        assert st["orders"]["ORD-0001"]["status"].lower() == "paid"
        rew = engine.rewind(2)
        assert rew["users"]["USR-0001"]["balance"] == 500.0
        engine.restore_state(2, reason="Audit recovery")
        assert engine.store.count() == 5
        print("✅ Standalone single-file engine & state time-machine verified with 100% success!")
        print("=" * 70)
        return

    try:
        import tkinter as tk
        root = tk.Tk()
        ChronoReplayUI(root)
        root.mainloop()
    except Exception as e:
        print(f"GUI notice: {e}")
        print("To run in headless verification mode: python3 chronoreplay-single.py --cli")


if __name__ == "__main__":
    start_application()
