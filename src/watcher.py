"""
ChronoReplay file watcher.

Detects file creation, modification and deletion
using Python standard-library functionality.

No third-party dependencies are used.
"""

import os
import time


class FileWatcher:
    """
    Watches a directory for file changes.

    The watcher takes periodic snapshots of the directory
    and compares them with the previous scan.
    """

    def __init__(self, workspace_path, interval=1.0):
        """
        Create a file watcher.

        workspace_path:
            Directory to monitor.

        interval:
            Time between scans in seconds.
        """

        self.workspace_path = os.path.abspath(
            workspace_path
        )

        self.interval = interval

        self.previous_state = {}

    def scan(self):
        """
        Scan the workspace and return the current
        state of tracked files.

        Returns:

        {
            "relative/path.py": {
                "size": 123,
                "mtime": 123456789
            }
        }
        """

        current_state = {}

        for root, directories, files in os.walk(
            self.workspace_path
        ):

            # Ignore hidden directories.
            directories[:] = [
                directory
                for directory in directories
                if not directory.startswith(".")
            ]

            for filename in files:

                # Ignore hidden files.
                if filename.startswith("."):
                    continue

                full_path = os.path.join(
                    root,
                    filename
                )

                relative_path = os.path.relpath(
                    full_path,
                    self.workspace_path
                )

                try:

                    stat = os.stat(
                        full_path
                    )

                except OSError:

                    continue

                current_state[relative_path] = {
                    "size": stat.st_size,
                    "mtime": stat.st_mtime_ns,
                }

        return current_state

    def initialize(self):
        """
        Record the initial state of the workspace.

        The first scan does not generate events.
        """

        self.previous_state = self.scan()

        return self.previous_state

    def detect_changes(self):
        """
        Compare the current workspace state with
        the previous state.

        Returns:

        {
            "created": [...],
            "modified": [...],
            "deleted": [...]
        }
        """

        current_state = self.scan()

        previous_files = set(
            self.previous_state
        )

        current_files = set(
            current_state
        )

        created = sorted(
            current_files - previous_files
        )

        deleted = sorted(
            previous_files - current_files
        )

        modified = sorted(
            path
            for path in (
                current_files & previous_files
            )
            if (
                current_state[path]["size"]
                != self.previous_state[path]["size"]
                or
                current_state[path]["mtime"]
                != self.previous_state[path]["mtime"]
            )
        )

        self.previous_state = current_state

        return {
            "created": created,
            "modified": modified,
            "deleted": deleted,
        }

    def watch(self):
        """
        Continuously watch the workspace.

        Yields a dictionary whenever a change
        is detected.
        """

        self.initialize()

        while True:

            changes = self.detect_changes()

            if (
                changes["created"]
                or changes["modified"]
                or changes["deleted"]
            ):
                yield changes

            time.sleep(
                self.interval
            )