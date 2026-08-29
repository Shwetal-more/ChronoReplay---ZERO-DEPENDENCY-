"""
sqlite event store for chronoreplay.
this module provides persistent storage for all the events.
only python standard library are used
"""
import json
import sqlite3

from src.event import Event

class EventStore:
    """
    events are stored in a sqlite database.
    the class provides following methods for this:
    - create the database
    - save events in it
    - retrieve events from it
    - retrieve all events
    - retrieve events by type
    - count events
    - clear the storeage
    """
    def __init__(self, database_path: str = "chronoreplay.db"):
        """
        create an event storage
        parameters:
        database_path:
          location of sqlite database file.
        """
        #store the database path so other methods can use it.
        self.database_path = database_path

        # create database table if it doesn't already exists.
        self._initialize_database()

    def _connect(self):
        """
        create and return a sqlite database connection.
        sqlite3 is part of python's standard library.
        """
        return sqlite3.connect(self.database_path)

    def _initialize_database(self) -> None:
        """
        create event table if it does not exists.
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
        save an event into database.
        if an event with same id already exists,
        a valueERROR is raised.
        """
        # Make sure we are storing an Event object.
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
                # Most likely cause is a duplicate event ID.
                raise ValueError(
                    f"Event with id '{event.id}' already exists."
                ) from exc

        finally:
            connection.close()
    def get(self, event_id: str):
        """
        Retrieve one event by its ID.

        Returns:
            Event object if found.
            None if the event does not exist.
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

        # No matching event was found.
        if row is None:
            return None

        return self._row_to_event(row)

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

        This is mainly useful for testing and development.
        """

        connection = self._connect()

        try:
            cursor = connection.cursor()

            cursor.execute("DELETE FROM events")

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

        # Convert JSON string back into a Python dictionary.
        data = json.loads(data_json)

        return Event(
            id=event_id,
            version=version,
            type=event_type,
            timestamp=timestamp,
            data=data,
        )