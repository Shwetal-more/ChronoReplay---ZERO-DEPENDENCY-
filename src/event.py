# The database automatically creates the basic constuctor for our event class.
#This saves us from writing a lot of repetitive code ourseleves.
from dataclasses import dataclass, asdict

#datetime gives us timestamps, and timezone lets us create UTC timestamps for our events.
from datetime import datetime, timezone

#jsonis used to convert python dictionaries to json and json back to dictionaries.
import json

#uuid generates unique identifiers for every events.
import uuid

@dataclass
class Event:
    """
    Represents one event in ChronoReplay.

    Every event has:
    - id        -> unique identifier
    - version   -> event format version
    - type      -> what happened
    - timestamp -> when it happened
    - data      -> information related to the event
    """
    id: str
    version: int
    type: str
    timestamp: str
    data: dict

    def __post_init__(self):
        self._validate()

    def _validate(self):
        """
        Validates the event data.
        Raises ValueError if any validation fails.
        """
        # An event must have a non-empty ID.
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Event id must be a non-empty string.")
        # Version must be a positive number.
        if not isinstance(self.version, int) or self.version < 1:
            raise ValueError("Event version must be a non-negative integer.")
        # Event type tells us what happened, so it cannot be empty.
        if not isinstance(self.type, str) or not self.type.strip():
            raise ValueError("Event type must be a non-empty string.")
        # Every event needs a timestamp.
        if not isinstance(self.timestamp, str) or not self.timestamp.strip():
            raise ValueError("Event timestamp must be a non-empty string.")
        # Event data must be stored as a dictionary.
        if not isinstance(self.data, dict):
            raise ValueError("Event data must be a dictionary.")
    @classmethod
    def create(cls, event_type: str, data: dict) -> 'Event':
        """
        Create a brand-new Event.

        The user only provides the event type and data.
        We automatically generate the ID, version, and timestamp.
        """

        return cls(
            #Generate a unique identifier for the event using python's standard library uuid.
            id=str(uuid.uuid4()),

            #The version is always 1 for new events.
            version=1,

            #store the event type provided by the caller.
            type=event_type,

            #store the current UTC timestamp.
            timestamp=datetime.now(timezone.utc).isoformat(),   

            #store the event data provided by the caller.
            data=data,
        )
    def to_dict(self) -> dict:
        """
        Convert the Event object to a dictionary.
        This is useful for sending and event and storage.
        """
        return asdict(self)
    def to_json(self) -> str:
        """
        Convert the Event object to a JSON string.
        This is useful for HTTP API and event storage.
        """
        return json.dumps(
            self.to_dict(),
            separators=(',', ':'),
            sort_keys=True,
        )
    
    @classmethod
    def from_dict(cls, value: dict) -> "Event":
        """
        Create an Event object from a dictionary.
        This is useful for receiving events from storage or HTTP API.
        """
        # make sure the input is a dictionary
        if not isinstance(value, dict):
            raise ValueError("Input must be a dictionary.")

        # These are the fields every event must have. If any of them are missing, we raise an error.
        required_fields = {
            "id", 
            "version", 
            "type", 
            "timestamp", 
            "data",
        }

        # Find which required fields are missing from the input dictionary.
        missing = required_fields - value.keys()

        if missing:
            raise ValueError(
                f"Missing required fields: {', '.join(sorted(missing))}"
            )

        # Create the Event object using the dictionary values.
        return cls(
            id=value["id"],
            version=value["version"],
            type=value["type"],
            timestamp=value["timestamp"],
            data=value["data"],
        )
    
    @classmethod
    def from_json(cls, value: str) -> "Event":
        """
        Create an Event from a JSON string.

        JSON -> dictionary -> Event object.
        """

        try:
            # Convert JSON text into a Python dictionary.
            data = json.loads(value)

        except json.JSONDecodeError as exc:
            # Give our own simple error if the JSON is invalid.
            raise ValueError("Invalid event JSON") from exc

        # Reuse our dictionary validation/conversion logic.
        return cls.from_dict(data)