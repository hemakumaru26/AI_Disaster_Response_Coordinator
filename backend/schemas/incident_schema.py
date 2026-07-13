from pydantic import BaseModel


class IncidentSchema(BaseModel):
    reporter_name: str
    phone: str
    disaster_type: str
    location: str
    people_affected: int
    description: str