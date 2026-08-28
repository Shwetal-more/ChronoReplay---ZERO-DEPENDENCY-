# STDLIB Substitutions

This project uses only Python's standard library.
No third-party runtime dependencies are required.

---

## Implemented Substitutions

### 1. Pydantic → dataclasses

**Capability:** Structured event models and basic validation

**Why we didn't use Pydantic:**
Pydantic is a third-party dependency and would violate the
zero-dependency requirement.

**Standard library replacement:**
`dataclasses`

**How we use it:**
The `Event` dataclass represents the event structure and
performs basic validation through `__post_init__`.

**Tradeoff:**
We implement validation ourselves rather than relying on
Pydantic's schema and validation system.

---

### 2. json libraries → json

**Capability:** JSON serialization/deserialization

**Why we didn't use a third-party JSON package:**
The Python standard library already provides the required
functionality.

**Standard library replacement:**
`json`

**How we use it:**
Events are converted between Python dictionaries and JSON strings.

**Tradeoff:**
The standard library implementation is sufficient for our use case,
but may not provide the performance of specialized JSON libraries.

---

### 3. UUID package → uuid

**Capability:** Unique event identifiers

**Standard library replacement:**
`uuid`

**How we use it:**
New events receive UUID-based identifiers.

**Tradeoff:**
We use standard UUID generation rather than a specialized ID library.

---

### 4. Date/time package → datetime

**Capability:** Event timestamps

**Standard library replacement:**
`datetime`

**How we use it:**
Events receive UTC timestamps using Python's standard datetime APIs.

**Tradeoff:**
We handle time formatting and timezone behavior ourselves.