
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

from src.event import Event
from src.validator import EventValidator
from src.store import EventStore
from src.relay import EventRelay


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
        from src.replay import ReplayEngine
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
