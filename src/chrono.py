"""
ChronoReplay orchestration engine.

Connects:
- Event creation
- Event validation
- Event relay
- Event storage

Only Python standard-library modules are used.
"""

from src.event import Event
from src.validator import EventValidator
from src.store import EventStore
from src.relay import EventRelay


class ChronoReplay:
    """
    Main ChronoReplay engine.

    This class coordinates event creation,
    validation, storage, and notification.
    """

    def __init__(self, database_path="chronoreplay.db"):
        """
        Create a ChronoReplay instance.

        Parameters:
            database_path:
                Location of the SQLite database.
        """

        # Persistent event storage.
        self.store = EventStore(database_path)

        # Event relay notifies subscribers.
        self.relay = EventRelay()

    def publish_event(self, event_type, data):
        """
        Create, validate, store, and publish an event.

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

        # Create a new Event object.
        event = Event.create(
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