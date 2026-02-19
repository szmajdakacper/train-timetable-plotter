from pydantic import BaseModel


class SelectSheetRequest(BaseModel):
    sheet: str


class SaveTimeRequest(BaseModel):
    sheet: str
    station: str
    km: float
    train_number: str
    hour: int
    minute: int
    second: int = 0
    day_offset: int = 0
    stop_type: str | None = None
    propagate: bool = False


class ClearTimeRequest(BaseModel):
    sheet: str
    station: str
    km: float
    train_number: str
    stop_type: str | None = None


class SetColorRequest(BaseModel):
    train_number: str
    color: str
