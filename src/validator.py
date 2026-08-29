"""
Event validator module.

This module checks whether an event follows the rules
defined in the ChronoReplay event schema.

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
    - whether values are within the expected range
    """

    # All event types currently supported by ChronoReplay.
    supported_event_types = {
        "user.created",
        "profile.updated",
        "status.changed",
        "balance.added",
        "payment.completed",
        "order.created",
        "order.updated",
        "user.deleted",
        "file.created",
        "file.modified",
        "file.deleted",
        "file.restored",
    }

    # Allowed values for status.changed.
    VALID_STATUS_VALUES = {
        "active",
        "inactive",
        "suspended",
    }

    # Allowed values for payment.completed.
    VALID_PAYMENT_METHODS = {
        "UPI",
        "CARD",
        "CASH",
    }

    # Allowed values for order.updated.
    VALID_ORDER_STATUSES = {
        "pending",
        "confirmed",
        "shipped",
        "completed",
        "cancelled",
    }

    @classmethod
    def validate(cls, event: Event) -> None:
        """
        Validate an Event.

        If the event is valid, this method returns None.

        If the event is invalid, ValueError is raised
        with a message explaining the problem.
        """

        # Make sure the supplied object is actually an Event.
        if not isinstance(event, Event):
            raise ValueError(
                "Invalid event object. "
                "Must be an instance of Event class."
            )

        # Check whether we recognize this event type.
        #
        # IMPORTANT:
        # Our Event class uses the field name "type",
        # not "event_type".
        if event.type not in cls.supported_event_types:
            raise ValueError(
                f"Unsupported event type: {event.type}"
            )

        # Connect every event type to its validation function.
        validators = {
            "user.created": cls._validate_user_created,
            "profile.updated": cls._validate_profile_updated,
            "status.changed": cls._validate_status_changed,
            "balance.added": cls._validate_balance_added,
            "payment.completed": cls._validate_payment_completed,
            "order.created": cls._validate_order_created,
            "order.updated": cls._validate_order_updated,
            "user.deleted": cls._validate_user_deleted,
            "file.created": cls._validate_file_created,
            "file.modified": cls._validate_file_modified,
            "file.deleted": cls._validate_file_deleted,
            "file.restored": cls._validate_file_restored,
        }

        # Run the validator belonging to this event type.
        validators[event.type](event.data)

    @staticmethod
    def _require_string(data: dict, field: str) -> None:
        """
        Make sure a field:
        1. exists
        2. contains a string
        3. is not an empty string
        """

        # Check whether the field exists.
        if field not in data:
            raise ValueError(
                f"Missing required field: {field}"
            )

        # Check whether the value is a string.
        if not isinstance(data[field], str):
            raise ValueError(
                f"Field '{field}' must be a string."
            )

        # Check whether the string contains something.
        if not data[field].strip():
            raise ValueError(
                f"Field '{field}' cannot be empty."
            )

    @staticmethod
    def _require_number(data: dict, field: str) -> None:
        """
        Make sure a field:
        1. exists
        2. contains a number

        bool is explicitly excluded because Python considers
        bool to be a subclass of int.
        """

        # Check whether the field exists.
        if field not in data:
            raise ValueError(
                f"Missing required field: {field}"
            )

        value = data[field]

        # Accept int and float, but reject bool.
        if isinstance(value, bool) or not isinstance(
            value, (int, float)
        ):
            raise ValueError(
                f"Field '{field}' must be a number."
            )

    @staticmethod
    def _require_integer(data: dict, field: str) -> None:
        """
        Make sure a field:
        1. exists
        2. contains an integer

        bool is excluded because bool is technically
        a subclass of int in Python.
        """

        # Check whether the field exists.
        if field not in data:
            raise ValueError(
                f"Missing required field: {field}"
            )

        value = data[field]

        # Check that the value is an integer.
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                f"Field '{field}' must be an integer."
            )

    @classmethod
    def _validate_user_created(cls, data: dict) -> None:
        """
        Validate a user.created event.

        Required fields:
        - user_id -> string
        - name    -> string
        - email   -> string
        - age     -> integer
        """

        cls._require_string(data, "user_id")
        cls._require_string(data, "name")
        cls._require_string(data, "email")
        cls._require_integer(data, "age")

        # Age cannot be negative.
        if data["age"] < 0:
            raise ValueError(
                "Field 'age' must be a non-negative integer."
            )

    @classmethod
    def _validate_profile_updated(cls, data: dict) -> None:
        """
        Validate a profile.updated event.

        Required fields:
        - user_id -> string
        - name    -> string
        - city    -> string
        """

        cls._require_string(data, "user_id")
        cls._require_string(data, "name")
        cls._require_string(data, "city")

    @classmethod
    def _validate_status_changed(cls, data: dict) -> None:
        """
        Validate a status.changed event.

        Required fields:
        - user_id -> string
        - status  -> one of the allowed status values
        """

        cls._require_string(data, "user_id")
        cls._require_string(data, "status")

        # Check whether the status is allowed.
        if data["status"] not in cls.VALID_STATUS_VALUES:
            raise ValueError(
                f"Invalid status value: {data['status']}. "
                f"Must be one of {sorted(cls.VALID_STATUS_VALUES)}"
            )

    @classmethod
    def _validate_balance_added(cls, data: dict) -> None:
        """
        Validate a balance.added event.

        Required fields:
        - user_id -> string
        - amount  -> positive number
        """

        cls._require_string(data, "user_id")
        cls._require_number(data, "amount")

        # Balance addition must be greater than zero.
        if data["amount"] <= 0:
            raise ValueError(
                "Balance amount must be greater than zero."
            )

    @classmethod
    def _validate_payment_completed(cls, data: dict) -> None:
        """
        Validate a payment.completed event.

        Required fields:
        - user_id -> string
        - amount  -> positive number
        - method  -> UPI, CARD, or CASH
        """

        cls._require_string(data, "user_id")
        cls._require_number(data, "amount")
        cls._require_string(data, "method")

        # Payment amount must be positive.
        if data["amount"] <= 0:
            raise ValueError(
                "Payment amount must be greater than zero."
            )

        # Payment method must be one of our supported methods.
        if data["method"] not in cls.VALID_PAYMENT_METHODS:
            raise ValueError(
                f"Invalid payment method: {data['method']}. "
                f"Must be one of "
                f"{sorted(cls.VALID_PAYMENT_METHODS)}"
            )

    @classmethod
    def _validate_order_created(cls, data: dict) -> None:
        """
        Validate an order.created event.

        Required fields:
        - order_id -> string
        - user_id  -> string
        - amount   -> positive number
        """

        cls._require_string(data, "order_id")
        cls._require_string(data, "user_id")
        cls._require_number(data, "amount")

        # Order amount must be positive.
        if data["amount"] <= 0:
            raise ValueError(
                "Order amount must be greater than zero."
            )

    @classmethod
    def _validate_order_updated(cls, data: dict) -> None:
        """
        Validate an order.updated event.

        Required fields:
        - order_id -> string
        - status   -> one of the allowed order statuses
        """

        cls._require_string(data, "order_id")
        cls._require_string(data, "status")

        # Check whether the order status is supported.
        if data["status"] not in cls.VALID_ORDER_STATUSES:
            raise ValueError(
                f"Invalid order status: {data['status']}. "
                f"Must be one of "
                f"{sorted(cls.VALID_ORDER_STATUSES)}"
            )

    @classmethod
    def _validate_user_deleted(cls, data: dict) -> None:
        """
        Validate a user.deleted event.

        Required fields:
        - user_id -> string
        """

        cls._require_string(data, "user_id")

    @classmethod
    def _validate_file_created(cls, data: dict) -> None:
        """Validate file.created."""

        cls._require_string(data, "file_path")
        cls._require_string(data, "snapshot_id")
        cls._require_string(data, "content_hash")


    @classmethod
    def _validate_file_modified(cls, data: dict) -> None:
        """Validate file.modified."""

        cls._require_string(data, "file_path")
        cls._require_string(data, "snapshot_id")
        cls._require_string(data, "content_hash")


    @classmethod
    def _validate_file_deleted(cls, data: dict) -> None:
        """Validate file.deleted."""

        cls._require_string(data, "file_path")


    @classmethod
    def _validate_file_restored(cls, data: dict) -> None:
        """Validate file.restored."""

        cls._require_string(data, "file_path")
        cls._require_string(data, "snapshot_id")
        cls._require_string(data, "content_hash")