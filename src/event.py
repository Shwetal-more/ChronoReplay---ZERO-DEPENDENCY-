"""
ChronoReplay event model.

Events are immutable historical facts.
ChronoReplay automatically assigns user IDs and order IDs
when the simulator does not provide them.

Only Python standard-library modules are used.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import uuid


@dataclass
class Event:
    """
    Represents one event in ChronoReplay.
    """

    id: str
    version: int
    type: str
    timestamp: str
    data: dict

    def __post_init__(self):
        self._validate()

    def _validate(self):
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Event id must be a non-empty string.")

        if not isinstance(self.version, int) or self.version < 1:
            raise ValueError("Event version must be a positive integer.")

        if not isinstance(self.type, str) or not self.type.strip():
            raise ValueError("Event type must be a non-empty string.")

        if not isinstance(self.timestamp, str) or not self.timestamp.strip():
            raise ValueError("Event timestamp must be a non-empty string.")

        if not isinstance(self.data, dict):
            raise ValueError("Event data must be a dictionary.")

    # =========================================================
    # ID GENERATORS
    # =========================================================

    @staticmethod
    def generate_user_id(seq: int = None):
        """
        ChronoReplay assigns user IDs.

        Users never need to type a user ID manually.
        """
        if seq is not None and isinstance(seq, int):
            return f"USR-{seq:04d}"
        return "USR-" + uuid.uuid4().hex[:8].upper()

    @staticmethod
    def generate_order_id(seq: int = None):
        """
        ChronoReplay assigns order IDs.

        Users never need to type an order ID manually.
        """
        if seq is not None and isinstance(seq, int):
            return f"ORD-{seq:04d}"
        return "ORD-" + uuid.uuid4().hex[:8].upper()

    @staticmethod
    def generate_event_id():
        """
        Generate a unique event ID.
        """
        return str(uuid.uuid4())

    # =========================================================
    # EVENT CREATION
    # =========================================================

    @classmethod
    def create(
        cls,
        event_type: str,
        data: dict,
        user_id=None,
        order_id=None,
    ) -> "Event":
        """
        Create a new event.

        IDs are automatically assigned.

        Rules:

        user.created
            -> creates a new user automatically

        order.created
            -> creates a new order automatically
            -> attaches it to the supplied/current user

        payment.completed
            -> attaches to the supplied/current user

        Other user-related events
            -> attach to supplied user
        """

        if not isinstance(data, dict):
            raise ValueError("Event data must be a dictionary.")

        data = dict(data)

        if user_id:
            data["user_id"] = user_id
        if order_id:
            data["order_id"] = order_id

        return cls(
            id=cls.generate_event_id(),
            version=1,
            type=event_type,
            timestamp=datetime.now().astimezone().isoformat(),
            data=data,
        )

    # =========================================================
    # SERIALIZATION
    # =========================================================

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            separators=(",", ":"),
            sort_keys=True,
        )

    # =========================================================
    # DESERIALIZATION
    # =========================================================

    @classmethod
    def from_dict(cls, value: dict) -> "Event":

        if not isinstance(value, dict):
            raise ValueError("Input must be a dictionary.")

        required_fields = {
            "id",
            "version",
            "type",
            "timestamp",
            "data",
        }

        missing = required_fields - value.keys()

        if missing:
            raise ValueError(
                f"Missing required fields: {', '.join(sorted(missing))}"
            )

        return cls(
            id=value["id"],
            version=value["version"],
            type=value["type"],
            timestamp=value["timestamp"],
            data=value["data"],
        )

    @classmethod
    def from_json(cls, value: str) -> "Event":

        try:
            data = json.loads(value)

        except json.JSONDecodeError as exc:
            raise ValueError("Invalid event JSON") from exc

        return cls.from_dict(data)
