from pydantic import BaseModel, Field


class ParamsModel(BaseModel):
    name: str = Field(..., description="Name of the parameter")
    type: str = Field(..., description="Type of the parameter")
