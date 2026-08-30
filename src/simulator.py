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
        """Find the latest active non-deleted user if none is active."""
        if self.current_user_id is None:
            active_users = [u for u in self.get_all_users() if u.get("status") != "deleted"]
            if active_users:
                last_active = active_users[-1]
                self.current_user_id = last_active["user_id"]
                self.current_user_name = last_active.get("name", "")
                self.current_user_email = last_active.get("email", "")
            else:
                self.current_user_id = None
                self.current_user_name = None
                self.current_user_email = None

    def get_current_user(self):
        """Return details of currently active non-deleted user or None."""
        if not self.current_user_id:
            return None
        for u in self.get_all_users():
            if u["user_id"] == self.current_user_id and u.get("status") != "deleted":
                return {
                    "user_id": u["user_id"],
                    "name": u.get("name") or self.current_user_name or "Unknown",
                    "email": u.get("email") or self.current_user_email or "",
                }
        active_users = [u for u in self.get_all_users() if u.get("status") != "deleted"]
        if active_users:
            self.current_user_id = active_users[0]["user_id"]
            self.current_user_name = active_users[0].get("name", "")
            self.current_user_email = active_users[0].get("email", "")
            return {
                "user_id": self.current_user_id,
                "name": self.current_user_name or "Unknown",
                "email": self.current_user_email or "",
            }
        self.current_user_id = None
        self.current_user_name = None
        self.current_user_email = None
        return None

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

    def get_active_users(self):
        """Return only active (non-deleted) users."""
        return [u for u in self.get_all_users() if u.get("status") != "deleted"]

    def get_ex_users(self):
        """Return ex-users (deleted users)."""
        return [u for u in self.get_all_users() if u.get("status") == "deleted"]

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

    def get_user_balance(self, user_id=None):
        """Calculate current user balance from stored events."""
        uid = user_id or self.current_user_id
        if not uid:
            return 0.0
        balance = 0.0
        for ev in self.store.get_all():
            if ev.data.get("user_id") == uid:
                if ev.type == "balance.added":
                    balance += float(ev.data.get("amount", 0.0))
                elif ev.type == "payment.completed":
                    amt = float(ev.data.get("amount", 0.0))
                    if balance >= amt:
                        balance -= amt
        return balance

    def get_user_orders(self, user_id=None):
        """Reconstruct list of all orders for user with payment amounts and statuses."""
        uid = user_id or self.current_user_id
        if not uid:
            return []
        orders = {}
        for ev in self.store.get_all():
            if ev.type == "order.created" and ev.data.get("user_id") == uid:
                oid = ev.data.get("order_id")
                orders[oid] = {
                    "order_id": oid,
                    "user_id": uid,
                    "amount": float(ev.data.get("amount", 0.0)),
                    "paid_amount": 0.0,
                    "status": "pending",
                }
            elif ev.type == "payment.completed" and ev.data.get("user_id") == uid:
                oid = ev.data.get("order_id")
                if oid and oid in orders:
                    amt = float(ev.data.get("amount", 0.0))
                    orders[oid]["paid_amount"] += amt
                    if orders[oid]["paid_amount"] >= orders[oid]["amount"]:
                        orders[oid]["status"] = "paid"
            elif ev.type == "order.updated":
                oid = ev.data.get("order_id")
                if oid and oid in orders:
                    orders[oid]["status"] = ev.data.get("status", orders[oid]["status"])
        return list(orders.values())

    def get_user_pending_orders(self, user_id=None):
        """Return list of pending orders that still have a remaining balance to be paid."""
        orders = self.get_user_orders(user_id)
        return [o for o in orders if o.get("status") in ("pending", "created") and (o.get("amount", 0.0) - o.get("paid_amount", 0.0)) > 0]

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
        self.current_order_id = order_id
        self.current_order_amount = float(amount)
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
            raise ValueError(
                "No user selected. Please create or select a user first."
            )

        target_order = order_id or self.current_order_id
        if not target_order:
            for ev in reversed(self.store.get_all()):
                if ev.type == "order.created" and ev.data.get("user_id") == self.current_user_id:
                    target_order = ev.data.get("order_id")
                    break

        if not target_order:
            raise ValueError(
                "No order found for this user. You cannot complete a payment without creating an order first. Please create an order first."
            )

        data = {
            "user_id": self.current_user_id,
            "amount": float(amount),
            "method": method,
            "order_id": target_order,
        }

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

    def delete_user(self, user_id=None):
        target_uid = user_id or self.current_user_id
        if target_uid is None:
            raise ValueError("No user is selected.")

        event = self._save(
            "user.deleted",
            {
                "user_id": target_uid,
            }
        )

        # If the deleted user was the active user, auto-switch to another existing active user
        if self.current_user_id == target_uid:
            remaining_users = [
                u for u in self.get_all_users()
                if u.get("status") != "deleted" and u.get("user_id") != target_uid
            ]
            if remaining_users:
                self.current_user_id = remaining_users[0]["user_id"]
                self.current_user_name = remaining_users[0]["name"]
                self.current_user_email = remaining_users[0]["email"]
            else:
                self.current_user_id = None
                self.current_user_name = None
                self.current_user_email = None
            self.current_order_id = None
            self.current_order_amount = None
        return event
