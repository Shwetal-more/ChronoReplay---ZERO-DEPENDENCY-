import os
import tempfile
import unittest

from src.workspace import WorkspaceManager
from src.event import Event
from src.validator import EventValidator


class TestWorkspaceEvents(unittest.TestCase):

    def setUp(self):

        self.workspace = tempfile.mkdtemp()

        self.manager = WorkspaceManager(
            self.workspace
        )

    def tearDown(self):

        import shutil

        shutil.rmtree(
            self.workspace,
            ignore_errors=True
        )

    def test_create_file_event(self):

        snapshot = self.manager.create_file(
            "main.py",
            'print("Hello")'
        )

        event = self.manager.create_file_event(
            snapshot
        )

        self.assertEqual(
            event.type,
            "file.created"
        )

        self.assertEqual(
            event.data["file_path"],
            "main.py"
        )

        self.assertEqual(
            event.data["snapshot_id"],
            snapshot.snapshot_id
        )

        EventValidator.validate(event)

    def test_modify_file_event(self):

        self.manager.create_file(
            "main.py",
            'print("Hello")'
        )

        snapshot = self.manager.modify_file(
            "main.py",
            'print("Hello World")'
        )

        event = self.manager.modify_file_event(
            snapshot
        )

        self.assertEqual(
            event.type,
            "file.modified"
        )

        self.assertEqual(
            event.data["file_path"],
            "main.py"
        )

        EventValidator.validate(event)

    def test_delete_file_event(self):

        self.manager.create_file(
            "main.py",
            'print("Hello")'
        )

        event = self.manager.delete_file_event(
            "main.py"
        )

        self.assertEqual(
            event.type,
            "file.deleted"
        )

        self.assertEqual(
            event.data["file_path"],
            "main.py"
        )

        EventValidator.validate(event)

    def test_restore_file_event(self):

        snapshot = self.manager.create_file(
            "main.py",
            'print("Hello")'
        )

        event = self.manager.restore_file_event(
            snapshot
        )

        self.assertEqual(
            event.type,
            "file.restored"
        )

        self.assertEqual(
            event.data["file_path"],
            "main.py"
        )

        EventValidator.validate(event)


if __name__ == "__main__":
    unittest.main()