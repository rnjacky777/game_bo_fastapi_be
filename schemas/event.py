from typing import Optional
from pydantic import BaseModel


class EventData(BaseModel):
    event_id: int
    name: str
    description: str


class ListEventsResponse(BaseModel):
    last_id: Optional[int] = None
    event_list: list[EventData] = []


class StoryTextData(BaseModel):
    name: str = None
    text: str


class AddEventResultRequest(BaseModel):
    event_id: int
    name: str


class CreateEventData(BaseModel):
    name: str
    event_type: str
    description: Optional[str]


class CreateEventRequest(BaseModel):
    event_datas: list[CreateEventData]


class EditEventRequest(BaseModel):
    description: Optional[str] = None
    story_text: list[StoryTextData] = None
    name: Optional[str] = None


class ConditionData(BaseModel):
    condition_key: Optional[str] = None
    condition_value: Optional[str] = None

class StatusEffectData(BaseModel):
    status_effect_key: Optional[str] = None
    status_effect_value: Optional[str] = None

class EditEventResultRequest(BaseModel):
    name: Optional[str] = None
    prior: Optional[int] = None
    story_text: list[StoryTextData] = None
    condition_list: list[ConditionData] = None
    status_effects_json: list[StatusEffectData] = None


class EditEventResultItemProbRequest(BaseModel):
    probability: float


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
