# unittest is Python's built-in testing framework.
# We use it instead of third-party tools such as pytest.
import unittest

# json lets us inspect the JSON produced by our Event.
import json

# Import the Event class we are testing.
from src.event import Event


class TestEvent(unittest.TestCase):
    """Tests for the Event model."""

    def test_create_event(self):
        # Create a new event using our helper method.
        event = Event.create(
            "user.created",
            {
                "name": "Alice",
                "email": "alice@example.com",
            },
        )

        # The ID should automatically be generated.
        self.assertTrue(event.id)

        # New events should start at version 1.
        self.assertEqual(event.version, 1)

        # Check that the event type was stored correctly.
        self.assertEqual(event.type, "user.created")

        # A timestamp should have been generated.
        self.assertIsInstance(event.timestamp, str)

        # Check that our event data was stored.
        self.assertEqual(event.data["name"], "Alice")

    def test_to_dict(self):
        # Create an Event with known values.
        event = Event(
            id="event-001",
            version=1,
            type="user.created",
            timestamp="2026-08-29T10:00:00+00:00",
            data={"name": "Alice"},
        )

        # Convert the Event into a dictionary.
        result = event.to_dict()

        # Check that important values are preserved.
        self.assertEqual(result["id"], "event-001")
        self.assertEqual(result["type"], "user.created")
        self.assertEqual(result["data"], {"name": "Alice"})

    def test_to_json(self):
        # Create an Event.
        event = Event(
            id="event-001",
            version=1,
            type="user.created",
            timestamp="2026-08-29T10:00:00+00:00",
            data={"name": "Alice"},
        )

        # Convert the Event into JSON.
        result = event.to_json()

        # The result should be text.
        self.assertIsInstance(result, str)

        # Convert the JSON back into a dictionary.
        parsed = json.loads(result)

        # Make sure the information is still correct.
        self.assertEqual(parsed["id"], "event-001")
        self.assertEqual(parsed["data"]["name"], "Alice")

    def test_from_dict(self):
        # This is an event represented as a normal dictionary.
        data = {
            "id": "event-001",
            "version": 1,
            "type": "user.created",
            "timestamp": "2026-08-29T10:00:00+00:00",
            "data": {"name": "Alice"},
        }

        # Convert the dictionary into an Event object.
        event = Event.from_dict(data)

        # Check that the values were restored correctly.
        self.assertEqual(event.id, "event-001")
        self.assertEqual(event.type, "user.created")
        self.assertEqual(event.data["name"], "Alice")

    def test_json_round_trip(self):
        """
        Test:

        Event
          ↓
        JSON
          ↓
        Event

        The information should remain unchanged.
        """

        # Create the original event.
        original = Event.create(
            "profile.updated",
            {
                "name": "Alice",
                "city": "Mumbai",
            },
        )

        # Convert Event -> JSON.
        json_data = original.to_json()

        # Convert JSON -> Event.
        restored = Event.from_json(json_data)

        # Compare the original and restored event.
        self.assertEqual(restored.id, original.id)
        self.assertEqual(restored.version, original.version)
        self.assertEqual(restored.type, original.type)
        self.assertEqual(restored.timestamp, original.timestamp)
        self.assertEqual(restored.data, original.data)

    def test_invalid_id(self):
        # An empty ID should not be allowed.
        with self.assertRaises(ValueError):
            Event(
                id="",
                version=1,
                type="user.created",
                timestamp="2026-08-29T10:00:00+00:00",
                data={},
            )

    def test_invalid_version(self):
        # Version 0 is invalid because versions start at 1.
        with self.assertRaises(ValueError):
            Event(
                id="event-001",
                version=0,
                type="user.created",
                timestamp="2026-08-29T10:00:00+00:00",
                data={},
            )

    def test_invalid_type(self):
        # Event type cannot be empty.
        with self.assertRaises(ValueError):
            Event(
                id="event-001",
                version=1,
                type="",
                timestamp="2026-08-29T10:00:00+00:00",
                data={},
            )

    def test_invalid_data(self):
        # Event data must be a dictionary.
        with self.assertRaises(ValueError):
            Event(
                id="event-001",
                version=1,
                type="user.created",
                timestamp="2026-08-29T10:00:00+00:00",
                data="not a dictionary",
            )


# This allows the test file to be run directly as well.
if __name__ == "__main__":
    unittest.main()