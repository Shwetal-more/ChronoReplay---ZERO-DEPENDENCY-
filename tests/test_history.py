import os
import tempfile
import unittest

from src.event import Event
from src.snapshot import Snapshot
from src.store import EventStore
from src.history import VersionHistory


class TestVersionHistory(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.database_path = os.path.join(
            self.temp_dir.name,
            "test.db"
        )

        self.store = EventStore(
            self.database_path
        )

        self.history = VersionHistory(
            self.store
        )

    def tearDown(self):

        self.temp_dir.cleanup()

    def _create_file_event(
        self,
        event_type,
        file_path,
        content=None
    ):

        data = {
            "file_path": file_path
        }

        if content is not None:

            snapshot = Snapshot.create(
                "snapshot-" + str(
                    self.store.count()
                ),
                file_path,
                content
            )

            self.store.save_snapshot(
                snapshot
            )

            data["snapshot_id"] = (
                snapshot.snapshot_id
            )

            data["content_hash"] = (
                snapshot.content_hash
            )

        event = Event.create(
            event_type,
            data
        )

        self.store.save(
            event
        )

        return event

    def test_list_files(self):

        self._create_file_event(
            "file.created",
            "main.py",
            "print('hello')"
        )

        self._create_file_event(
            "file.created",
            "app.py",
            "print('app')"
        )

        files = self.history.list_files()

        self.assertEqual(
            files,
            ["app.py", "main.py"]
        )

    def test_get_file_history(self):

        self._create_file_event(
            "file.created",
            "main.py",
            "version 1"
        )

        self._create_file_event(
            "file.modified",
            "main.py",
            "version 2"
        )

        self._create_file_event(
            "file.modified",
            "main.py",
            "version 3"
        )

        history = self.history.get_file_history(
            "main.py"
        )

        self.assertEqual(
            len(history),
            3
        )

        self.assertEqual(
            history[0].version,
            1
        )

        self.assertEqual(
            history[1].version,
            2
        )

        self.assertEqual(
            history[2].version,
            3
        )

    def test_get_version(self):

        self._create_file_event(
            "file.created",
            "main.py",
            "hello"
        )

        version = self.history.get_version(
            "main.py",
            1
        )

        self.assertIsNotNone(
            version
        )

        self.assertEqual(
            version.event_type,
            "file.created"
        )

    def test_missing_version(self):

        self._create_file_event(
            "file.created",
            "main.py",
            "hello"
        )

        version = self.history.get_version(
            "main.py",
            99
        )

        self.assertIsNone(
            version
        )

    def test_latest_version(self):

        self._create_file_event(
            "file.created",
            "main.py",
            "one"
        )

        self._create_file_event(
            "file.modified",
            "main.py",
            "two"
        )

        latest = self.history.latest_version(
            "main.py"
        )

        self.assertEqual(
            latest.version,
            2
        )

    def test_deleted_version_has_no_snapshot(self):

        self._create_file_event(
            "file.created",
            "main.py",
            "hello"
        )

        self._create_file_event(
            "file.deleted",
            "main.py"
        )

        deleted = self.history.latest_version(
            "main.py"
        )

        self.assertTrue(
            deleted.is_deleted()
        )

        self.assertIsNone(
            deleted.snapshot_id
        )

    def test_get_content(self):

        self._create_file_event(
            "file.created",
            "main.py",
            "print('hello')"
        )

        content = self.history.get_content(
            "main.py",
            1
        )

        self.assertEqual(
            content,
            "print('hello')"
        )

    def test_get_content_for_deleted_version(self):

        self._create_file_event(
            "file.created",
            "main.py",
            "hello"
        )

        self._create_file_event(
            "file.deleted",
            "main.py"
        )

        content = self.history.get_content(
            "main.py",
            2
        )

        self.assertIsNone(
            content
        )

    def test_integrity_failure(self):

        snapshot = Snapshot.create(
            "snapshot-1",
            "main.py",
            "original"
        )

        self.store.save_snapshot(
            snapshot
        )

        event = Event.create(
            "file.created",
            {
                "file_path": "main.py",
                "snapshot_id": snapshot.snapshot_id,
                "content_hash": snapshot.content_hash,
            }
        )

        self.store.save(
            event
        )

        # Simulate corrupted snapshot object by
        # modifying the stored content directly.
        connection = self.store._connect()

        try:

            connection.execute(
                """
                UPDATE snapshots
                SET content = ?
                WHERE snapshot_id = ?
                """,
                (
                    "CORRUPTED",
                    snapshot.snapshot_id
                )
            )

            connection.commit()

        finally:

            connection.close()

        with self.assertRaises(ValueError):

            self.history.get_content(
                "main.py",
                1
            )


if __name__ == "__main__":
    unittest.main()