import unittest

from src.event import Event
from src.validator import EventValidator


class TestEventValidator(unittest.TestCase):
    """Tests for the ChronoReplay event validator."""

    # ---------------------------------------------------------
    # USER CREATED
    # ---------------------------------------------------------

    def test_valid_user_created(self):
        """A correctly formatted user.created event is valid."""

        event = Event.create(
            "user.created",
            {
                "user_id": "user-001",
                "name": "Alice",
                "email": "alice@example.com",
                "age": 22,
            },
        )

        # This should not raise an exception.
        EventValidator.validate(event)

    def test_user_created_missing_user_id(self):
        """user.created must contain user_id."""

        event = Event.create(
            "user.created",
            {
                "name": "Alice",
                "email": "alice@example.com",
                "age": 22,
            },
        )

        with self.assertRaises(ValueError):
            EventValidator.validate(event)

    def test_user_created_missing_name(self):
        """user.created must contain name."""

        event = Event.create(
            "user.created",
            {
                "user_id": "user-001",
                "email": "alice@example.com",
                "age": 22,
            },
        )

        with self.assertRaises(ValueError):
            EventValidator.validate(event)

    def test_user_created_invalid_age_type(self):
        """Age must be an integer."""

        event = Event.create(
            "user.created",
            {
                "user_id": "user-001",
                "name": "Alice",
                "email": "alice@example.com",
                "age": "twenty-two",
            },
        )

        with self.assertRaises(ValueError):
            EventValidator.validate(event)

    def test_user_created_negative_age(self):
        """Age cannot be negative."""

        event = Event.create(
            "user.created",
            {
                "user_id": "user-001",
                "name": "Alice",
                "email": "alice@example.com",
                "age": -5,
            },
        )

        with self.assertRaises(ValueError):
            EventValidator.validate(event)

    # ---------------------------------------------------------
    # PROFILE UPDATED
    # ---------------------------------------------------------

    def test_valid_profile_updated(self):
        """A valid profile.updated event should pass."""

        event = Event.create(
            "profile.updated",
            {
                "user_id": "user-001",
                "name": "Alice",
                "city": "Mumbai",
            },
        )

        EventValidator.validate(event)

    def test_profile_updated_missing_city(self):
        """profile.updated requires city."""

        event = Event.create(
            "profile.updated",
            {
                "user_id": "user-001",
                "name": "Alice",
            },
        )

        with self.assertRaises(ValueError):
            EventValidator.validate(event)

    # ---------------------------------------------------------
    # STATUS CHANGED
    # ---------------------------------------------------------

    def test_valid_status_changed(self):
        """A supported status should pass."""

        event = Event.create(
            "status.changed",
            {
                "user_id": "user-001",
                "status": "active",
            },
        )

        EventValidator.validate(event)

    def test_invalid_status_changed(self):
        """An unsupported status should fail."""

        event = Event.create(
            "status.changed",
            {
                "user_id": "user-001",
                "status": "unknown",
            },
        )

        with self.assertRaises(ValueError):
            EventValidator.validate(event)

    # ---------------------------------------------------------
    # BALANCE ADDED
    # ---------------------------------------------------------

    def test_valid_balance_added(self):
        """A positive balance addition should pass."""

        event = Event.create(
            "balance.added",
            {
                "user_id": "user-001",
                "amount": 500,
            },
        )

        EventValidator.validate(event)

    def test_negative_balance(self):
        """A negative balance addition should fail."""

        event = Event.create(
            "balance.added",
            {
                "user_id": "user-001",
                "amount": -500,
            },
        )

        with self.assertRaises(ValueError):
            EventValidator.validate(event)

    def test_zero_balance(self):
        """A zero balance addition should fail."""

        event = Event.create(
            "balance.added",
            {
                "user_id": "user-001",
                "amount": 0,
            },
        )

        with self.assertRaises(ValueError):
            EventValidator.validate(event)

    def test_balance_invalid_type(self):
        """Balance amount must be a number."""

        event = Event.create(
            "balance.added",
            {
                "user_id": "user-001",
                "amount": "500",
            },
        )

        with self.assertRaises(ValueError):
            EventValidator.validate(event)

    # ---------------------------------------------------------
    # PAYMENT COMPLETED
    # ---------------------------------------------------------

    def test_valid_payment(self):
        """A valid payment should pass."""

        event = Event.create(
            "payment.completed",
            {
                "user_id": "user-001",
                "amount": 200,
                "method": "UPI",
            },
        )

        EventValidator.validate(event)

    def test_invalid_payment_method(self):
        """Unsupported payment methods should fail."""

        event = Event.create(
            "payment.completed",
            {
                "user_id": "user-001",
                "amount": 200,
                "method": "BITCOIN",
            },
        )

        with self.assertRaises(ValueError):
            EventValidator.validate(event)

    def test_negative_payment(self):
        """Payment amount cannot be negative."""

        event = Event.create(
            "payment.completed",
            {
                "user_id": "user-001",
                "amount": -200,
                "method": "UPI",
            },
        )

        with self.assertRaises(ValueError):
            EventValidator.validate(event)

    # ---------------------------------------------------------
    # ORDER CREATED
    # ---------------------------------------------------------

    def test_valid_order_created(self):
        """A valid order.created event should pass."""

        event = Event.create(
            "order.created",
            {
                "order_id": "order-001",
                "user_id": "user-001",
                "amount": 1000,
            },
        )

        EventValidator.validate(event)

    def test_invalid_order_amount(self):
        """Order amount must be greater than zero."""

        event = Event.create(
            "order.created",
            {
                "order_id": "order-001",
                "user_id": "user-001",
                "amount": 0,
            },
        )

        with self.assertRaises(ValueError):
            EventValidator.validate(event)

    # ---------------------------------------------------------
    # ORDER UPDATED
    # ---------------------------------------------------------

    def test_valid_order_updated(self):
        """A valid order status should pass."""

        event = Event.create(
            "order.updated",
            {
                "order_id": "order-001",
                "status": "shipped",
            },
        )

        EventValidator.validate(event)

    def test_invalid_order_status(self):
        """An unsupported order status should fail."""

        event = Event.create(
            "order.updated",
            {
                "order_id": "order-001",
                "status": "random-status",
            },
        )

        with self.assertRaises(ValueError):
            EventValidator.validate(event)

    # ---------------------------------------------------------
    # USER DELETED
    # ---------------------------------------------------------

    def test_valid_user_deleted(self):
        """A valid user.deleted event should pass."""

        event = Event.create(
            "user.deleted",
            {
                "user_id": "user-001",
            },
        )

        EventValidator.validate(event)

    def test_user_deleted_missing_user_id(self):
        """user.deleted requires user_id."""

        event = Event.create(
            "user.deleted",
            {}

        )

        with self.assertRaises(ValueError):
            EventValidator.validate(event)

    # ---------------------------------------------------------
    # GENERAL VALIDATION
    # ---------------------------------------------------------

    def test_invalid_event_type(self):
        """An unsupported event type should fail."""

        event = Event.create(
            "something.random",
            {
                "hello": "world",
            },
        )

        with self.assertRaises(ValueError):
            EventValidator.validate(event)

    def test_invalid_event_object(self):
        """Validator should reject objects that are not Events."""

        with self.assertRaises(ValueError):
            EventValidator.validate(
                {
                    "type": "user.created",
                    "data": {},
                }
            )


if __name__ == "__main__":
    unittest.main()