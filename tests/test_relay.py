import unittest

from src.event import Event
from src.relay import EventRelay


class TestEventRelay(unittest.TestCase):
    """
    Tests for the ChronoReplay EventRelay.
    """

    def create_event(self):
        """
        Create a valid test event.
        """

        return Event.create(
            "user.created",
            {
                "user_id": "user-001",
                "name": "Alice",
                "email": "alice@example.com",
                "age": 22,
            },
        )

    def test_relay_starts_empty(self):
        """
        A new relay should have no subscribers.
        """

        relay = EventRelay()

        self.assertEqual(
            relay.subscriber_count(),
            0,
        )

    def test_subscribe(self):
        """
        A subscriber should be registered.
        """

        relay = EventRelay()

        def listener(event):
            pass

        relay.subscribe(listener)

        self.assertEqual(
            relay.subscriber_count(),
            1,
        )

    def test_duplicate_subscriber_is_not_added(self):
        """
        The same subscriber should not be registered twice.
        """

        relay = EventRelay()

        def listener(event):
            pass

        relay.subscribe(listener)
        relay.subscribe(listener)

        self.assertEqual(
            relay.subscriber_count(),
            1,
        )

    def test_unsubscribe(self):
        """
        A subscriber should be removable.
        """

        relay = EventRelay()

        def listener(event):
            pass

        relay.subscribe(listener)

        self.assertEqual(
            relay.subscriber_count(),
            1,
        )

        relay.unsubscribe(listener)

        self.assertEqual(
            relay.subscriber_count(),
            0,
        )

    def test_publish_sends_event_to_subscriber(self):
        """
        Publishing an event should send it to subscribers.
        """

        relay = EventRelay()

        received_events = []

        def listener(event):
            received_events.append(event)

        relay.subscribe(listener)

        event = self.create_event()

        result = relay.publish(event)

        self.assertEqual(
            result,
            1,
        )

        self.assertEqual(
            len(received_events),
            1,
        )

        self.assertEqual(
            received_events[0].id,
            event.id,
        )

    def test_publish_to_multiple_subscribers(self):
        """
        Every subscriber should receive the event.
        """

        relay = EventRelay()

        received_by_first = []
        received_by_second = []

        def first_listener(event):
            received_by_first.append(event)

        def second_listener(event):
            received_by_second.append(event)

        relay.subscribe(first_listener)
        relay.subscribe(second_listener)

        event = self.create_event()

        result = relay.publish(event)

        self.assertEqual(
            result,
            2,
        )

        self.assertEqual(
            len(received_by_first),
            1,
        )

        self.assertEqual(
            len(received_by_second),
            1,
        )

        self.assertEqual(
            received_by_first[0].id,
            event.id,
        )

        self.assertEqual(
            received_by_second[0].id,
            event.id,
        )

    def test_unsubscribed_listener_does_not_receive_event(self):
        """
        An unsubscribed listener should not receive events.
        """

        relay = EventRelay()

        received_events = []

        def listener(event):
            received_events.append(event)

        relay.subscribe(listener)
        relay.unsubscribe(listener)

        relay.publish(
            self.create_event()
        )

        self.assertEqual(
            len(received_events),
            0,
        )

    def test_clear_subscribers(self):
        """
        clear_subscribers() should remove every subscriber.
        """

        relay = EventRelay()

        def first_listener(event):
            pass

        def second_listener(event):
            pass

        relay.subscribe(first_listener)
        relay.subscribe(second_listener)

        self.assertEqual(
            relay.subscriber_count(),
            2,
        )

        relay.clear_subscribers()

        self.assertEqual(
            relay.subscriber_count(),
            0,
        )

    def test_invalid_subscriber(self):
        """
        Non-callable objects cannot become subscribers.
        """

        relay = EventRelay()

        with self.assertRaises(ValueError):
            relay.subscribe("not a function")

    def test_invalid_event(self):
        """
        Relay should reject objects that are not Events.
        """

        relay = EventRelay()

        with self.assertRaises(ValueError):
            relay.publish(
                {
                    "type": "user.created",
                    "data": {},
                }
            )

    def test_invalid_event_is_not_published(self):
        """
        Invalid events must not reach subscribers.
        """

        relay = EventRelay()

        received_events = []

        def listener(event):
            received_events.append(event)

        relay.subscribe(listener)

        invalid_event = Event.create(
            "something.invalid",
            {
                "hello": "world",
            },
        )

        with self.assertRaises(ValueError):
            relay.publish(invalid_event)

        self.assertEqual(
            len(received_events),
            0,
        )


if __name__ == "__main__":
    unittest.main()