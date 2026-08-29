import os
import tempfile
import unittest

from src.chrono import ChronoReplay


class TestChronoReplay(unittest.TestCase):

    def setUp(self):

        self.temp_directory = tempfile.mkdtemp()

        self.database_path = os.path.join(
            self.temp_directory,
            "events.db"
        )

        self.chrono = ChronoReplay(
            self.database_path
        )

    def tearDown(self):

        import shutil

        shutil.rmtree(
            self.temp_directory,
            ignore_errors=True
        )

    def test_publish_event(self):

        event = self.chrono.publish_event(
            "user.created",
            {
                "user_id": "U001",
                "name": "Alice",
                "email": "alice@example.com",
                "age": 22,
            }
        )

        self.assertEqual(
            event.type,
            "user.created"
        )

        self.assertEqual(
            self.chrono.count_events(),
            1
        )

    def test_event_appears_in_history(self):

        self.chrono.publish_event(
            "user.created",
            {
                "user_id": "U001",
                "name": "Alice",
                "email": "alice@example.com",
                "age": 22,
            }
        )

        self.chrono.publish_event(
            "status.changed",
            {
                "user_id": "U001",
                "status": "active",
            }
        )

        history = self.chrono.get_history()

        self.assertEqual(
            len(history),
            2
        )

        self.assertEqual(
            history[0].type,
            "user.created"
        )

        self.assertEqual(
            history[1].type,
            "status.changed"
        )

    def test_get_event(self):

        event = self.chrono.publish_event(
            "user.deleted",
            {
                "user_id": "U001",
            }
        )

        result = self.chrono.get_event(
            event.id
        )

        self.assertIsNotNone(result)

        self.assertEqual(
            result.id,
            event.id
        )

    def test_subscriber_receives_event(self):

        received = []

        def listener(event):
            received.append(event)

        self.chrono.subscribe(listener)

        self.chrono.publish_event(
            "user.deleted",
            {
                "user_id": "U001",
            }
        )

        self.assertEqual(
            len(received),
            1
        )

        self.assertEqual(
            received[0].type,
            "user.deleted"
        )

    def test_clear_history(self):

        self.chrono.publish_event(
            "user.deleted",
            {
                "user_id": "U001",
            }
        )

        self.assertEqual(
            self.chrono.count_events(),
            1
        )

        self.chrono.clear_history()

        self.assertEqual(
            self.chrono.count_events(),
            0
        )


if __name__ == "__main__":
    unittest.main()