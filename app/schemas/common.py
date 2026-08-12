from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator


def _force_utc(value: datetime) -> datetime:
    # SQLite hands back naive datetimes even for DateTime(timezone=True)
    # columns, and every stored timestamp here is UTC (CURRENT_TIMESTAMP /
    # func.now()). Tagging the zone makes JSON carry an explicit offset, so
    # browsers stop parsing the value as local wall-clock time.
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


UTCDateTime = Annotated[datetime, AfterValidator(_force_utc)]
