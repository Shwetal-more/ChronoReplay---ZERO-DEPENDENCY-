import os
import tempfile
import unittest

from src.event import Event
from src.store import EventStore
from src.replay import ReplayEngine


class TestReplayEngine(unittest.TestCase):

    def setUp(self):
        """
        Create a temporary database for every test.
        """

        self.temp_file = tempfile.NamedTemporaryFile(
            delete=False
        )

        self.database_path = self.temp_file.name

        self.temp_file.close()

        self.store = EventStore(
            self.database_path
        )

        self.replay = ReplayEngine(
            self.store
        )

    def tearDown(self):
        """
        Remove the temporary database.
        """

        if os.path.exists(
            self.database_path
        ):
            os.remove(
                self.database_path
            )

    def create_user_event(self):
        return Event.create(
            "user.created",
            {
                "user_id": "U001",
                "name": "Alice",
                "email": "alice@example.com",
                "age": 22,
            },
        )

    def add_balance_event(self, amount):
        return Event.create(
            "balance.added",
            {
                "user_id": "U001",
                "amount": amount,
            },
        )

    def test_empty_history(self):
        """
        Replaying an empty database should return
        an empty state.
        """

        state = self.replay.replay_all()

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

    def test_replay_all(self):
        """
        All stored events should be reconstructed.
        """

        self.store.save(
            self.create_user_event()
        )

        self.store.save(
            self.add_balance_event(500)
        )

        state = self.replay.replay_all()

        self.assertEqual(
            state["users"]["U001"]["balance"],
            500,
        )

    def test_replay_until_first_event(self):
        """
        Replaying only the first event should not
        include later changes.
        """

        self.store.save(
            self.create_user_event()
        )

        self.store.save(
            self.add_balance_event(500)
        )

        state = self.replay.replay_until(1)

        self.assertEqual(
            state["users"]["U001"]["balance"],
            0,
        )

    def test_replay_until_second_event(self):
        """
        Replaying two events should include the
        balance change.
        """

        self.store.save(
            self.create_user_event()
        )

        self.store.save(
            self.add_balance_event(500)
        )

        state = self.replay.replay_until(2)

        self.assertEqual(
            state["users"]["U001"]["balance"],
            500,
        )

    def test_replay_until_middle_of_history(self):
        """
        Only events before the selected point
        should affect the reconstructed state.
        """

        self.store.save(
            self.create_user_event()
        )

        self.store.save(
            self.add_balance_event(500)
        )

        self.store.save(
            self.add_balance_event(1000)
        )

        state = self.replay.replay_until(2)

        self.assertEqual(
            state["users"]["U001"]["balance"],
            500,
        )

    def test_replay_all_includes_every_event(self):
        """
        The final state should contain all changes.
        """

        self.store.save(
            self.create_user_event()
        )

        self.store.save(
            self.add_balance_event(500)
        )

        self.store.save(
            self.add_balance_event(1000)
        )

        state = self.replay.replay_all()

        self.assertEqual(
            state["users"]["U001"]["balance"],
            1500,
        )

    def test_replay_by_event_id(self):
        """
        State can be reconstructed using an event ID.
        """

        first = self.create_user_event()

        second = self.add_balance_event(500)

        third = self.add_balance_event(1000)

        self.store.save(first)
        self.store.save(second)
        self.store.save(third)

        state = self.replay.replay_event(
            second.id
        )

        self.assertEqual(
            state["users"]["U001"]["balance"],
            500,
        )

    def test_invalid_event_number(self):
        """
        Invalid event numbers should fail.
        """

        self.store.save(
            self.create_user_event()
        )

        with self.assertRaises(ValueError):
            self.replay.replay_until(0)

    def test_event_number_too_large(self):
        """
        Replaying beyond the available history
        should fail.
        """

        self.store.save(
            self.create_user_event()
        )

        with self.assertRaises(ValueError):
            self.replay.replay_until(100)

    def test_missing_event_id(self):
        """
        An unknown event ID should fail.
        """

        with self.assertRaises(ValueError):
            self.replay.replay_event(
                "does-not-exist"
            )

    def test_history_count(self):
        """
        History count should match stored events.
        """

        self.store.save(
            self.create_user_event()
        )

        self.store.save(
            self.add_balance_event(500)
        )

        self.assertEqual(
            self.replay.history_count(),
            2,
        )


if __name__ == "__main__":
    unittest.main()