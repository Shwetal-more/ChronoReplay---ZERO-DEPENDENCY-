# ChronoReplay — Zero-Dependency Event Sourcing & Time Machine Engine

ChronoReplay is a zero-dependency, event-sourced audit and state time-machine engine built entirely with Python standard libraries. It records immutable business and workspace events, deterministically reconstructs past application states, supports bidirectional time travel, enables append-only state restoration, and provides file-level snapshot recovery.

---

## 🏆 Hackathon Compliance & Track Info

- **Track Selection:** **Track F (Open / Developer Tools & Infrastructure)**
  - *Rationale:* ChronoReplay provides developer-grade infrastructure for audit trails, immutable ledger management, state debugging, and non-destructive state time-travel without relying on external databases, frameworks, or cloud SDKs.
- **Third-Party Runtime Dependencies:** **0** (Standard Library only)
- **License:** MIT License (OSI-Approved, see `LICENSE`)
- **Receipts & Disclosures:** See `STDLIB.md` and `deps-proof.txt`

---

## 💡 What is ChronoReplay?

In traditional systems, state is stored as a mutable snapshot of the present moment—when data is updated or deleted, past context is lost forever.

**ChronoReplay** implements event-sourcing principles using pure Python standard library:
- **Events as the Single Source of Truth:** Business operations (user creation, wallet funding, order placement, payments) and workspace file modifications are stored as immutable, sequential events in an append-only SQLite database.
- **Deterministic State Reconstruction:** Application state is never overwritten; it is calculated deterministically on demand by replaying events from Step 1 to Step $N$.
- **Bidirectional Time Travel:** Step backward or forward through any historical moment in time to inspect exact user balances, order states, and workspace files as they existed at that instant.
- **Append-Only State Restoration:** Rewind to an earlier state and make it active by appending an immutable `state.restored` event to the ledger—zero historical data is erased or destroyed.
- **Point-in-Time Workspace Rollback:** Track, diff, and restore workspace files with line-by-line granular selective merge and rollback.

---

## ✨ Features

1. **Immutable Append-Only Event Store (`sqlite3`, `dataclasses`)**
   - Sequential, tamper-evident transaction ledger with SHA-256 event checksums.
2. **Deterministic State Engine & Invariant Diagnostics (`copy`, `json`)**
   - Reconstructs full business state on the fly. Automatically detects and flags invariant violations (e.g., overdraft attempts, unpaid order transitions).
3. **Interactive Time Machine & State Scrubbing**
   - Step through historical state chronologically, jump to arbitrary event steps, and filter timelines by user ID or calendar date.
4. **Append-Only State Restoration**
   - Restores past application state non-destructively by recording a `state.restored` event, ensuring a 100% complete audit trail.
5. **Workspace File Version History & Diffs (`difflib`, `os`, `pathlib`)**
   - Watches directory files, creates SHA-256 content snapshots, computes unified line diffs, and restores full files or selected line subsets safely without leaving the workspace sandbox.
6. **Zero-Dependency Native Dark GUI (`tkinter`, `ttk`)**
   - Modern, responsive graphical interface featuring an Event Simulator, Time Machine, and Workspace Recovery dashboards.
7. **Single-File Deterministic Compilation (`build.py`)**
   - Compiles the entire modular application into a single standalone artifact (`artifacts/chronoreplay-single.py`) with byte-for-byte reproducible SHA-256 hashing.

---

## 🏗️ Architecture

```text
[User Actions / Simulator] ──> [EventValidator] ──> [EventStore (SQLite)]
                                                           │
                                          ┌────────────────┴────────────────┐
                                          ▼                                 ▼
                                   [StateEngine]                    [VersionHistory]
                             (Replays & Reduces State)            (File Diffs & Hashes)
                                          │                                 │
                                          └────────────────┬────────────────┘
                                                           ▼
                                            [ChronoReplay Time Machine UI]
```

### Modular Components (`src/`):
- `src/event.py`: Immutable event dataclass definitions, schema validation hooks, and automatic ID generation.
- `src/validator.py`: Business logic validation and payload type/range verification.
- `src/store.py`: Append-only SQLite event and file snapshot persistence.
- `src/snapshot.py`: File snapshot models with SHA-256 content hashing.
- `src/state.py`: Deterministic state reducer, user wallet engine, and invariant diagnostics.
- `src/replay.py`: Bidirectional event replayer and point-in-time state reconstructor.
- `src/history.py`: High-level file version history and `difflib` unified diff engine.
- `src/restore.py`: Sandboxed file restorer, partial line-selective merger, and state restoration.
- `src/watcher.py` & `src/tracker.py`: Filesystem change detection via differential polling.
- `src/workspace.py`: Workspace manager, relative path safety sandboxing, and snapshot tracker.
- `src/simulator.py`: Event simulator with automatic user/order context resolution.
- `src/relay.py`: In-memory publish/subscribe observer relay.
- `src/chrono.py`: Main ChronoReplay orchestration engine facade.
- `src/ui.py`: Native dark-themed desktop Tkinter GUI dashboard.

---
---

## 🎮 Demo — Click and Play
Judges can launch the actual ChronoReplay desktop GUI directly from the public GitHub repository without cloning the repository or installing any third-party Python packages.

Requirement: Python 3.10+ with Tkinter and an internet connection.

### ⚡ 1-Click / 1-Line Instant Demo (No Git Clone Required!)

Judges do not need to clone the entire repository or install any virtual environment. You can stream and execute the standalone single file directly from GitHub using Python's standard `urllib`:

**Windows (PowerShell):**
```powershell
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/moreshwetal417/ChronoReplay---ZERO-DEPENDENCY-/main/artifacts/chronoreplay-single.py').read().decode('utf-8'))"
```

**macOS / Linux (Bash):**
```bash
curl -fsSL https://raw.githubusercontent.com/moreshwetal417/ChronoReplay---ZERO-DEPENDENCY-/main/artifacts/chronoreplay-single.py | python3
```

*(Alternatively, judges can simply download the single file [`artifacts/chronoreplay-single.py`](artifacts/chronoreplay-single.py) by right-clicking "Raw" -> "Save Link As..." and double-clicking or running `python chronoreplay-single.py` directly.)*

### 🖥️ Standard Execution (Cloned Repo)

#### Run via Single-File Standalone Artifact:
```bash
python artifacts/chronoreplay-single.py
```
- Launches the complete graphical desktop Tkinter application containing the full engine, simulator, time machine, and file restorer in one file.

#### Run Modular Source Application:
```bash
python main.py
```

---

## 📦 Single-File Artifact & Commands

ChronoReplay includes a deterministic build script that packages all modular source code into a standalone single-file distribution:

### Build and Verify the Reproducible Artifact
```bash
python build.py
```
- Compiles `src/*.py` into `artifacts/chronoreplay-single.py`.
- Executes two successive build passes to verify byte-for-byte reproducibility.

### Launch Complete Application via Single-File Artifact
```bash
python artifacts/chronoreplay-single.py
```
- Launches the complete graphical desktop application containing all engine and UI features in one self-contained Python file.

### Run Standalone CLI Self-Test
```bash
python artifacts/chronoreplay-single.py --cli
```
- Executes headless standalone self-tests verifying event publication, wallet deductions, invariant checking, time-travel rewind, and append-only state restoration in memory.
- Expected Exit Code: `0` (`$LASTEXITCODE = 0`).

---

## 🧪 How to Test

Run the full automated unit test suite (150+ tests covering all modules) using Python's built-in `unittest` runner:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 🔒 Zero-Dependency Proof

Verify that `requirements.txt` and the runtime environment require zero third-party packages:

```bash
cat requirements.txt
# Output: # Zero third-party runtime dependencies. Standard library only.
```

Inspect dependencies with pip:
```bash
pip list
```

---

## 📋 Standard Library Substitutions Summary

For complete details on all 13 zero-dependency standard library replacements and design rationale, refer to [`STDLIB.md`](STDLIB.md).

| Capability Replaced | Standard Library Replacement | ChronoReplay Module |
|---------------------|------------------------------|---------------------|
| `Pydantic` / `Attrs` | `dataclasses` | `src/event.py`, `src/snapshot.py` |
| `SQLAlchemy` / `Peewee` | `sqlite3` | `src/store.py` |
| `watchdog` / `inotify` | `os` + `pathlib` + `time` | `src/watcher.py`, `src/tracker.py` |
| `orjson` / `ujson` | `json` | `src/event.py`, `src/store.py` |
| `GitPython` / `diff-match-patch` | `difflib` | `src/history.py`, `src/ui.py` |
| `PyCryptodome` (Hashing) | `hashlib` | `src/snapshot.py`, `build.py` |
| `shortuuid` | `uuid` | `src/event.py`, `src/tracker.py` |
| `Arrow` / `Pendulum` | `datetime` | `src/event.py`, `src/snapshot.py` |
| `PyQt` / `CustomTkinter` | `tkinter` + `ttk` | `src/ui.py` |
| `pyrsistent` / `Immer` | `copy.deepcopy` | `src/state.py`, `src/replay.py` |
| `path.py` / `pathlib2` | `pathlib` + `os.path` | `src/workspace.py`, `src/restore.py` |
| `PyPubSub` / `blinker` | Observer Relay | `src/relay.py`, `src/chrono.py` |
| `pytest` | `unittest` | `tests/test_*.py` |

---

## 📂 Project Structure

```text
ChronoReplay---ZERO-DEPENDENCY-/
├── artifacts/
│   └── chronoreplay-single.py # Standalone single-file build artifact
├── src/
│   ├── chrono.py              # Orchestration engine facade
│   ├── event.py               # Immutable event dataclasses & ID generators
│   ├── history.py             # Version history & diff query engine
│   ├── relay.py               # In-memory pub/sub observer relay
│   ├── replay.py              # Replay engine & time-travel state reconstruction
│   ├── restore.py             # File restore manager & state restoration
│   ├── simulator.py           # Business transaction simulator
│   ├── snapshot.py            # File snapshot model & SHA-256 integrity
│   ├── state.py               # Deterministic state engine & invariant diagnostics
│   ├── store.py               # SQLite append-only event store & snapshot storage
│   ├── tracker.py             # Automatic workspace change tracker
│   ├── ui.py                  # Complete native Tkinter dark GUI dashboard
│   ├── validator.py           # Event payload validation rules
│   ├── watcher.py             # Filesystem polling watcher
│   └── workspace.py           # Sandboxed workspace manager
├── tests/
│   ├── test_chrono.py         # Facade tests
│   ├── test_event.py          # Event model & validation tests
│   ├── test_history.py        # Version history & diff tests
│   ├── test_relay.py          # Relay subscriber tests
│   ├── test_replay.py         # Time machine & replay tests
│   ├── test_restore.py        # File & state restoration tests
│   ├── test_simulator.py      # Simulator workflow tests
│   ├── test_snapshot.py       # Snapshot hashing tests
│   ├── test_state.py          # State reducer & invariant tests
│   ├── test_store.py          # SQLite storage & rollback tests
│   ├── test_tracker.py        # Workspace tracker tests
│   ├── test_validator.py      # Event validator tests
│   ├── test_watcher.py        # Directory watcher tests
│   └── test_workspace.py      # Workspace sandboxing tests
├── build.py                   # Deterministic single-file builder & verifier
├── deps-proof.txt             # Zero-dependency verification report
├── LICENSE                    # MIT Open-Source License
├── main.py                    # Modular entry point
├── README.md                  # Project documentation
├── requirements.txt           # Empty (0 dependencies)
└── STDLIB.md                  # Detailed stdlib substitutions document
```

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
