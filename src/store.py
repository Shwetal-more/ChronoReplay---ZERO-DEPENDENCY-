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

from src.event import Event
from src.snapshot import Snapshot


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
        """
        Create and return a SQLite database connection.

        sqlite3 is part of Python's standard library.
        """

        return sqlite3.connect(
            self.database_path
        )

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