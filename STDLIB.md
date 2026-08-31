# ChronoReplay — Zero-Dependency Standard Library Substitutions

ChronoReplay is built from the ground up using **only Python's standard library**.

**Total External Third-Party Dependencies:** `0`

ChronoReplay replaces common third-party capabilities with focused Python standard-library implementations. The substitutions below correspond directly to functionality implemented and used in the codebase.

---

## 📋 Standard Library Substitution Summary Table

| # | Target Capability / Third-Party Package | Python Standard Library Replacement | ChronoReplay Modules |
|---|------------------------------------------|-------------------------------------|----------------------|
| 1 | `Pydantic` / `Attrs` | `dataclasses` (`@dataclass`, `asdict`) | `src/event.py`, `src/snapshot.py`, `src/history.py` |
| 2 | `SQLAlchemy` / `Peewee` / `SQLite ORM` | `sqlite3` | `src/store.py` |
| 3 | `watchdog` / `inotify` (filesystem polling) | `os` (`os.walk`, `os.stat`) + `time` | `src/watcher.py`, `src/tracker.py` |
| 4 | `orjson` / `ujson` | `json` (`json.dumps`, `json.loads`) | `src/event.py`, `src/store.py` |
| 5 | `GitPython` / `diff-match-patch` (diff functionality) | `difflib` (`unified_diff`) | `src/history.py`, `src/ui.py` |
| 6 | `PyCryptodome` / `cryptography` (hashing use cases) | `hashlib` (`hashlib.sha256`) | `src/snapshot.py`, `src/workspace.py`, `build.py` |
| 7 | `shortuuid` / `uuidtools` (unique ID generation) | `uuid` (`uuid.uuid4`) | `src/event.py`, `src/tracker.py`, `src/workspace.py` |
| 8 | `Arrow` / `Pendulum` / `python-dateutil` | `datetime` (`datetime`, `timezone.utc`) | `src/event.py`, `src/snapshot.py`, `src/ui.py` |
| 9 | `PyQt5` / `PySide6` / `CustomTkinter` | `tkinter` + `ttk` | `src/ui.py` |
| 10 | `pyrsistent` / immutable data structures | `copy` (`deepcopy`) + built-in `dict`/`list` | `src/state.py`, `src/replay.py` |
| 11 | `path.py` / `pathlib2` | `pathlib` (`Path`) + `os.path` | `src/workspace.py`, `src/restore.py`, `src/tracker.py` |
| 12 | `PyPubSub` / `blinker` | Observer Relay (`Callable` dispatch) | `src/relay.py`, `src/chrono.py` |
| 13 | `pytest` | `unittest` (`unittest.TestCase`) | `tests/test_*.py` |

---

## 🔍 Detailed Package Substitutions & Architectural Rationale

### 1. Pydantic / Attrs → `dataclasses`
- **Replaced Capability:** Data modeling, validation hooks, serialization helpers
- **Standard Library Replacement:** `dataclasses` (`@dataclass`, `asdict`, `__post_init__`)
- **Reason:** Typed immutable event models (`Event`), file snapshot data structures (`Snapshot`), and historical version records (`FileVersion`) are modeled with strict structural integrity, type hints, and serialization helpers without requiring third-party runtime validation or bytecode generation dependencies.

### 2. SQLAlchemy / Peewee / SQLite ORM → `sqlite3`
- **Replaced Capability:** Relational storage and table queries
- **Standard Library Replacement:** `sqlite3`
- **Reason:** Append-only event persistence, file snapshot storage, row-level queries, and transaction management are implemented directly over Python's built-in SQLite engine. Standard SQL schema definitions and parameterized queries avoid heavy ORM abstraction layers.

### 3. watchdog / inotify → `os` + `pathlib` + `time`
- **Replaced Capability:** Filesystem change monitoring
- **Standard Library Replacement:** `os` (`os.walk`, `os.stat`) + `pathlib` + `time`
- **Reason:** Workspace file changes (creations, edits, and deletions) are detected using periodic differential scanning comparing `mtime_ns` and file size. This eliminates platform-specific C extension dependencies and OS-level file descriptor monitors.

### 4. orjson / ujson → `json`
- **Replaced Capability:** Fast & deterministic JSON serialization
- **Standard Library Replacement:** `json` (`json.dumps`, `json.loads`)
- **Reason:** Event payloads and metadata require deterministic JSON serialization (`sort_keys=True`, compact separators) to guarantee identical event checksums across different OS platforms. Python's built-in `json` module provides standard-compliant, reproducible serialization.

### 5. GitPython / diff-match-patch (diff functionality) → `difflib`
- **Replaced Capability:** Text comparison and unified diff generation
- **Standard Library Replacement:** `difflib` (`unified_diff`, `SequenceMatcher`)
- **Reason:** Historical version comparison, line-by-line inspection, and file rollback previews are computed natively using standard unified line diffing algorithms without external Git binary wrappers or external diff packages.

### 6. PyCryptodome / cryptography (hashing use cases) → `hashlib`
- **Replaced Capability:** Cryptographic hash digest computation (SHA-256)
- **Standard Library Replacement:** `hashlib` (`hashlib.sha256`)
- **Reason:** SHA-256 hashing is implemented with Python's built-in `hashlib`. ChronoReplay uses this for tamper-evident event checksums, snapshot verification, and deterministic build artifact hashing. No encryption or signature functionality is claimed.

### 7. shortuuid / uuidtools (unique ID generation) → `uuid`
- **Replaced Capability:** Unique identifier generation
- **Standard Library Replacement:** `uuid` (`uuid.uuid4`)
- **Reason:** `uuid.uuid4()` provides unique identifiers for events and workspace snapshot records without requiring a third-party ID-generation package.

### 8. Arrow / Pendulum / python-dateutil → `datetime`
- **Replaced Capability:** Timezone-aware date parsing and ISO-8601 formatting
- **Standard Library Replacement:** `datetime` (`datetime`, `timezone.utc`, `fromisoformat`)
- **Reason:** Chronological event ordering, ISO-8601 UTC timestamp generation, and local timeline rendering are supported natively using the built-in `datetime` module with timezone awareness.

### 9. PyQt5 / PySide6 / CustomTkinter → `tkinter` + `ttk`
- **Replaced Capability:** Desktop graphical user interface
- **Standard Library Replacement:** `tkinter` + `ttk` (`ttk.Style`, `ttk.Combobox`, `ttk.Scrollbar`)
- **Reason:** The rich desktop GUI dashboard—featuring dynamic event generation, step-by-step Time Machine playback, invariant diagnostics, and file diff recovery—runs natively across Windows, macOS, and Linux without hundreds of megabytes of external GUI wheels, webview runtimes, or C++ binaries.

### 10. pyrsistent / immutable data structures → `copy.deepcopy` + built-in `dict`/`list`
- **Replaced Capability:** Functional immutable state management
- **Standard Library Replacement:** `copy` (`deepcopy`) + standard Python dictionaries and lists
- **Reason:** Deterministic state machine transitions and point-in-time isolation during Time Machine scrubbing are achieved by applying pure reducer functions to isolated, deep-copied state dictionaries, ensuring zero state mutation leaks without external immutable data structure libraries.

### 11. path.py / pathlib2 → `pathlib` + `os.path`
- **Replaced Capability:** File path manipulation and security sandboxing
- **Standard Library Replacement:** `pathlib` (`Path`) + `os.path` (`commonpath`, `abspath`)
- **Reason:** Sandboxing file recovery operations inside designated workspace folders and defending against directory traversal attacks (`../../`) is achieved using standard `os.path.commonpath` and `pathlib.Path.relative_to`.

### 12. PyPubSub / blinker → Pure Python Observer Relay
- **Replaced Capability:** In-memory event publish/subscribe notification
- **Standard Library Replacement:** Standard Python `Callable` lists and method dispatch in `src/relay.py`
- **Reason:** Live decoupled event notification from the core ChronoReplay engine to UI subscribers is cleanly handled by an in-memory PubSub relay class without third-party reactive streaming frameworks.

### 13. pytest → `unittest`
- **Replaced Capability:** Test runner and assertion framework
- **Standard Library Replacement:** `unittest` (`unittest.TestCase`, `unittest.TestSuite`)
- **Reason:** The comprehensive unit test suite covering event schema validation, store persistence, state machine invariants, replay time-travel, and workspace rollback executes via standard `python -m unittest discover -s tests` with zero dev dependencies.

---

## 🎯 Verification

To verify that ChronoReplay contains zero external runtime dependencies:

```bash
# 1. Run the test suite using built-in unittest
python -m unittest discover -s tests

# 2. Build the deterministic single-file artifact
python build.py

# 3. Execute the standalone artifact self-test
python artifacts/chronoreplay-single.py --cli
```

The standalone artifact is generated from the project's source modules and contains the complete ChronoReplay engine and GUI in one Python file.



