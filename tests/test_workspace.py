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


    def test_multi_workspace_isolation(self):
        from src.store import EventStore
        import tempfile
        import shutil

        store_dir = tempfile.mkdtemp()
        db_path = os.path.join(store_dir, "test_iso.db")
        store = EventStore(db_path)

        ws1_dir = tempfile.mkdtemp()
        ws2_dir = tempfile.mkdtemp()

        try:
            # Workspace 1 has file_a.txt and file_b.txt
            with open(os.path.join(ws1_dir, "file_a.txt"), "w") as f:
                f.write("Hello A")
            with open(os.path.join(ws1_dir, "file_b.txt"), "w") as f:
                f.write("Hello B")

            # Workspace 2 has only file_x.txt
            with open(os.path.join(ws2_dir, "file_x.txt"), "w") as f:
                f.write("Hello X")

            mgr1 = WorkspaceManager(ws1_dir, store)
            mgr2 = WorkspaceManager(ws2_dir, store)

            # Scan WS1
            sum1 = mgr1.scan_and_record_changes()
            self.assertEqual(sum1["created"], 2)

            # Scan WS2
            sum2 = mgr2.scan_and_record_changes()
            self.assertEqual(sum2["created"], 1)
            self.assertEqual(sum2["deleted"], 0)

            # Check status in WS2: must only contain file_x.txt, not file_a.txt or file_b.txt
            ws2_files = mgr2.get_workspace_files_with_status()
            file_names = [f["file_path"] for f in ws2_files]
            self.assertEqual(file_names, ["file_x.txt"])

            # Check status in WS1: must only contain file_a.txt and file_b.txt
            ws1_files = mgr1.get_workspace_files_with_status()
            file_names1 = [f["file_path"] for f in ws1_files]
            self.assertEqual(file_names1, ["file_a.txt", "file_b.txt"])

        finally:
            shutil.rmtree(store_dir, ignore_errors=True)
            shutil.rmtree(ws1_dir, ignore_errors=True)
            shutil.rmtree(ws2_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()