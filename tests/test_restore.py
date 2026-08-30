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

    # =========================================================
    # SELECTIVE & KEEP-BOTH TESTS
    # =========================================================

    def test_restore_selected_lines(self):
        """
        Extract specific lines from previous snapshot and append/prepend to current file.
        """
        # Create initial file on disk
        target_path = os.path.join(self.workspace_path, "code.py")
        with open(target_path, "w", encoding="utf-8") as f:
            f.write("def current_func():\n    pass\n")

        # Snapshot with older lines
        snap = self._create_snapshot(
            "code.py",
            "# Line 1: header\n# Line 2: helper\ndef old_helper():\n    return 42\n"
        )

        # Restore lines 3 and 4 (the helper function)
        evt = self.manager.restore_selected_lines(
            snap.snapshot_id,
            line_numbers=[3, 4],
            placement="append"
        )
        self.assertEqual(evt.type, "file.restored")

        with open(target_path, "r", encoding="utf-8") as f:
            restored_content = f.read()

        self.assertIn("def current_func():", restored_content)
        self.assertIn("def old_helper():\n    return 42", restored_content)

    def test_restore_keep_both_combined(self):
        """
        Merge current state and historical snapshot in one file.
        """
        target_path = os.path.join(self.workspace_path, "notes.txt")
        with open(target_path, "w", encoding="utf-8") as f:
            f.write("Current notes: line A\nline B\n")

        snap = self._create_snapshot("notes.txt", "Old notes: line X\nline Y\n")

        evt = self.manager.restore_keep_both(snap.snapshot_id, mode="combine_sections")
        self.assertEqual(evt.type, "file.restored")

        with open(target_path, "r", encoding="utf-8") as f:
            merged = f.read()

        self.assertIn("CURRENT WORKING STATE", merged)
        self.assertIn("Current notes: line A", merged)
        self.assertIn("RESTORED HISTORICAL VERSION", merged)
        self.assertIn("Old notes: line X", merged)

    def test_restore_keep_both_new_file(self):
        """
        Save historical version as a separate file without modifying current file.
        """
        target_path = os.path.join(self.workspace_path, "doc.txt")
        with open(target_path, "w", encoding="utf-8") as f:
            f.write("Current document\n")

        snap = self._create_snapshot("doc.txt", "Historical document\n")

        evt = self.manager.restore_keep_both(
            snap.snapshot_id,
            mode="new_file",
            new_file_path="doc_backup.txt"
        )
        self.assertEqual(evt.type, "file.created")

        # Original file unchanged
        with open(target_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "Current document\n")

        # New file created
        backup_path = os.path.join(self.workspace_path, "doc_backup.txt")
        self.assertTrue(os.path.isfile(backup_path))
        with open(backup_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "Historical document\n")

    def test_restore_state_snapshot_append_only(self):
        """
        Restoring application state appends an immutable state.restored event.
        """
        # Save sample business events
        e1 = Event.create("user.created", {"user_id": "USR-001", "name": "Alice", "email": "alice@example.com", "age": 25})
        e2 = Event.create("balance.added", {"user_id": "USR-001", "amount": 500.0})
        self.store.save(e1)
        self.store.save(e2)

        # Restore state back to step 1
        restore_evt = self.manager.restore_state_snapshot(1, reason="Rollback balance")
        self.assertEqual(restore_evt.type, "state.restored")
        self.assertEqual(restore_evt.data["source_event_number"], 1)

        # Confirm all 3 events exist in store
        events = self.store.get_all()
        self.assertEqual(len(events), 3)
        self.assertEqual(events[2].type, "state.restored")


if __name__ == "__main__":
    unittest.main()
