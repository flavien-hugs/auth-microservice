from datetime import datetime, UTC
from typing import Optional
from pydantic import Field


class DatetimeTimestamp:
    created_at: Optional[datetime] = Field(default=datetime.now(tz=UTC), description="Datetime created")
    updated_at: Optional[datetime] = Field(default=datetime.now(tz=UTC), description="Datetime updated")
