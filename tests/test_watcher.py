import os
import tempfile
import unittest

from src.watcher import FileWatcher


class TestFileWatcher(unittest.TestCase):

    def setUp(self):

        self.workspace = tempfile.mkdtemp()

        self.watcher = FileWatcher(
            self.workspace
        )

    def tearDown(self):

        import shutil

        shutil.rmtree(
            self.workspace,
            ignore_errors=True
        )

    def test_initial_scan(self):

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

        state = self.watcher.initialize()

        self.assertIn(
            "main.py",
            state
        )

    def test_detect_created_file(self):

        self.watcher.initialize()

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

        changes = self.watcher.detect_changes()

        self.assertIn(
            "main.py",
            changes["created"]
        )

    def test_detect_modified_file(self):

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

        self.watcher.initialize()

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                'print("Hello World")'
            )

        changes = self.watcher.detect_changes()

        self.assertIn(
            "main.py",
            changes["modified"]
        )

    def test_detect_deleted_file(self):

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

        self.watcher.initialize()

        os.remove(path)

        changes = self.watcher.detect_changes()

        self.assertIn(
            "main.py",
            changes["deleted"]
        )


if __name__ == "__main__":
    unittest.main()