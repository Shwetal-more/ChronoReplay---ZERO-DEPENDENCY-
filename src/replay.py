"""
Replay and time-machine functionality for ChronoReplay.

The ReplayEngine reconstructs application state from stored events.

Only Python standard-library functionality is used.
"""

from src.event import Event
from src.state import StateEngine
from src.store import EventStore


class ReplayEngine:
    """
    Reconstructs application state from event history.

    The original event history is never modified.
    """

    def __init__(self, store: EventStore):
        """
        Create a ReplayEngine using an EventStore.
        """

        if not isinstance(store, EventStore):
            raise ValueError(
                "ReplayEngine requires an EventStore."
            )

        self.store = store

    def replay_all(self) -> dict:
        """
        Replay the complete event history.

        Returns:
            Final reconstructed state.
        """

        events = self.store.get_all()

        return self._replay_events(events)

    def replay_until(self, event_number: int) -> dict:
        """
        Reconstruct state up to a specific event.

        Example:

            replay_until(3)

        means:

            Event 1
            Event 2
            Event 3

        are applied.

        Events after #3 are ignored for this reconstruction.
        """

        if event_number < 1:
            raise ValueError(
                "Event number must be at least 1."
            )

        events = self.store.get_all()

        if event_number > len(events):
            raise ValueError(
                "Requested event number does not exist."
            )

        selected_events = events[:event_number]

        return self._replay_events(
            selected_events
        )

    def replay_event(self, event_id: str) -> dict:
        """
        Reconstruct state immediately after a specific event ID.
        """

        events = self.store.get_all()

        for index, event in enumerate(events):

            if event.id == event_id:

                return self._replay_events(
                    events[: index + 1]
                )

        raise ValueError(
            f"Event '{event_id}' does not exist."
        )

    def get_history(self) -> list:
        """
        Return the complete event history.
        """

        return self.store.get_all()

    def history_count(self) -> int:
        """
        Return the number of stored events.
        """

        return self.store.count()

    @staticmethod
    def _replay_events(events: list) -> dict:
        """
        Apply a sequence of events to a fresh StateEngine.
        """

        engine = StateEngine()

        for event in events:
            engine.apply(event)

        return engine.get_state()