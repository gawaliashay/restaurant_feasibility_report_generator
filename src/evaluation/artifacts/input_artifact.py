from pydantic import BaseModel


class InputArtifact(BaseModel):
    restaurant_concept: str | None = None
    investment: str | None = None
    target_demographic: str | None = None
    special_note: str | None = None

    society: str | None = None
    local_area: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None