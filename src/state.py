"""
State engine for ChronoReplay.

The StateEngine reconstructs the current application state
by applying events in chronological order.

Only Python standard-library functionality is used.
"""

from copy import deepcopy

from src.event import Event


class StateEngine:
    """
    Maintains the current state of the system.

    Events are applied one at a time.

    The engine also keeps snapshots so that previous states
    can later be inspected or restored.
    """

    def __init__(self):
        """
        Create an empty state engine.
        """

        # Current reconstructed state.
        self._state = {
            "users": {},
            "orders": {},
            "payments": [],
        }

        # State snapshots after every event.
        self._snapshots = []

        # Number of events processed.
        self._event_count = 0

    def apply(self, event: Event) -> None:
        """
        Apply one event to the current state.
        """

        if not isinstance(event, Event):
            raise ValueError(
                "Only Event objects can be applied."
            )

        event_type = event.type
        data = event.data

        if event_type == "user.created":
            self._apply_user_created(data)

        elif event_type == "profile.updated":
            self._apply_profile_updated(data)

        elif event_type == "status.changed":
            self._apply_status_changed(data)

        elif event_type == "balance.added":
            self._apply_balance_added(data)

        elif event_type == "payment.completed":
            self._apply_payment_completed(data)

        elif event_type == "order.created":
            self._apply_order_created(data)

        elif event_type == "order.updated":
            self._apply_order_updated(data)

        elif event_type == "user.deleted":
            self._apply_user_deleted(data)

        else:
            raise ValueError(
                f"Unsupported event type: {event_type}"
            )

        # Increase processed event count.
        self._event_count += 1

        # Save a snapshot after processing the event.
        self._snapshots.append(
            deepcopy(self._state)
        )

    def _apply_user_created(self, data: dict) -> None:
        """
        Create a new user.
        """

        user_id = data["user_id"]

        self._state["users"][user_id] = {
            "user_id": user_id,
            "name": data.get("name", ""),
            "email": data.get("email", ""),
            "age": data.get("age"),
            "status": "active",
            "balance": 0,
        }

    def _apply_profile_updated(self, data: dict) -> None:
        """
        Update a user's profile.
        """

        user_id = data["user_id"]

        user = self._get_user(user_id)

        user["name"] = data["name"]
        user["city"] = data["city"]

    def _apply_status_changed(self, data: dict) -> None:
        """
        Change a user's status.
        """

        user_id = data["user_id"]

        user = self._get_user(user_id)

        user["status"] = data["status"]

    def _apply_balance_added(self, data: dict) -> None:
        """
        Add money to a user's balance.
        """

        user_id = data["user_id"]

        user = self._get_user(user_id)

        user["balance"] += data["amount"]

    def _apply_payment_completed(self, data: dict) -> None:
        """
        Record a completed payment.
        """

        payment = {
            "user_id": data["user_id"],
            "amount": data["amount"],
            "method": data["method"],
        }

        self._state["payments"].append(payment)

    def _apply_order_created(self, data: dict) -> None:
        """
        Create an order.
        """

        order_id = data["order_id"]

        self._state["orders"][order_id] = {
            "order_id": order_id,
            "user_id": data["user_id"],
            "amount": data["amount"],
            "status": "pending",
        }

    def _apply_order_updated(self, data: dict) -> None:
        """
        Update an existing order.
        """

        order_id = data["order_id"]

        if order_id not in self._state["orders"]:
            raise ValueError(
                f"Order '{order_id}' does not exist."
            )

        self._state["orders"][order_id]["status"] = (
            data["status"]
        )

    def _apply_user_deleted(self, data: dict) -> None:
        """
        Delete a user from the current state.
        """

        user_id = data["user_id"]

        self._state["users"].pop(
            user_id,
            None,
        )

    def _get_user(self, user_id: str) -> dict:
        """
        Return a user or raise an error if the user doesn't exist.
        """

        if user_id not in self._state["users"]:
            raise ValueError(
                f"User '{user_id}' does not exist."
            )

        return self._state["users"][user_id]

    def get_state(self) -> dict:
        """
        Return a copy of the current state.
        """

        return deepcopy(self._state)

    def get_snapshot(self, event_number: int) -> dict:
        """
        Return the state after a specific event.

        event_number:
            1 = state after first event
            2 = state after second event
            etc.
        """

        if event_number < 1:
            raise ValueError(
                "Event number must be at least 1."
            )

        if event_number > len(self._snapshots):
            raise ValueError(
                "Requested event number does not exist."
            )

        return deepcopy(
            self._snapshots[event_number - 1]
        )

    def event_count(self) -> int:
        """
        Return the number of processed events.
        """

        return self._event_count

    def reset(self) -> None:
        """
        Completely reset the state engine.
        """

        self._state = {
            "users": {},
            "orders": {},
            "payments": [],
        }

        self._snapshots = []

        self._event_count = 0