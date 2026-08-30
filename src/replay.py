"""
ChronoReplay replay and time-machine engine.
"""

from src.event import Event
from src.state import StateEngine
from src.store import EventStore


class ReplayEngine:

    def __init__(self, store: EventStore):

        if not isinstance(store, EventStore):
            raise ValueError(
                "ReplayEngine requires an EventStore."
            )

        self.store = store

    # =========================================================
    # FULL REPLAY
    # =========================================================

    def replay_all(self) -> dict:

        events = self.store.get_all()

        return self._replay_events(events)

    # =========================================================
    # REPLAY UNTIL EVENT
    # =========================================================

    def replay_until(
        self,
        event_number: int
    ) -> dict:

        if (
            isinstance(event_number, bool)
            or not isinstance(event_number, int)
        ):
            raise ValueError(
                "Event number must be an integer."
            )

        if event_number < 1:
            raise ValueError(
                "Event number must be at least 1."
            )

        events = self.store.get_all()

        if event_number > len(events):
            raise ValueError(
                "Requested event number does not exist."
            )

        return self._replay_events(
            events[:event_number]
        )

    # =========================================================
    # REPLAY EVENT
    # =========================================================

    def replay_event(
        self,
        event_id: str
    ) -> dict:

        events = self.store.get_all()

        for index, event in enumerate(events):

            if event.id == event_id:

                return self._replay_events(
                    events[:index + 1]
                )

        raise ValueError(
            f"Event '{event_id}' does not exist."
        )

    def replay_until_event_id(
        self,
        event_id: str
    ) -> dict:
        """Replay all historical events up to and including event_id."""
        return self.replay_event(event_id)

    def replay_before_event_id(
        self,
        event_id: str
    ) -> dict:
        """Replay all historical events strictly before event_id."""
        events = self.store.get_all()
        for index, event in enumerate(events):
            if event.id == event_id:
                if index == 0:
                    return StateEngine().get_state()
                return self._replay_events(events[:index])

        raise ValueError(
            f"Event '{event_id}' does not exist."
        )

    def replay_events_list(
        self,
        events: list
    ) -> dict:
        """Replay an explicit list of events."""
        return self._replay_events(events)

    def replay_events_with_engine(
        self,
        events: list
    ):
        """Replay an explicit list of events returning (state, engine)."""
        engine = StateEngine()
        for event in events:
            engine.apply(event)
        return engine.get_state(), engine

    # =========================================================
    # REPLAY USER
    # =========================================================

    def replay_user(
        self,
        user_id: str
    ) -> dict:

        events = self.store.get_all()

        selected = []

        for event in events:

            if event.data.get("user_id") == user_id:
                selected.append(event)

        return self._replay_events(selected)

    # =========================================================
    # HISTORY
    # =========================================================

    def get_history(self) -> list:
        return self.store.get_all()

    def history_count(self) -> int:
        return self.store.count()

    # =========================================================
    # EVENT DETAILS
    # =========================================================

    def get_event_number(
        self,
        event_id: str
    ):

        events = self.store.get_all()

        for index, event in enumerate(events):

            if event.id == event_id:
                return index + 1

        return None

    # =========================================================
    # USER TIMELINE
    # =========================================================

    def get_user_timeline(
        self,
        user_id
    ):

        events = self.store.get_events_for_user(
            user_id
        )

        timeline = []

        for number, event in enumerate(events, start=1):

            timeline.append({
                "number": number,
                "event_id": event.id,
                "type": event.type,
                "timestamp": event.timestamp,
                "data": event.data,
            })

        return timeline

    # =========================================================
    # ORDER TIMELINE
    # =========================================================

    def get_order_timeline(
        self,
        order_id
    ):

        events = self.store.get_events_for_order(
            order_id
        )

        timeline = []

        for number, event in enumerate(events, start=1):

            timeline.append({
                "number": number,
                "event_id": event.id,
                "type": event.type,
                "timestamp": event.timestamp,
                "data": event.data,
            })

        return timeline

    # =========================================================
    # STATE AT EVENT
    # =========================================================

    def state_at_event(
        self,
        event_number
    ):

        return self.replay_until(
            event_number
        )

    # =========================================================
    # STATE BEFORE EVENT
    # =========================================================

    def state_before_event(
        self,
        event_number
    ):

        if event_number <= 1:

            return StateEngine().get_state()

        return self.replay_until(
            event_number - 1
        )

    # =========================================================
    # REPLAY WITH ENGINE / DIAGNOSTICS
    # =========================================================

    def replay_with_engine(self, event_number: int = None):
        """
        Replay up to event_number (or all events) and return (state, engine).
        """
        events = self.store.get_all()
        if event_number is not None:
            if event_number < 1 or event_number > len(events):
                raise ValueError("Requested event number out of range.")
            events = events[:event_number]

        engine = StateEngine()
        for event in events:
            engine.apply(event)

        return engine.get_state(), engine

    def get_diagnostics_for_event(self, event_number: int) -> dict:
        """
        Check if event at event_number produced an invalid state.
        """
        _, engine = self.replay_with_engine(event_number)
        return engine.get_event_validity(event_number)

    def get_diagnostics_for_event_id(self, event_id: str) -> dict:
        """
        Check if the event with event_id produced an invalid state during historical replay.
        """
        events = self.store.get_all()
        engine = StateEngine()
        for index, event in enumerate(events, start=1):
            engine.apply(event)
            if event.id == event_id:
                return engine.get_event_validity(index)
        return {"event_index": 0, "is_valid": True}

    def get_all_diagnostics(self) -> list:
        """
        Return all diagnostic items from replaying the entire history.
        """
        _, engine = self.replay_with_engine()
        return engine.get_diagnostics()

    # =========================================================
    # REPLAY
    # =========================================================

    @staticmethod
    def _replay_events(
        events: list
    ) -> dict:

        engine = StateEngine()

        for event in events:
            engine.apply(event)

        return engine.get_state()
