from datetime import datetime, UTC
from typing import Optional


class DatetimeTimestamp:
    created_at: Optional[datetime] = datetime.now(tz=UTC)
    updated_at: Optional[datetime] = datetime.now(tz=UTC)
