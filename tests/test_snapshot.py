import unittest

from src.snapshot import Snapshot


class TestSnapshot(unittest.TestCase):

    def test_create_snapshot(self):

        snapshot = Snapshot.create(
            "snap-001",
            "main.py",
            'print("Hello")'
        )

        self.assertEqual(
            snapshot.snapshot_id,
            "snap-001"
        )

        self.assertEqual(
            snapshot.file_path,
            "main.py"
        )

        self.assertEqual(
            snapshot.content,
            'print("Hello")'
        )

        self.assertTrue(
            snapshot.content_hash
        )

    def test_integrity_check(self):

        snapshot = Snapshot.create(
            "snap-001",
            "main.py",
            'print("Hello")'
        )

        self.assertTrue(
            snapshot.verify_integrity()
        )

    def test_modified_content_fails_integrity(self):

        snapshot = Snapshot.create(
            "snap-001",
            "main.py",
            'print("Hello")'
        )

        snapshot.content = 'print("Changed")'

        self.assertFalse(
            snapshot.verify_integrity()
        )

    def test_empty_snapshot_id(self):

        with self.assertRaises(ValueError):

            Snapshot.create(
                "",
                "main.py",
                "hello"
            )

    def test_invalid_content(self):

        with self.assertRaises(ValueError):

            Snapshot.create(
                "snap-001",
                "main.py",
                123
            )


if __name__ == "__main__":
    unittest.main()