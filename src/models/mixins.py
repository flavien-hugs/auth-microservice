from datetime import datetime, UTC
from typing import Optional

from beanie import after_event, Update


class DatetimeTimestamp:
    created_at: Optional[datetime] = datetime.now(tz=UTC)
    updated_at: Optional[datetime] = None

    @after_event(Update)
    def set_updated_at(self):
        self.updated_at = datetime.now(tz=UTC)
