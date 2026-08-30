"""
ChronoReplay state reconstruction engine.

The state is NEVER stored as the source of truth.

It is reconstructed by replaying events.
"""

from copy import deepcopy
from src.event import Event


class StateEngine:

    def __init__(self):
        self.state = {
            "users": {},
            "orders": {},
            "payments": [],
            "files": {},
        }
        self._snapshots = []
        self._diagnostics = []
        self._event_count = 0

    # =========================================================
    # APPLY EVENT
    # =========================================================

    def apply(self, event: Event):

        if not isinstance(event, Event):
            raise ValueError(
                "StateEngine can only apply Event objects."
            )

        event_type = event.type
        data = event.data

        if event_type == "user.created":
            self._user_created(data)

        elif event_type == "profile.updated":
            self._profile_updated(data)

        elif event_type == "status.changed":
            self._status_changed(data)

        elif event_type == "balance.added":
            self._balance_added(data)

        elif event_type == "payment.completed":
            self._payment_completed(data)

        elif event_type == "order.created":
            self._order_created(data)

        elif event_type == "order.updated":
            self._order_updated(data)

        elif event_type == "user.deleted":
            self._user_deleted(data)

        # State recovery events
        elif event_type == "state.restored":
            self._apply_state_restored(data)

        # File events do not modify core application state
        elif event_type == "file.created":
            self._file_created(data)

        elif event_type == "file.modified":
            self._file_modified(data)

        elif event_type == "file.deleted":
            self._file_deleted(data)

        elif event_type == "file.restored":
            self._file_restored(data)

        else:
            raise ValueError(
                f"Unsupported event type: {event_type}"
            )

        self._event_count += 1
        self._snapshots.append(deepcopy(self.state))

    # =========================================================
    # USER CREATED
    # =========================================================

    def _user_created(self, data):

        user_id = data["user_id"]

        self.state["users"][user_id] = {
            "user_id": user_id,
            "name": data.get("name", ""),
            "email": data.get("email", ""),
            "age": data.get("age", 0),
            "status": "active",
            "balance": 0.0,
            "deleted": False,
        }

    # =========================================================
    # PROFILE
    # =========================================================

    def _profile_updated(self, data):

        user = self._get_user(data["user_id"])

        user["name"] = data["name"]
        user["city"] = data.get("city", "")

    # =========================================================
    # STATUS
    # =========================================================

    def _status_changed(self, data):

        user = self._get_user(data["user_id"])

        user["status"] = data["status"]

    # =========================================================
    # BALANCE
    # =========================================================

    def _balance_added(self, data):

        user = self._get_user(data["user_id"])

        user["balance"] += float(data["amount"])

    # =========================================================
    # PAYMENT
    # =========================================================

    def _payment_completed(self, data):

        user = self._get_user(data["user_id"])

        amount = float(data["amount"])

        # Auto-resolve target order if not explicitly provided
        order_id = data.get("order_id")
        if not order_id:
            for oid, ord_info in self.state["orders"].items():
                if ord_info.get("user_id") == data["user_id"] and ord_info.get("status") in ("pending", "created"):
                    order_id = oid
                    break

        # Check balance invariant: if balance before payment was less than amount, flag invalid state
        is_valid = user["balance"] >= amount
        if not is_valid:
            self._diagnostics.append({
                "event_index": self._event_count + 1,
                "type": "payment.completed",
                "is_valid": False,
                "reason": "Payment cannot be completed because the available balance is insufficient.",
                "user_id": data["user_id"],
                "order_id": order_id,
                "amount": amount,
                "balance_before": user["balance"],
                "deficit": amount - user["balance"],
            })
        else:
            self._diagnostics.append({
                "event_index": self._event_count + 1,
                "type": "payment.completed",
                "is_valid": True,
                "reason": None,
                "user_id": data["user_id"],
                "order_id": order_id,
                "amount": amount,
            })

        # If payment is valid, deduct from balance and update order
        if is_valid:
            user["balance"] -= amount
        else:
            # When payment is invalid (insufficient funds), balance must NOT drop into negative.
            # Balance is preserved and kept at >= 0.0.
            user["balance"] = max(0.0, user["balance"])

        payment_entry = {
            "user_id": data["user_id"],
            "amount": amount,
            "method": data.get("method", "UPI"),
            "status": "success" if is_valid else "failed_insufficient_funds",
        }

        if order_id:
            payment_entry["order_id"] = order_id
            if order_id in self.state["orders"]:
                order = self.state["orders"][order_id]
                if is_valid:
                    order["paid_amount"] = order.get("paid_amount", 0.0) + amount
                    if order["paid_amount"] >= order["amount"]:
                        order["status"] = "paid"

        self.state["payments"].append(payment_entry)

    # =========================================================
    # ORDER CREATED
    # =========================================================

    def _order_created(self, data):

        user = self._get_user(data["user_id"])

        order_id = data["order_id"]

        self.state["orders"][order_id] = {
            "order_id": order_id,
            "user_id": user["user_id"],
            "amount": float(data["amount"]),
            "paid_amount": 0.0,
            "status": "pending",
        }

    # =========================================================
    # ORDER UPDATED
    # =========================================================

    def _order_updated(self, data):

        order_id = data["order_id"]

        if order_id not in self.state["orders"]:
            raise ValueError(
                f"Order '{order_id}' does not exist."
            )

        self.state["orders"][order_id]["status"] = data["status"]

    # =========================================================
    # USER DELETED
    # =========================================================

    def _user_deleted(self, data):
        user_id = data.get("user_id")
        if user_id in self.state["users"]:
            del self.state["users"][user_id]

    # =========================================================
    # FILE EVENTS
    # =========================================================

    def _file_created(self, data):
        file_path = data["file_path"]
        self.state["files"][file_path] = {
            "file_path": file_path,
            "snapshot_id": data.get("snapshot_id"),
            "content_hash": data.get("content_hash"),
            "exists": True,
        }

    def _file_modified(self, data):
        file_path = data["file_path"]
        self.state["files"][file_path] = {
            "file_path": file_path,
            "snapshot_id": data.get("snapshot_id"),
            "content_hash": data.get("content_hash"),
            "exists": True,
        }

    def _file_deleted(self, data):
        file_path = data["file_path"]
        if file_path in self.state["files"]:
            self.state["files"][file_path]["exists"] = False
        else:
            self.state["files"][file_path] = {
                "file_path": file_path,
                "snapshot_id": None,
                "content_hash": None,
                "exists": False,
            }

    def _file_restored(self, data):
        file_path = data["file_path"]
        self.state["files"][file_path] = {
            "file_path": file_path,
            "snapshot_id": data.get("snapshot_id"),
            "content_hash": data.get("content_hash"),
            "exists": True,
        }

    def _apply_state_restored(self, data: dict) -> None:
        source_event_number = data["source_event_number"]

        if not isinstance(source_event_number, int):
            raise ValueError("source_event_number must be an integer.")

        if source_event_number < 1:
            raise ValueError("source_event_number must be at least 1.")

        if source_event_number > len(self._snapshots):
            raise ValueError("Cannot restore to a future or unavailable event.")

        self.state = deepcopy(self._snapshots[source_event_number - 1])

    # =========================================================
    # HELPERS
    # =========================================================

    def _get_user(self, user_id):

        if user_id not in self.state["users"]:
            raise ValueError(
                f"User '{user_id}' does not exist."
            )

        return self.state["users"][user_id]

    # =========================================================
    # STATE
    # =========================================================

    def get_state(self):

        return {
            "users": {
                key: dict(value)
                for key, value in self.state["users"].items()
            },
            "orders": {
                key: dict(value)
                for key, value in self.state["orders"].items()
            },
            "payments": list(self.state.get("payments", [])),
            "files": {
                key: dict(value)
                for key, value in self.state.get("files", {}).items()
            },
        }

    # =========================================================
    # USER STATE
    # =========================================================

    def get_user(self, user_id):

        return dict(
            self._get_user(user_id)
        )

    # =========================================================
    # ORDER STATE
    # =========================================================

    def get_order(self, order_id):

        if order_id not in self.state["orders"]:
            raise ValueError(
                f"Order '{order_id}' does not exist."
            )

        return dict(
            self.state["orders"][order_id]
        )

    # =========================================================
    # SNAPSHOTS & COUNTS
    # =========================================================

    def get_snapshot(self, event_number: int) -> dict:
        if event_number < 1:
            raise ValueError("Event number must be at least 1.")

        if event_number > len(self._snapshots):
            raise ValueError("Requested event number does not exist.")

        return deepcopy(self._snapshots[event_number - 1])

    def event_count(self) -> int:
        return self._event_count

    def get_diagnostics(self) -> list:
        return list(self._diagnostics)

    def get_event_validity(self, event_number: int) -> dict:
        for diag in self._diagnostics:
            if diag.get("event_index") == event_number:
                return diag
        return {"event_index": event_number, "is_valid": True, "reason": None}

    def reset(self) -> None:
        self.state = {
            "users": {},
            "orders": {},
            "payments": [],
            "files": {},
        }
        self._snapshots = []
        self._diagnostics = []
        self._event_count = 0
