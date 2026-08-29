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


if __name__ == "__main__":
    unittest.main()