from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    versions: dict[str, str]
