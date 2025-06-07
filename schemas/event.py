from typing import Optional
from pydantic import BaseModel


class StoryTextData(BaseModel):
    name: str = None
    text: str


class AddEventResultRequest(BaseModel):
    event_id: int
    name: str


class CreateEventRequest(BaseModel):
    name: str
    event_type: str
    description: str


class EditEventRequest(BaseModel):
    event_id: int
    description: Optional[str] = None
    story_text: list[StoryTextData] = None


class EditEventResultRequest(BaseModel):
    event_result_id: int
    prior: int
    story_text: list[StoryTextData] = None
    condition_list: list[dict]

class AddItemToEventResultRequest(BaseModel):
    item_id: int
    probability: float
    result_id: int

class RemoveItemFromEventResultRequest(BaseModel):
    item_id: int
    result_id: int

class RemoveEventResultRequest(BaseModel):
    result_id: int

class RemoveEventRequest(BaseModel):
    event_id: int