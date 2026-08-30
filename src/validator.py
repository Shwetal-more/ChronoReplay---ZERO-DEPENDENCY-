"""
Event validator module.

This module checks whether an event follows
the rules defined in the ChronoReplay event schema.

Only Python standard-library functionality is used.
"""

from src.event import Event


class EventValidator:
    """
    Validates ChronoReplay events.

    The validator checks:

    - whether the event type is supported
    - whether required fields are present
    - whether field values have the correct type
    - whether values are within expected ranges
    """

    supported_event_types = {
        "user.created",
        "profile.updated",
        "status.changed",
        "balance.added",
        "payment.completed",
        "order.created",
        "order.updated",
        "user.deleted",

        # ChronoReplay workspace events
        "file.created",
        "file.modified",
        "file.deleted",
        "file.restored",

        # State recovery events
        "state.restored",
    }

    VALID_STATUS_VALUES = {
        "active",
        "inactive",
        "suspended",
    }

    VALID_PAYMENT_METHODS = {
        "UPI",
        "CARD",
        "CASH",
    }

    VALID_ORDER_STATUSES = {
        "pending",
        "confirmed",
        "shipped",
        "completed",
        "paid",
    }

    @classmethod
    def validate(cls, event: Event) -> None:
        """
        Validate an Event.

        If valid:
            returns None

        If invalid:
            raises ValueError.
        """

        if not isinstance(event, Event):
            raise ValueError(
                "Invalid event object. "
                "Must be an instance of Event class."
            )

        # IMPORTANT:
        # Event uses .type, not .event_type.
        if event.type not in cls.supported_event_types:
            raise ValueError(
                f"Unsupported event type: {event.type}"
            )

        validators = {
            "user.created":
                cls._validate_user_created,

            "profile.updated":
                cls._validate_profile_updated,

            "status.changed":
                cls._validate_status_changed,

            "balance.added":
                cls._validate_balance_added,

            "payment.completed":
                cls._validate_payment_completed,

            "order.created":
                cls._validate_order_created,

            "order.updated":
                cls._validate_order_updated,

            "user.deleted":
                cls._validate_user_deleted,

            # ChronoReplay file events
            "file.created":
                cls._validate_file_created,

            "file.modified":
                cls._validate_file_modified,

            "file.deleted":
                cls._validate_file_deleted,

            "file.restored":
                cls._validate_file_restored,

            # ChronoReplay state recovery
            "state.restored":
                cls._validate_state_restored,
        }

        validators[event.type](
            event.data
        )

    @staticmethod
    def _require_string(
        data: dict,
        field: str
    ) -> None:
        """
        Ensure a field exists and contains
        a non-empty string.
        """

        if field not in data:
            raise ValueError(
                f"missing required field: {field}"
            )

        if not isinstance(
            data[field],
            str
        ):
            raise ValueError(
                f"field {field} must be a string."
            )

        if not data[field].strip():
            raise ValueError(
                f"field {field} cannot be empty."
            )

    @staticmethod
    def _require_number(
        data: dict,
        field: str
    ) -> None:
        """
        Ensure a field exists and contains
        a number.

        bool is excluded because bool is technically
        a subclass of int in Python.
        """

        if field not in data:
            raise ValueError(
                f"missing required field: {field}"
            )

        value = data[field]

        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                (int, float)
            )
        ):
            raise ValueError(
                f"field {field} must be a number."
            )

    @staticmethod
    def _require_integer(
        data: dict,
        field: str
    ) -> None:
        """
        Ensure a field exists and contains
        an integer.
        """

        if field not in data:
            raise ValueError(
                f"missing required field: {field}"
            )

        value = data[field]

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
        ):
            raise ValueError(
                f"field {field} must be an integer."
            )

    @classmethod
    def _validate_user_created(
        cls,
        data: dict
    ) -> None:
        """
        Validate user.created.

        Required:
            user_id -> string
            name    -> string
            email   -> string
            age     -> integer
        """

        cls._require_string(
            data,
            "user_id"
        )

        cls._require_string(
            data,
            "name"
        )

        cls._require_string(
            data,
            "email"
        )

        cls._require_integer(
            data,
            "age"
        )

        if data["age"] < 0:
            raise ValueError(
                "field age must be a non-negative integer."
            )

    @classmethod
    def _validate_profile_updated(
        cls,
        data: dict
    ) -> None:
        """
        Validate profile.updated.

        Required:
            user_id -> string
            name    -> string
            city    -> string
        """

        cls._require_string(
            data,
            "user_id"
        )

        cls._require_string(
            data,
            "name"
        )

        cls._require_string(
            data,
            "city"
        )

    @classmethod
    def _validate_status_changed(
        cls,
        data: dict
    ) -> None:
        """
        Validate status.changed.
        """

        cls._require_string(
            data,
            "user_id"
        )

        cls._require_string(
            data,
            "status"
        )

        if data["status"] not in cls.VALID_STATUS_VALUES:
            raise ValueError(
                f"Invalid status value: "
                f"{data['status']}. "
                f"Must be one of "
                f"{cls.VALID_STATUS_VALUES}"
            )

    @classmethod
    def _validate_balance_added(
        cls,
        data: dict
    ) -> None:
        """
        Validate balance.added.
        """

        cls._require_string(
            data,
            "user_id"
        )

        cls._require_number(
            data,
            "amount"
        )

        if data["amount"] <= 0:
            raise ValueError(
                "Balance amount must be greater than zero"
            )

    @classmethod
    def _validate_payment_completed(
        cls,
        data: dict
    ) -> None:
        """
        Validate payment.completed.
        """

        cls._require_string(
            data,
            "user_id"
        )

        cls._require_number(
            data,
            "amount"
        )

        cls._require_string(
            data,
            "method"
        )

        if data["amount"] <= 0:
            raise ValueError(
                "Payment amount must be greater than zero"
            )

        if data["method"] not in cls.VALID_PAYMENT_METHODS:
            raise ValueError(
                f"Invalid payment method: "
                f"{data['method']}"
            )

        if "order_id" in data and data["order_id"] is not None:
            if not isinstance(data["order_id"], str) or not data["order_id"].strip():
                raise ValueError("field order_id must be a non-empty string if provided.")

    @classmethod
    def _validate_order_created(
        cls,
        data: dict
    ) -> None:
        """
        Validate order.created.
        """

        cls._require_string(
            data,
            "order_id"
        )

        cls._require_string(
            data,
            "user_id"
        )

        cls._require_number(
            data,
            "amount"
        )

        if data["amount"] <= 0:
            raise ValueError(
                "Order amount must be greater than zero"
            )

    @classmethod
    def _validate_order_updated(
        cls,
        data: dict
    ) -> None:
        """
        Validate order.updated.
        """

        cls._require_string(
            data,
            "order_id"
        )

        cls._require_string(
            data,
            "status"
        )

        if data["status"] not in cls.VALID_ORDER_STATUSES:
            raise ValueError(
                f"Invalid order status: "
                f"{data['status']}"
            )

    @classmethod
    def _validate_user_deleted(
        cls,
        data: dict
    ) -> None:
        """
        Validate user.deleted.
        """

        cls._require_string(
            data,
            "user_id"
        )

    # =========================================================
    # CHRONOREPLAY FILE EVENTS
    # =========================================================

    @classmethod
    def _validate_file_created(
        cls,
        data: dict
    ) -> None:
        """
        Validate file.created.

        Required:
            file_path
            snapshot_id
            content_hash
        """

        cls._require_string(
            data,
            "file_path"
        )

        cls._require_string(
            data,
            "snapshot_id"
        )

        cls._require_string(
            data,
            "content_hash"
        )

    @classmethod
    def _validate_file_modified(
        cls,
        data: dict
    ) -> None:
        """
        Validate file.modified.

        Required:
            file_path
            snapshot_id
            content_hash
        """

        cls._require_string(
            data,
            "file_path"
        )

        cls._require_string(
            data,
            "snapshot_id"
        )

        cls._require_string(
            data,
            "content_hash"
        )

    @classmethod
    def _validate_file_deleted(
        cls,
        data: dict
    ) -> None:
        """
        Validate file.deleted.

        Required:
            file_path
        """

        cls._require_string(
            data,
            "file_path"
        )

    @classmethod
    def _validate_file_restored(
        cls,
        data: dict
    ) -> None:
        """
        Validate file.restored.

        Required:
            file_path
            snapshot_id
            content_hash
        """

        cls._require_string(
            data,
            "file_path"
        )

        cls._require_string(
            data,
            "snapshot_id"
        )

        cls._require_string(
            data,
            "content_hash"
        )

    @classmethod
    def _validate_state_restored(
        cls,
        data: dict
    ) -> None:
        """
        Validate state.restored.

        Required:
            source_event_number (int >= 1)
        """
        if "source_event_number" not in data:
            raise ValueError("missing required field: source_event_number")

        val = data["source_event_number"]
        if isinstance(val, bool) or not isinstance(val, int):
            raise ValueError("field source_event_number must be an integer.")

        if val < 1:
            raise ValueError("source_event_number must be at least 1.")
