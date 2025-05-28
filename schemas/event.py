from pydantic import BaseModel


class StoryTextData(BaseModel):
    name: str = None
    text: str


class ConditionData(BaseModel):
    result_id: int
    prior: int
    condition: dict


class AddEventResultRequest(BaseModel):
    event_id: int
    name: str
    story_text: list[StoryTextData] = []
    condition_list: list[ConditionData] = []
    reward_pool_id: int
    prior: int


class CreateEventRequest(BaseModel):
    name: str
    event_type: str
    description: str
    story_text: list[StoryTextData] = []
