from datetime import datetime

from beanie import after_event, Update
from pydantic import Field


class DatetimeTimestamp:
    created_at: datetime = Field(default=datetime.now(), description="Create date")
    updated_at: datetime = Field(default=datetime.now(), description="Updated date")

    @after_event(Update)
    def set_updated_at(self):
        self.updated_at = datetime.now()
