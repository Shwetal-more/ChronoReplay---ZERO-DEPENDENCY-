#!/usr/bin/env python3
"""
ChronoReplay Deterministic Single-File Builder & Verification Script.

This build script compiles all modular source components:
- Event & Model (`src/event.py`)
- Validator (`src/validator.py`)
- SQLite Event Store (`src/store.py`)
- Snapshot Model & Store (`src/snapshot.py`, `src/tracker.py`)
- Deterministic State Engine (`src/state.py`)
- Replay Engine (`src/replay.py`)
- Version History & Diffs (`src/history.py`)
- File Restorer (`src/restore.py`)
- Workspace Manager & Watcher (`src/workspace.py`, `src/watcher.py`)
- Event Simulator (`src/simulator.py`)
- PubSub Relay (`src/relay.py`)
- Facade Engine (`src/chrono.py`)
- Complete Tkinter GUI (`src/ui.py`)

into a single standalone, self-contained Python file:
`artifacts/chronoreplay-single.py`

Guaranteed Reproducibility:
- Deterministic ordering of sections
- Zero external dependencies
- Identical SHA-256 output across multiple builds
"""

import hashlib
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
OUTPUT_FILE = os.path.join(BASE_DIR, "artifacts", "chronoreplay-single.py")


def read_module(filename: str) -> str:
    path = os.path.join(SRC_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Strip local module imports and top-level stdlib re-imports
    lines = []
    skip_main_block = False
    for line in content.splitlines():
        if 'if __name__ == "__main__":' in line:
            skip_main_block = True
            continue
        if skip_main_block:
            if line.startswith("    ") or line.strip() == "":
                continue
            else:
                skip_main_block = False

        if re.match(r"^\s*from\s+(src\.|event|validator|store|snapshot|tracker|state|replay|history|restore|workspace|watcher|simulator|relay|chrono|ui)\b", line):
            continue
        if re.match(r"^\s*import\s+(src\.|event|validator|store|snapshot|tracker|state|replay|history|restore|workspace|watcher|simulator|relay|chrono|ui)\b", line):
            continue
        if re.match(r"^\s*(import\s+tkinter|from\s+tkinter\b)", line):
            continue
        lines.append(line)

    mod_text = "\n".join(lines)

    # For store.py, ensure persistent in-memory database connection handling is bulletproof
    if filename == "store.py":
        # Ensure _NoCloseConn class is present and _connect handles :memory:
        mem_fix = """
class _NoCloseConn:
    def __init__(self, conn):
        self._conn = conn
    def close(self):
        pass
    def __getattr__(self, name):
        return getattr(self._conn, name)

"""
        if "class _NoCloseConn:" not in mod_text:
            mod_text = mem_fix + mod_text

        # Patch _connect to keep :memory: connections alive across calls
        if "def _connect(self):" in mod_text:
            connect_patch = """    def _connect(self):
        if self.database_path == ":memory:":
            if not hasattr(self, "_mem_conn_cache") or self._mem_conn_cache is None:
                self._mem_conn_cache = _NoCloseConn(sqlite3.connect(":memory:"))
            return self._mem_conn_cache
        return sqlite3.connect(self.database_path)"""
            mod_text = re.sub(
                r"    def _connect\(self\):.*?(?=\n    def |\n    # =|\n\s*class |\Z)",
                connect_patch,
                mod_text,
                flags=re.DOTALL
            )

    # For chrono.py, ensure get_current_state method is present on ChronoReplay class
    if filename == "chrono.py":
        if "def get_current_state" not in mod_text:
            mod_text += """

    def get_current_state(self) -> dict:
        \"\"\"Return the fully reduced current state from all stored events.\"\"\"
        replayer = ReplayEngine(self.store)
        return replayer.replay_all()
"""

    return mod_text


def build_single_file() -> str:
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    header = '''#!/usr/bin/env python3
"""
=============================================================================
ChronoReplay — ZERO-DEPENDENCY COMPLETE SINGLE-FILE APPLICATION
=============================================================================
Zero-Dependency Event-Sourced Audit, State Time-Machine & Workspace Recovery Engine.

This single file contains the entire ChronoReplay application:
- Immutable Event Definitions & Validation Engine
- Append-Only SQLite Event Store & SHA-256 Checksums
- Deterministic State Engine & Invariant Diagnostics
- Bidirectional Time Machine Replay & Append-Only Restoration
- Workspace File Snapshotting, difflib Unified Line Diffs & Rollback
- Event Simulator with Automatic User/Order Context Resolution
- Native Dark-Themed Tkinter GUI Dashboard

Standard Library Only (Zero Third-Party Dependencies):
dataclasses, sqlite3, hashlib, difflib, json, uuid, datetime, copy, os, pathlib, time, typing, tkinter

Usage:
    python3 chronoreplay-single.py
    python3 chronoreplay-single.py --cli
=============================================================================
"""

# Global Standard Library Imports
import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:
    tk = None
    filedialog = None
    messagebox = None
    ttk = None
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import uuid

'''

    modules = [
        "event.py",
        "validator.py",
        "snapshot.py",
        "tracker.py",
        "store.py",
        "state.py",
        "replay.py",
        "history.py",
        "restore.py",
        "watcher.py",
        "workspace.py",
        "simulator.py",
        "relay.py",
        "chrono.py",
        "ui.py",
    ]

    parts = [header]
    for mod in modules:
        parts.append(f"\n# {'=' * 75}\n# MODULE: {mod}\n# {'=' * 75}\n")
        parts.append(read_module(mod))

    entry_point = '''

# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

def start_application():
    if "--test" in sys.argv or "--cli" in sys.argv:
        print("=" * 70)
        print("🚀 ChronoReplay Single-File Standalone CLI Self-Test")
        print("=" * 70)
        engine = ChronoReplay(":memory:")
        e1 = engine.publish_event("user.created", {"user_id": "USR-0001", "name": "Rahul Verma", "email": "rahul@example.com", "age": 28})
        e2 = engine.publish_event("balance.added", {"user_id": "USR-0001", "amount": 500.0})
        e3 = engine.publish_event("order.created", {"order_id": "ORD-0001", "user_id": "USR-0001", "amount": 200.0})
        e4 = engine.publish_event("payment.completed", {"order_id": "ORD-0001", "user_id": "USR-0001", "amount": 200.0, "method": "UPI"})
        st = engine.get_current_state()
        assert st["users"]["USR-0001"]["balance"] == 300.0
        assert st["orders"]["ORD-0001"]["status"].lower() == "paid"
        rew = engine.rewind(2)
        assert rew["users"]["USR-0001"]["balance"] == 500.0
        engine.restore_state(2, reason="Audit recovery")
        assert engine.store.count() == 5
        print("✅ Standalone single-file engine & state time-machine verified with 100% success!")
        print("=" * 70)
        return

    try:
        import tkinter as tk
        root = tk.Tk()
        ChronoReplayUI(root)
        root.mainloop()
    except Exception as e:
        print(f"GUI notice: {e}")
        print("To run in headless verification mode: python3 chronoreplay-single.py --cli")


if __name__ == "__main__":
    start_application()
'''
    parts.append(entry_point)

    full_code = "\n".join(parts)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(full_code)

    hasher = hashlib.sha256()
    with open(OUTPUT_FILE, "rb") as f:
        hasher.update(f.read())
    file_hash = hasher.hexdigest()

    return file_hash


if __name__ == "__main__":
    h1 = build_single_file()
    print(f"✅ Build 1 completed. SHA-256: {h1}")
    h2 = build_single_file()
    print(f"✅ Build 2 completed. SHA-256: {h2}")
    if h1 == h2:
        print("🎯 REPRODUCIBILITY VERIFICATION: PASS (Byte-identical output)")
    else:
        print("❌ REPRODUCIBILITY VERIFICATION: FAILED")
        sys.exit(1)
