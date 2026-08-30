import os
import tempfile
import unittest
import shutil

from src.snapshot import Snapshot
from src.store import EventStore


class TestSnapshotStore(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.mkdtemp()

        self.database_path = os.path.join(
            self.temp_dir,
            "events.db"
        )

        self.store = EventStore(
            self.database_path
        )

    def tearDown(self):

        shutil.rmtree(
            self.temp_dir,
            ignore_errors=True
        )

    def create_snapshot(
        self,
        snapshot_id,
        file_path,
        content
    ):

        return Snapshot.create(
            snapshot_id,
            file_path,
            content
        )

    def test_save_snapshot(self):

        snapshot = self.create_snapshot(
            "snapshot-001",
            "main.py",
            'print("Hello")'
        )

        self.store.save_snapshot(
            snapshot
        )

        result = self.store.get_snapshot(
            "snapshot-001"
        )

        self.assertIsNotNone(
            result
        )

        self.assertEqual(
            result.content,
            'print("Hello")'
        )

    def test_snapshot_integrity(self):

        snapshot = self.create_snapshot(
            "snapshot-001",
            "main.py",
            'print("Hello")'
        )

        self.store.save_snapshot(
            snapshot
        )

        result = self.store.get_snapshot(
            "snapshot-001"
        )

        self.assertTrue(
            result.verify_integrity()
        )

    def test_get_snapshots_for_file(self):

        first = self.create_snapshot(
            "snapshot-001",
            "main.py",
            'print("A")'
        )

        second = self.create_snapshot(
            "snapshot-002",
            "main.py",
            'print("B")'
        )

        self.store.save_snapshot(first)
        self.store.save_snapshot(second)

        snapshots = (
            self.store.get_snapshots_for_file(
                "main.py"
            )
        )

        self.assertEqual(
            len(snapshots),
            2
        )

        self.assertEqual(
            snapshots[0].content,
            'print("A")'
        )

        self.assertEqual(
            snapshots[1].content,
            'print("B")'
        )

    def test_missing_snapshot(self):

        result = self.store.get_snapshot(
            "does-not-exist"
        )

        self.assertIsNone(
            result
        )


if __name__ == "__main__":
    unittest.main()