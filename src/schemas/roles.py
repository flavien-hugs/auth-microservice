from typing import Optional

from pydantic import BaseModel, StrictStr, Field


class RoleModel(BaseModel):
    name: StrictStr = Field(..., description="Role name")
    description: Optional[StrictStr] = Field(None, description="Role description")
