from pydantic import BaseModel, ConfigDict


class BisibilityModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
