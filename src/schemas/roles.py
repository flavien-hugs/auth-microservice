from typing import Optional

from pydantic import BaseModel, StrictStr


class RoleModel(BaseModel):
    name: StrictStr
    description: Optional[StrictStr] = None
