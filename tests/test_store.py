import os
import tempfile
import unittest

from src.event import Event
from src.store import EventStore


class TestEventStore(unittest.TestCase):
    """
    Tests for the ChronoReplay SQLite event store.
    """

    def setUp(self):
        """
        Create a temporary database for each test.

        This prevents tests from modifying the real
        ChronoReplay database.
        """

        self.temp_file = tempfile.NamedTemporaryFile(
            suffix=".db",
            delete=False,
        )

        self.database_path = self.temp_file.name

        self.temp_file.close()

        self.store = EventStore(self.database_path)

    def tearDown(self):
        """
        Delete the temporary database after each test.
        """

        if os.path.exists(self.database_path):
            os.remove(self.database_path)

    def create_event(
        self,
        event_type="user.created",
        data=None,
    ):
        """
        Helper method for creating test events.
        """

        if data is None:
            data = {
                "user_id": "user-001",
                "name": "Alice",
                "email": "alice@example.com",
                "age": 22,
            }

        return Event.create(
            event_type,
            data,
        )

    def test_database_is_created(self):
        """
        The EventStore should create its database.
        """

        self.assertTrue(
            os.path.exists(self.database_path)
        )

    def test_save_event(self):
        """
        An event should be stored successfully.
        """

        event = self.create_event()

        self.store.save(event)

        self.assertEqual(
            self.store.count(),
            1,
        )

    def test_get_event(self):
        """
        A saved event should be retrievable by ID.
        """

        event = self.create_event()

        self.store.save(event)

        retrieved = self.store.get(event.id)

        self.assertIsNotNone(retrieved)

        self.assertEqual(
            retrieved.id,
            event.id,
        )

        self.assertEqual(
            retrieved.type,
            event.type,
        )

        self.assertEqual(
            retrieved.data,
            event.data,
        )

    def test_get_missing_event(self):
        """
        Getting a nonexistent event should return None.
        """

        result = self.store.get("does-not-exist")

        self.assertIsNone(result)

    def test_get_all_events(self):
        """
        All stored events should be returned.
        """

        event1 = self.create_event(
            "user.created"
        )

        event2 = self.create_event(
            "profile.updated",
            {
                "user_id": "user-001",
                "name": "Alice",
                "city": "Mumbai",
            },
        )

        event3 = self.create_event(
            "balance.added",
            {
                "user_id": "user-001",
                "amount": 500,
            },
        )

        self.store.save(event1)
        self.store.save(event2)
        self.store.save(event3)

        events = self.store.get_all()

        self.assertEqual(
            len(events),
            3,
        )

        self.assertEqual(
            events[0].id,
            event1.id,
        )

        self.assertEqual(
            events[1].id,
            event2.id,
        )

        self.assertEqual(
            events[2].id,
            event3.id,
        )

    def test_get_by_type(self):
        """
        Events can be retrieved by event type.
        """

        event1 = self.create_event(
            "user.created"
        )

        event2 = self.create_event(
            "balance.added",
            {
                "user_id": "user-001",
                "amount": 500,
            },
        )

        event3 = self.create_event(
            "balance.added",
            {
                "user_id": "user-001",
                "amount": 200,
            },
        )

        self.store.save(event1)
        self.store.save(event2)
        self.store.save(event3)

        balance_events = self.store.get_by_type(
            "balance.added"
        )

        self.assertEqual(
            len(balance_events),
            2,
        )

        self.assertEqual(
            balance_events[0].id,
            event2.id,
        )

        self.assertEqual(
            balance_events[1].id,
            event3.id,
        )

    def test_count(self):
        """
        count() should return the number of events.
        """

        self.assertEqual(
            self.store.count(),
            0,
        )

        self.store.save(
            self.create_event()
        )

        self.assertEqual(
            self.store.count(),
            1,
        )

        self.store.save(
            self.create_event(
                "balance.added",
                {
                    "user_id": "user-001",
                    "amount": 500,
                },
            )
        )

        self.assertEqual(
            self.store.count(),
            2,
        )

    def test_clear(self):
        """
        clear() should remove all events.
        """

        self.store.save(
            self.create_event()
        )

        self.store.save(
            self.create_event(
                "balance.added",
                {
                    "user_id": "user-001",
                    "amount": 500,
                },
            )
        )

        self.assertEqual(
            self.store.count(),
            2,
        )

        self.store.clear()

        self.assertEqual(
            self.store.count(),
            0,
        )

    def test_duplicate_event_id(self):
        """
        Saving the same event twice should fail.
        """

        event = self.create_event()

        self.store.save(event)

        with self.assertRaises(ValueError):
            self.store.save(event)

    def test_invalid_object(self):
        """
        Only Event objects should be stored.
        """

        with self.assertRaises(ValueError):
            self.store.save(
                {
                    "id": "fake",
                    "type": "user.created",
                }
            )

    def test_event_data_is_preserved(self):
        """
        Nested event data should survive the
        Event -> SQLite -> Event round trip.
        """

        event = self.create_event(
            "profile.updated",
            {
                "user_id": "user-001",
                "name": "Alice",
                "city": "Mumbai",
                "preferences": {
                    "theme": "dark",
                    "notifications": True,
                },
            },
        )

        self.store.save(event)

        retrieved = self.store.get(event.id)

        self.assertEqual(
            retrieved.data,
            event.data,
        )

    def test_get_all_tracked_files_and_get_events_for_file(self):
        """
        get_all_tracked_files() and get_events_for_file() should track file events.
        """
        event1 = self.create_event(
            "file.created",
            {"file_path": "src/main.py", "content_hash": "abc"}
        )
        event2 = self.create_event(
            "file.modified",
            {"file_path": "src/main.py", "content_hash": "def"}
        )
        event3 = self.create_event(
            "file.created",
            {"file_path": "docs/readme.md", "content_hash": "123"}
        )

        self.store.save(event1)
        self.store.save(event2)
        self.store.save(event3)

        tracked = self.store.get_all_tracked_files()
        self.assertEqual(tracked, ["docs/readme.md", "src/main.py"])

        file_events = self.store.get_events_for_file("src/main.py")
        self.assertEqual(len(file_events), 2)
        self.assertEqual(file_events[0].id, event1.id)
        self.assertEqual(file_events[1].id, event2.id)


if __name__ == "__main__":
    unittest.main()