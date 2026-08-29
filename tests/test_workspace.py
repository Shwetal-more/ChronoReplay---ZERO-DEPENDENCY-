import os
import tempfile
import unittest

from src.workspace import WorkspaceManager


class TestWorkspaceManager(unittest.TestCase):

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

    def test_create_file(self):

        snapshot = self.manager.create_file(
            "main.py",
            'print("Hello")'
        )

        self.assertTrue(
            os.path.exists(
                os.path.join(
                    self.workspace,
                    "main.py"
                )
            )
        )

        self.assertEqual(
            snapshot.content,
            'print("Hello")'
        )

    def test_read_file(self):

        self.manager.create_file(
            "main.py",
            'print("Hello")'
        )

        content = self.manager.read_file(
            "main.py"
        )

        self.assertEqual(
            content,
            'print("Hello")'
        )

    def test_modify_file(self):

        self.manager.create_file(
            "main.py",
            'print("Hello")'
        )

        snapshot = self.manager.modify_file(
            "main.py",
            'print("Hello World")'
        )

        self.assertEqual(
            snapshot.content,
            'print("Hello World")'
        )

        self.assertEqual(
            self.manager.read_file("main.py"),
            'print("Hello World")'
        )

    def test_delete_file(self):

        self.manager.create_file(
            "main.py",
            'print("Hello")'
        )

        self.manager.delete_file(
            "main.py"
        )

        with self.assertRaises(
            FileNotFoundError
        ):
            self.manager.read_file(
                "main.py"
            )

    def test_restore_snapshot(self):

        snapshot = self.manager.create_file(
            "main.py",
            'print("Version 1")'
        )

        self.manager.modify_file(
            "main.py",
            'print("Version 2")'
        )

        self.manager.restore_snapshot(
            snapshot
        )

        content = self.manager.read_file(
            "main.py"
        )

        self.assertEqual(
            content,
            'print("Version 1")'
        )

    def test_cannot_escape_workspace(self):

        with self.assertRaises(ValueError):

            self.manager.create_file(
                "../outside.py",
                "bad"
            )


if __name__ == "__main__":
    unittest.main()