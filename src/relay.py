"""
Event relay for ChronoReplay.

The EventRelay distributes validated events to registered
subscriber functions.

Only Python standard-library functionality is used.
"""

from src.event import Event
from src.validator import EventValidator


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