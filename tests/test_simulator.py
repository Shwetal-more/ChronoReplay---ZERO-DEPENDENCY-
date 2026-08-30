import unittest
import os
from src.store import EventStore
from src.simulator import EventSimulator
from src.state import StateEngine
from src.replay import ReplayEngine
from src.event import Event


class TestEventSimulator(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_simulator.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.store = EventStore(self.db_path)
        self.simulator = EventSimulator(self.store)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_full_simulation_flow(self):
        # 1. Create user
        user_event = self.simulator.create_user("Alice", "alice@example.com", 25)
        self.assertTrue(user_event.data["user_id"].startswith("USR-"))
        user_id = user_event.data["user_id"]

        # 2. Add balance 500
        balance_event = self.simulator.add_balance(500.0)
        self.assertEqual(balance_event.data["user_id"], user_id)
        self.assertEqual(balance_event.data["amount"], 500.0)

        # 3. Create order 200
        order_event = self.simulator.create_order(200.0)
        self.assertTrue(order_event.data["order_id"].startswith("ORD-"))
        self.assertEqual(order_event.data["user_id"], user_id)
        order_id = order_event.data["order_id"]

        # 4. Pay 200
        pay1 = self.simulator.complete_payment(200.0, "UPI")
        self.assertEqual(pay1.data["amount"], 200.0)

        # 5. Pay 300
        pay2 = self.simulator.complete_payment(300.0, "UPI")
        self.assertEqual(pay2.data["amount"], 300.0)

        # 6. Add 300
        add2 = self.simulator.add_balance(300.0)
        self.assertEqual(add2.data["amount"], 300.0)

        # 7. Pay 300
        pay3 = self.simulator.complete_payment(300.0, "UPI")
        self.assertEqual(pay3.data["amount"], 300.0)

        # Verify state reconstruction
        engine = StateEngine()
        for event in self.store.get_all():
            engine.apply(event)

        state = engine.get_state()
        self.assertEqual(state["users"][user_id]["balance"], 0.0)
        self.assertEqual(state["orders"][order_id]["amount"], 200.0)

        # Verify replay engine timelines
        replay = ReplayEngine(self.store)
        user_timeline = replay.get_user_timeline(user_id)
        self.assertEqual(len(user_timeline), 7)

        order_timeline = replay.get_order_timeline(order_id)
        self.assertEqual(len(order_timeline), 4)

        # Replay at event 1 (after user created)
        state_at_1 = replay.state_at_event(1)
        self.assertEqual(state_at_1["users"][user_id]["balance"], 0.0)

        # Replay at event 2 (after balance added 500)
        state_at_2 = replay.state_at_event(2)
        self.assertEqual(state_at_2["users"][user_id]["balance"], 500.0)

        # Replay before event 2
        state_before_2 = replay.state_before_event(2)
        self.assertEqual(state_before_2["users"][user_id]["balance"], 0.0)


if __name__ == "__main__":
    unittest.main()
