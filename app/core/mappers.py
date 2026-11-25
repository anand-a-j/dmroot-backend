import json
from typing import Any


def record_to_dict(record: Any | None) -> dict | None:
    """Convert an asyncpg Record into a dictionary."""
    if record is None:
        return None

    data = dict(record)

    # Handle PostgreSQL JSONB fields.
    for key, value in data.items():
        if isinstance(value, str):
            try:
                data[key] = json.loads(value)
            except json.JSONDecodeError:
                pass

    return data
