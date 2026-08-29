"""
SQLite event store for ChronoReplay.

This module provides persistent storage for all events.

Only Python standard-library modules are used.
"""

import json
import sqlite3

from src.event import Event


class EventStore:
    """
    Events are stored in a SQLite database.

    The class provides methods to:

    - create the database
    - save events
    - retrieve events
    - retrieve all events
    - retrieve events by type
    - count events
    - clear storage
    """

    def __init__(
        self,
        database_path: str = "chronoreplay.db"
    ):
        """
        Create an event storage.

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
        Create the events table if it does not exist.
        """

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

            connection.commit()

        finally:
            connection.close()

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

        Both of these are valid:

            store.save(event)

        and:

            store.save_event(event)
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

        This provides the more explicit method name
        used by some tests and application code.
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

    def clear(self) -> None:
        """
        Delete all events from the database.

        Mainly useful for testing and development.
        """

        connection = self._connect()

        try:
            cursor = connection.cursor()

            cursor.execute(
                "DELETE FROM events"
            )

            connection.commit()

        finally:
            connection.close()

    def _row_to_event(self, row) -> Event:
        """
        Convert a SQLite row back into an Event.

        Database row:

            (
                id,
                version,
                type,
                timestamp,
                data_json
            )

        becomes:

            Event(...)
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