import os
import tempfile
import unittest
import shutil

from src.store import EventStore
from src.tracker import WorkspaceTracker


class TestWorkspaceTracker(unittest.TestCase):

    def setUp(self):

        self.workspace = tempfile.mkdtemp()

        self.database = os.path.join(
            self.workspace,
            "events.db"
        )

        self.store = EventStore(
            self.database
        )

        self.tracker = WorkspaceTracker(
            self.workspace,
            self.store
        )

        self.tracker.initialize()

    def tearDown(self):

        shutil.rmtree(
            self.workspace,
            ignore_errors=True
        )

    def test_created_file_generates_event(self):

        path = os.path.join(
            self.workspace,
            "main.py"
        )

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                'print("Hello")'
            )

        events = self.tracker.process_changes()

        self.assertEqual(
            len(events),
            1
        )

        self.assertEqual(
            events[0].type,
            "file.created"
        )

        self.assertEqual(
            events[0].data["file_path"],
            "main.py"
        )

    def test_modified_file_generates_event(self):

        path = os.path.join(
            self.workspace,
            "main.py"
        )

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                'print("Hello")'
            )

        self.tracker.process_changes()

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                'print("Hello World")'
            )

        events = self.tracker.process_changes()

        self.assertEqual(
            len(events),
            1
        )

        self.assertEqual(
            events[0].type,
            "file.modified"
        )

    def test_deleted_file_generates_event(self):

        path = os.path.join(
            self.workspace,
            "main.py"
        )

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                'print("Hello")'
            )

        self.tracker.process_changes()

        os.remove(path)

        events = self.tracker.process_changes()

        self.assertEqual(
            len(events),
            1
        )

        self.assertEqual(
            events[0].type,
            "file.deleted"
        )

    def test_event_is_stored(self):

        path = os.path.join(
            self.workspace,
            "main.py"
        )

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                'print("Hello")'
            )

        self.tracker.process_changes()

        stored_events = self.store.get_all_events()

        self.assertEqual(
            len(stored_events),
            1
        )

        self.assertEqual(
            stored_events[0].type,
            "file.created"
        )


if __name__ == "__main__":
    unittest.main()