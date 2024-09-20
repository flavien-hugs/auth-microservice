from pydantic import BaseModel


class ParamsModel(BaseModel):
    name: str
    type: str
