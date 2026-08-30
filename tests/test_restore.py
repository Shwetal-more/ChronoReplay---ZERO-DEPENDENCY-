"""
Tests for ChronoReplay restore and version-history functionality.

Only Python standard-library modules are used.
"""

import os
import tempfile
import unittest

from src.event import Event
from src.snapshot import Snapshot
from src.store import EventStore
from src.restore import RestoreManager


class TestRestoreManager(unittest.TestCase):
    """
    Tests version history and snapshot restoration.
    """

    def setUp(self):
        """
        Create a temporary workspace and database
        for every test.
        """

        self.temp_directory = tempfile.TemporaryDirectory()

        self.workspace_path = os.path.join(
            self.temp_directory.name,
            "workspace"
        )

        os.makedirs(
            self.workspace_path,
            exist_ok=True
        )

        self.database_path = os.path.join(
            self.temp_directory.name,
            "events.db"
        )

        self.store = EventStore(
            self.database_path
        )

        self.manager = RestoreManager(
            self.workspace_path,
            self.store
        )

    def tearDown(self):
        """
        Remove the temporary workspace and database.
        """

        self.temp_directory.cleanup()

    # =========================================================
    # HELPERS
    # =========================================================

    def _create_snapshot(
        self,
        file_path,
        content
    ):
        """
        Create and store a snapshot.
        """

        snapshot = Snapshot.create(
            snapshot_id=os.urandom(16).hex(),
            file_path=file_path,
            content=content,
        )

        self.store.save_snapshot(
            snapshot
        )

        return snapshot

    # =========================================================
    # VERSION HISTORY
    # =========================================================

    def test_get_versions(self):
        """
        All snapshots for a file should be returned
        in creation order.
        """

        first = self._create_snapshot(
            "main.py",
            "print('version 1')"
        )

        second = self._create_snapshot(
            "main.py",
            "print('version 2')"
        )

        versions = self.manager.get_versions(
            "main.py"
        )

        self.assertEqual(
            len(versions),
            2
        )

        self.assertEqual(
            versions[0].snapshot_id,
            first.snapshot_id
        )

        self.assertEqual(
            versions[1].snapshot_id,
            second.snapshot_id
        )

    def test_get_versions_for_unknown_file(self):
        """
        An unknown file should have no version history.
        """

        versions = self.manager.get_versions(
            "does_not_exist.py"
        )

        self.assertEqual(
            versions,
            []
        )

    # =========================================================
    # GET VERSION
    # =========================================================

    def test_get_version(self):
        """
        A snapshot should be retrievable by snapshot ID.
        """

        snapshot = self._create_snapshot(
            "main.py",
            "hello"
        )

        result = self.manager.get_version(
            snapshot.snapshot_id
        )

        self.assertIsNotNone(
            result
        )

        self.assertEqual(
            result.snapshot_id,
            snapshot.snapshot_id
        )

        self.assertEqual(
            result.content,
            "hello"
        )

    def test_get_missing_version(self):
        """
        A missing snapshot should return None.
        """

        result = self.manager.get_version(
            "does-not-exist"
        )

        self.assertIsNone(
            result
        )

    # =========================================================
    # VIEW VERSION
    # =========================================================

    def test_view_version(self):
        """
        view_version() should return historical file content.
        """

        snapshot = self._create_snapshot(
            "main.py",
            "print('hello')"
        )

        content = self.manager.view_version(
            snapshot.snapshot_id
        )

        self.assertEqual(
            content,
            "print('hello')"
        )

    def test_view_missing_version_fails(self):
        """
        Viewing a missing snapshot should raise ValueError.
        """

        with self.assertRaises(ValueError):
            self.manager.view_version(
                "missing-snapshot"
            )

    # =========================================================
    # LATEST VERSION
    # =========================================================

    def test_get_latest_version(self):
        """
        The latest snapshot should be returned.
        """

        first = self._create_snapshot(
            "main.py",
            "first"
        )

        second = self._create_snapshot(
            "main.py",
            "second"
        )

        latest = self.manager.get_latest_version(
            "main.py"
        )

        self.assertIsNotNone(
            latest
        )

        self.assertEqual(
            latest.snapshot_id,
            second.snapshot_id
        )

        self.assertNotEqual(
            latest.snapshot_id,
            first.snapshot_id
        )

    def test_get_latest_version_when_no_history(self):
        """
        Files without history should return None.
        """

        latest = self.manager.get_latest_version(
            "unknown.py"
        )

        self.assertIsNone(
            latest
        )

    # =========================================================
    # VERSION COUNT
    # =========================================================

    def test_version_count(self):
        """
        version_count() should return the number of snapshots.
        """

        self._create_snapshot(
            "main.py",
            "one"
        )

        self._create_snapshot(
            "main.py",
            "two"
        )

        self._create_snapshot(
            "main.py",
            "three"
        )

        self.assertEqual(
            self.manager.version_count(
                "main.py"
            ),
            3
        )

    def test_file_has_history(self):
        """
        file_has_history() should correctly report whether
        snapshots exist.
        """

        self.assertFalse(
            self.manager.file_has_history(
                "main.py"
            )
        )

        self._create_snapshot(
            "main.py",
            "hello"
        )

        self.assertTrue(
            self.manager.file_has_history(
                "main.py"
            )
        )

    # =========================================================
    # RESTORE EXISTING FILE
    # =========================================================

    def test_restore_existing_file(self):
        """
        Restoring a snapshot should replace the current
        contents of an existing file.
        """

        file_path = os.path.join(
            self.workspace_path,
            "main.py"
        )

        with open(
            file_path,
            "w",
            encoding="utf-8"
        ) as file:
            file.write(
                "current version"
            )

        snapshot = self._create_snapshot(
            "main.py",
            "historical version"
        )

        event = self.manager.restore(
            snapshot.snapshot_id
        )

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:
            content = file.read()

        self.assertEqual(
            content,
            "historical version"
        )

        self.assertIsInstance(
            event,
            Event
        )

        self.assertEqual(
            event.type,
            "file.restored"
        )

    def test_restore_merge_with_current_keeps_both_versions(self):
        """
        When merge_with_current=True, the current file should remain and
        historical lines should be appended without erasing the active state.
        """

        file_path = os.path.join(
            self.workspace_path,
            "main.py"
        )

        with open(
            file_path,
            "w",
            encoding="utf-8"
        ) as file:
            file.write(
                "current\nstate\n"
            )

        snapshot = self._create_snapshot(
            "main.py",
            "prev\nline1\nline2\n"
        )

        event = self.manager.restore(
            snapshot.snapshot_id,
            merge_with_current=True,
            previous_line_count=2,
        )

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:
            content = file.read()

        self.assertEqual(
            content,
            "current\nstate\n\nline1\nline2"
        )

        self.assertIsInstance(
            event,
            Event
        )

        self.assertEqual(
            event.type,
            "file.restored"
        )

    # =========================================================
    # RESTORE DELETED FILE
    # =========================================================

    def test_restore_deleted_file(self):
        """
        A deleted file should be recreated from its snapshot.
        """

        file_path = os.path.join(
            self.workspace_path,
            "main.py"
        )

        snapshot = self._create_snapshot(
            "main.py",
            "restored content"
        )

        self.assertFalse(
            os.path.exists(file_path)
        )

        event = self.manager.restore(
            snapshot.snapshot_id
        )

        self.assertTrue(
            os.path.exists(file_path)
        )

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:
            content = file.read()

        self.assertEqual(
            content,
            "restored content"
        )

        self.assertEqual(
            event.type,
            "file.restored"
        )

    # =========================================================
    # RESTORE CREATES DIRECTORIES
    # =========================================================

    def test_restore_creates_missing_directories(self):
        """
        Restoring a file should recreate missing parent
        directories when necessary.
        """

        file_path = os.path.join(
            self.workspace_path,
            "src",
            "utils",
            "main.py"
        )

        snapshot = self._create_snapshot(
            "src/utils/main.py",
            "print('restored')"
        )

        self.assertFalse(
            os.path.exists(file_path)
        )

        self.manager.restore(
            snapshot.snapshot_id
        )

        self.assertTrue(
            os.path.exists(file_path)
        )

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:
            content = file.read()

        self.assertEqual(
            content,
            "print('restored')"
        )

    # =========================================================
    # RESTORE EVENT
    # =========================================================

    def test_restore_generates_event(self):
        """
        A successful restore should generate and persist
        a file.restored event.
        """

        snapshot = self._create_snapshot(
            "main.py",
            "hello"
        )

        before_count = self.store.count()

        event = self.manager.restore(
            snapshot.snapshot_id
        )

        after_count = self.store.count()

        self.assertEqual(
            after_count,
            before_count + 1
        )

        self.assertEqual(
            event.type,
            "file.restored"
        )

        self.assertEqual(
            event.data["file_path"],
            "main.py"
        )

        self.assertEqual(
            event.data["snapshot_id"],
            snapshot.snapshot_id
        )

        self.assertEqual(
            event.data["content_hash"],
            snapshot.content_hash
        )

        stored_event = self.store.get(
            event.id
        )

        self.assertIsNotNone(
            stored_event
        )

        self.assertEqual(
            stored_event.type,
            "file.restored"
        )

    # =========================================================
    # RESTORE BY VERSION NUMBER
    # =========================================================

    def test_restore_version(self):
        """
        restore_version() should restore the selected
        one-based version.
        """

        file_path = os.path.join(
            self.workspace_path,
            "main.py"
        )

        self._create_snapshot(
            "main.py",
            "version 1"
        )

        self._create_snapshot(
            "main.py",
            "version 2"
        )

        self._create_snapshot(
            "main.py",
            "version 3"
        )

        event = self.manager.restore_version(
            "main.py",
            2
        )

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:
            content = file.read()

        self.assertEqual(
            content,
            "version 2"
        )

        self.assertEqual(
            event.type,
            "file.restored"
        )

    def test_restore_first_version(self):
        """
        Version 1 should restore the first snapshot.
        """

        file_path = os.path.join(
            self.workspace_path,
            "main.py"
        )

        self._create_snapshot(
            "main.py",
            "first"
        )

        self._create_snapshot(
            "main.py",
            "second"
        )

        self.manager.restore_version(
            "main.py",
            1
        )

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:
            content = file.read()

        self.assertEqual(
            content,
            "first"
        )

    # =========================================================
    # INVALID VERSION
    # =========================================================

    def test_restore_invalid_version_zero(self):
        """
        Version zero should fail because versions are
        one-based.
        """

        self._create_snapshot(
            "main.py",
            "hello"
        )

        with self.assertRaises(ValueError):
            self.manager.restore_version(
                "main.py",
                0
            )

    def test_restore_invalid_version_negative(self):
        """
        Negative versions should fail.
        """

        self._create_snapshot(
            "main.py",
            "hello"
        )

        with self.assertRaises(ValueError):
            self.manager.restore_version(
                "main.py",
                -1
            )

    def test_restore_version_out_of_range(self):
        """
        A version that does not exist should fail.
        """

        self._create_snapshot(
            "main.py",
            "hello"
        )

        with self.assertRaises(ValueError):
            self.manager.restore_version(
                "main.py",
                99
            )

    def test_restore_version_invalid_type(self):
        """
        Version numbers must be integers.
        """

        with self.assertRaises(ValueError):
            self.manager.restore_version(
                "main.py",
                "1"
            )

    # =========================================================
    # MISSING SNAPSHOT
    # =========================================================

    def test_restore_missing_snapshot(self):
        """
        Restoring a missing snapshot should fail.
        """

        with self.assertRaises(ValueError):
            self.manager.restore(
                "missing-snapshot"
            )

    # =========================================================
    # PATH SECURITY
    # =========================================================

    def test_path_escape_is_rejected(self):
        """
        Restoration must never write outside the workspace.
        """

        snapshot = self._create_snapshot(
            "../outside.py",
            "danger"
        )

        with self.assertRaises(ValueError):
            self.manager.restore(
                snapshot.snapshot_id
            )

    def test_absolute_path_escape_is_rejected(self):
        """
        Absolute paths outside the workspace should be rejected.
        """

        snapshot = self._create_snapshot(
            os.path.abspath(
                os.path.join(
                    self.temp_directory.name,
                    "outside.py"
                )
            ),
            "danger"
        )

        with self.assertRaises(ValueError):
            self.manager.restore(
                snapshot.snapshot_id
            )

    # =========================================================
    # INTEGRITY
    # =========================================================

    def test_corrupted_snapshot_is_not_restored(self):
        """
        A corrupted snapshot stored in the database must not
        be restored.
        """
        snapshot = Snapshot.create(
             snapshot_id=os.urandom(16).hex(),
             file_path="main.py",
             content="original content",
             )
        # Store the snapshot first.
        self.store.save_snapshot(snapshot)
        # Simulate database corruption by directly changing
        #  the stored content without changing its original hash.
        connection = self.store._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE snapshots
                SET content = ?
                WHERE snapshot_id = ?
                """,
                (
                    "tampered content",
                    snapshot.snapshot_id,
                    ),
             )
            connection.commit()
        finally:
            connection.close()
        # The RestoreManager retrieves the corrupted snapshot
        #  from SQLite and should detect the hash mismatch.
        with self.assertRaises(ValueError):
            self.manager.restore(
                snapshot.snapshot_id
                )

        file_path = os.path.join(
        self.workspace_path,
        "main.py"
        )
        # The corrupted snapshot must never be written.
        self.assertFalse(
        os.path.exists(file_path)
        )

if __name__ == "__main__":
    unittest.main()