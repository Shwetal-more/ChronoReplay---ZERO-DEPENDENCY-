"""
ChronoReplay Event Simulator.

Creates realistic event sequences while automatically
managing user IDs and order IDs.
"""

from src.event import Event
from src.validator import EventValidator
from src.store import EventStore


class EventSimulator:

    def __init__(self, store: EventStore):

        self.store = store

        # Current active user selected by simulator.
        self.current_user_id = None
        self.current_user_name = None
        self.current_user_email = None

        # Last order created for the current user.
        self.current_order_id = None
        self.current_order_amount = None

        # Initialize from existing store state if any
        self._sync_active_user()

    def _sync_active_user(self):
        """Find the latest created user if none is active."""
        if self.current_user_id is None:
            all_events = self.store.get_all()
            for evt in reversed(all_events):
                if evt.type == "user.created" and "user_id" in evt.data:
                    self.current_user_id = evt.data["user_id"]
                    self.current_user_name = evt.data.get("name", "")
                    self.current_user_email = evt.data.get("email", "")
                    break

    def get_current_user(self):
        """Return details of currently active user or None."""
        if not self.current_user_id:
            return None
        return {
            "user_id": self.current_user_id,
            "name": self.current_user_name or "Unknown",
            "email": self.current_user_email or "",
        }

    def _next_user_seq(self):
        """Calculate next sequential user number."""
        user_events = [e for e in self.store.get_all() if e.type == "user.created"]
        return len(user_events) + 1

    def _next_order_seq(self):
        """Calculate next sequential order number."""
        order_events = [e for e in self.store.get_all() if e.type == "order.created"]
        return len(order_events) + 1

    # =========================================================
    # INTERNAL SAVE
    # =========================================================

    def _save(
        self,
        event_type,
        data
    ):
        data = dict(data)

        if event_type == "user.created":
            if "user_id" not in data:
                data["user_id"] = Event.generate_user_id(self._next_user_seq())
        elif "user_id" not in data and self.current_user_id:
            data["user_id"] = self.current_user_id

        if event_type == "order.created":
            if "order_id" not in data:
                data["order_id"] = Event.generate_order_id(self._next_order_seq())

        if event_type == "payment.completed":
            if "order_id" not in data and self.current_order_id:
                data["order_id"] = self.current_order_id

        event = Event.create(
            event_type,
            data,
        )

        EventValidator.validate(event)

        self.store.save(event)

        # Automatically remember newly generated user.
        if "user_id" in event.data and (event.type == "user.created" or self.current_user_id is None):
            self.current_user_id = event.data["user_id"]
            if "name" in event.data:
                self.current_user_name = event.data["name"]
            if "email" in event.data:
                self.current_user_email = event.data["email"]

        # Automatically remember newly generated order.
        if event.type == "order.created":
            self.current_order_id = event.data["order_id"]
            self.current_order_amount = event.data.get("amount")

        return event

    # =========================================================
    # CREATE USER
    # =========================================================

    def get_all_users(self):
        """Reconstruct and return list of all users from the store."""
        users = {}
        for event in self.store.get_all():
            if event.type == "user.created" and "user_id" in event.data:
                uid = event.data["user_id"]
                users[uid] = {
                    "user_id": uid,
                    "name": event.data.get("name", "Unknown"),
                    "email": event.data.get("email", ""),
                    "age": event.data.get("age", 0),
                    "status": "active",
                }
            elif event.type == "profile.updated" and "user_id" in event.data:
                uid = event.data["user_id"]
                if uid in users:
                    users[uid]["name"] = event.data.get("name", users[uid]["name"])
            elif event.type == "status.changed" and "user_id" in event.data:
                uid = event.data["user_id"]
                if uid in users:
                    users[uid]["status"] = event.data.get("status", users[uid]["status"])
            elif event.type == "user.deleted" and "user_id" in event.data:
                uid = event.data["user_id"]
                if uid in users:
                    users[uid]["status"] = "deleted"
        return list(users.values())

    def switch_user(self, user_id):
        """Switch active user by ID."""
        for u in self.get_all_users():
            if u["user_id"] == user_id:
                self.current_user_id = u["user_id"]
                self.current_user_name = u["name"]
                self.current_user_email = u["email"]
                self.current_order_id = None
                return u
        raise ValueError(f"User {user_id} not found.")

    def create_user(
        self,
        name,
        email,
        age
    ):
        seq = self._next_user_seq()
        user_id = Event.generate_user_id(seq)

        event = self._save(
            "user.created",
            {
                "user_id": user_id,
                "name": name,
                "email": email,
                "age": int(age),
            }
        )

        self.current_user_id = user_id
        self.current_user_name = name
        self.current_user_email = email
        self.current_order_id = None
        self.current_order_amount = None

        return event

    # =========================================================
    # SELECT USER
    # =========================================================

    def select_user(
        self,
        user_id,
        name=None,
        email=None
    ):
        self.current_user_id = user_id
        self.current_user_name = name
        self.current_user_email = email
        self.current_order_id = None
        self.current_order_amount = None

    # =========================================================
    # ADD BALANCE
    # =========================================================

    def add_balance(
        self,
        amount
    ):
        if self.current_user_id is None:
            self.create_user(
                "Rahul",
                "rahul@gmail.com",
                25
            )

        return self._save(
            "balance.added",
            {
                "user_id": self.current_user_id,
                "amount": float(amount),
            }
        )

    # =========================================================
    # CREATE ORDER
    # =========================================================

    def create_order(
        self,
        amount
    ):
        if self.current_user_id is None:
            self.create_user(
                "Rahul",
                "rahul@gmail.com",
                25
            )

        order_id = Event.generate_order_id(self._next_order_seq())

        event = self._save(
            "order.created",
            {
                "user_id": self.current_user_id,
                "order_id": order_id,
                "amount": float(amount),
            }
        )
        return event

    # =========================================================
    # PAYMENT
    # =========================================================

    def complete_payment(
        self,
        amount,
        method="UPI",
        order_id=None
    ):
        if self.current_user_id is None:
            self.create_user(
                "Rahul",
                "rahul@gmail.com",
                25
            )

        data = {
            "user_id": self.current_user_id,
            "amount": float(amount),
            "method": method,
        }
        if order_id:
            data["order_id"] = order_id
        elif self.current_order_id:
            data["order_id"] = self.current_order_id

        return self._save(
            "payment.completed",
            data
        )

    # =========================================================
    # ORDER STATUS
    # =========================================================

    def update_order(
        self,
        status,
        order_id=None
    ):
        target_order = order_id or self.current_order_id
        if target_order is None:
            raise ValueError(
                "No order has been created yet."
            )

        return self._save(
            "order.updated",
            {
                "order_id": target_order,
                "status": status,
            }
        )

    # =========================================================
    # PROFILE
    # =========================================================

    def update_profile(
        self,
        name,
        city="Mumbai"
    ):
        if self.current_user_id is None:
            raise ValueError(
                "No user is selected."
            )

        event = self._save(
            "profile.updated",
            {
                "user_id": self.current_user_id,
                "name": name,
                "city": city,
            }
        )
        self.current_user_name = name
        return event

    # =========================================================
    # STATUS
    # =========================================================

    def change_status(
        self,
        status
    ):
        if self.current_user_id is None:
            raise ValueError(
                "No user is selected."
            )

        return self._save(
            "status.changed",
            {
                "user_id": self.current_user_id,
                "status": status,
            }
        )

    # =========================================================
    # USER DELETED
    # =========================================================

    def delete_user(self):
        if self.current_user_id is None:
            raise ValueError("No user is selected.")

        event = self._save(
            "user.deleted",
            {
                "user_id": self.current_user_id,
            }
        )
        self.current_user_id = None
        self.current_user_name = None
        self.current_user_email = None
        self.current_order_id = None
        return event
