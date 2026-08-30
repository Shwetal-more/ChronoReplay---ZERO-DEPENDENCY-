import unittest

from src.event import Event
from src.state import StateEngine


class TestStateEngine(unittest.TestCase):

    def create_user(self):
        return Event.create(
            "user.created",
            {
                "user_id": "U001",
                "name": "Alice",
                "email": "alice@example.com",
                "age": 22,
            },
        )

    def test_initial_state(self):
        engine = StateEngine()

        state = engine.get_state()

        self.assertEqual(
            state["users"],
            {},
        )

        self.assertEqual(
            state["orders"],
            {},
        )

        self.assertEqual(
            state["payments"],
            [],
        )

    def test_user_created(self):
        engine = StateEngine()

        engine.apply(
            self.create_user()
        )

        state = engine.get_state()

        self.assertIn(
            "U001",
            state["users"],
        )

        self.assertEqual(
            state["users"]["U001"]["name"],
            "Alice",
        )

    def test_status_changed(self):
        engine = StateEngine()

        engine.apply(
            self.create_user()
        )

        event = Event.create(
            "status.changed",
            {
                "user_id": "U001",
                "status": "suspended",
            },
        )

        engine.apply(event)

        state = engine.get_state()

        self.assertEqual(
            state["users"]["U001"]["status"],
            "suspended",
        )

    def test_balance_added(self):
        engine = StateEngine()

        engine.apply(
            self.create_user()
        )

        event = Event.create(
            "balance.added",
            {
                "user_id": "U001",
                "amount": 500,
            },
        )

        engine.apply(event)

        state = engine.get_state()

        self.assertEqual(
            state["users"]["U001"]["balance"],
            500,
        )

    def test_multiple_balance_events(self):
        engine = StateEngine()

        engine.apply(
            self.create_user()
        )

        engine.apply(
            Event.create(
                "balance.added",
                {
                    "user_id": "U001",
                    "amount": 500,
                },
            )
        )

        engine.apply(
            Event.create(
                "balance.added",
                {
                    "user_id": "U001",
                    "amount": 250,
                },
            )
        )

        state = engine.get_state()

        self.assertEqual(
            state["users"]["U001"]["balance"],
            750,
        )

    def test_profile_update(self):
        engine = StateEngine()

        engine.apply(
            self.create_user()
        )

        engine.apply(
            Event.create(
                "profile.updated",
                {
                    "user_id": "U001",
                    "name": "Alice More",
                    "city": "Mumbai",
                },
            )
        )

        state = engine.get_state()

        self.assertEqual(
            state["users"]["U001"]["name"],
            "Alice More",
        )

        self.assertEqual(
            state["users"]["U001"]["city"],
            "Mumbai",
        )

    def test_user_deleted(self):
        engine = StateEngine()

        engine.apply(
            self.create_user()
        )

        engine.apply(
            Event.create(
                "user.deleted",
                {
                    "user_id": "U001",
                },
            )
        )

        state = engine.get_state()

        self.assertNotIn(
            "U001",
            state["users"],
        )

    def test_snapshot(self):
        engine = StateEngine()

        engine.apply(
            self.create_user()
        )

        engine.apply(
            Event.create(
                "balance.added",
                {
                    "user_id": "U001",
                    "amount": 500,
                },
            )
        )

        first_snapshot = engine.get_snapshot(1)

        second_snapshot = engine.get_snapshot(2)

        self.assertEqual(
            first_snapshot["users"]["U001"]["balance"],
            0,
        )

        self.assertEqual(
            second_snapshot["users"]["U001"]["balance"],
            500,
        )

    def test_event_count(self):
        engine = StateEngine()

        self.assertEqual(
            engine.event_count(),
            0,
        )

        engine.apply(
            self.create_user()
        )

        self.assertEqual(
            engine.event_count(),
            1,
        )

    def test_reset(self):
        engine = StateEngine()

        engine.apply(
            self.create_user()
        )

        engine.reset()

        self.assertEqual(
            engine.event_count(),
            0,
        )

        self.assertEqual(
            engine.get_state()["users"],
            {},
        )

    def test_payment_insufficient_balance_does_not_produce_negative_balance(self):
        """
        When user has balance 200 and tries to make payment of 300,
        the balance should NOT become negative (-100).
        It must remain non-negative, and the invariant violation is diagnosed.
        """
        engine = StateEngine()
        engine.apply(self.create_user())
        engine.apply(Event.create("balance.added", {"user_id": "U001", "amount": 200}))

        # State before payment
        self.assertEqual(engine.get_state()["users"]["U001"]["balance"], 200)

        # Payment exceeding balance
        engine.apply(Event.create("payment.completed", {"user_id": "U001", "amount": 300, "method": "UPI"}))

        # Balance must NOT be negative
        user_balance = engine.get_state()["users"]["U001"]["balance"]
        self.assertGreaterEqual(user_balance, 0)
        self.assertEqual(user_balance, 200)

        # Invariant violation diagnostics
        diag = engine.get_diagnostics()
        self.assertEqual(len(diag), 1)
        self.assertFalse(diag[0]["is_valid"])
        self.assertEqual(diag[0]["deficit"], 100)
        self.assertIn("insufficient", diag[0]["reason"])

    def test_order_payment_insufficient_then_topup_and_pay(self):
        """
        Tests the complete scenario:
        1. User creates an order (e.g. ₹200).
        2. User attempts payment with insufficient balance (balance = 0).
           -> Order stays pending (paid_amount = 0).
           -> Balance stays 0 (non-negative).
           -> Payment recorded with status failed_insufficient_funds and linked to order.
        3. User adds balance (e.g. ₹500).
        4. User pays ₹200.
           -> Order status becomes 'paid', paid_amount = 200.
           -> User balance becomes 300.
           -> Payment recorded with status 'success' and linked to order.
        """
        engine = StateEngine()
        engine.apply(self.create_user())

        # Create Order ORD-0001 for 200
        engine.apply(Event.create("order.created", {
            "user_id": "U001",
            "order_id": "ORD-0001",
            "amount": 200,
        }))

        state = engine.get_state()
        self.assertEqual(state["orders"]["ORD-0001"]["status"], "pending")
        self.assertEqual(state["orders"]["ORD-0001"]["paid_amount"], 0.0)
        self.assertEqual(state["users"]["U001"]["balance"], 0.0)

        # Attempt payment of 200 with 0 balance
        engine.apply(Event.create("payment.completed", {
            "user_id": "U001",
            "amount": 200,
            "method": "UPI",
            "order_id": "ORD-0001",
        }))

        state = engine.get_state()
        # Order must remain pending
        self.assertEqual(state["orders"]["ORD-0001"]["status"], "pending")
        self.assertEqual(state["orders"]["ORD-0001"]["paid_amount"], 0.0)
        # Balance must remain 0
        self.assertEqual(state["users"]["U001"]["balance"], 0.0)
        # Payment must be classified as failed
        self.assertEqual(len(state["payments"]), 1)
        self.assertEqual(state["payments"][0]["status"], "failed_insufficient_funds")
        self.assertEqual(state["payments"][0]["order_id"], "ORD-0001")

        # Now add balance 500
        engine.apply(Event.create("balance.added", {
            "user_id": "U001",
            "amount": 500,
        }))
        state = engine.get_state()
        self.assertEqual(state["users"]["U001"]["balance"], 500.0)

        # Now complete payment
        engine.apply(Event.create("payment.completed", {
            "user_id": "U001",
            "amount": 200,
            "method": "UPI",
            "order_id": "ORD-0001",
        }))

        state = engine.get_state()
        # Order must now be paid
        self.assertEqual(state["orders"]["ORD-0001"]["status"], "paid")
        self.assertEqual(state["orders"]["ORD-0001"]["paid_amount"], 200.0)
        # Balance must be 500 - 200 = 300
        self.assertEqual(state["users"]["U001"]["balance"], 300.0)
        # Payment must be recorded as success
        self.assertEqual(len(state["payments"]), 2)
        self.assertEqual(state["payments"][1]["status"], "success")
        self.assertEqual(state["payments"][1]["order_id"], "ORD-0001")


if __name__ == "__main__":
    unittest.main()