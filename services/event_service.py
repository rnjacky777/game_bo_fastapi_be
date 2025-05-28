from pydantic import Json
from sqlalchemy.orm import Session
from typing import Optional
from models import Item
from models.event import ConditionData, Event, GeneralEventLogic, EventResult,StoryTextData


def create_event_service(db: Session, name: str, event_type: str, description: str = None):
    event = Event(name=name,
                  type=event_type,
                  description=description)
    db.add(event)
    db.commit()
    db.flush(event)
    return event.id


def get_general_logic_by_event_id(db: Session, event_id: int) -> GeneralEventLogic:
    event_logic = db.query(GeneralEventLogic).filter_by(
        event_id=event_id).first()
    return event_logic


def edit_event_logic(db: Session, event_logic: GeneralEventLogic,condition_data:ConditionData=None):
    if condition_data:
        condition_list = event_logic.get_condition_list()
        condition_list.append(condition_data)
        event_logic.set_condition_list(condition_list)
    db.commit()

def edit_event_result(db: Session, event_result: EventResult,story_text_list:list[StoryTextData]=None):
    if story_text_list:
        event_result.set_story_text(story_text_list)
    db.commit()


def edit_general_logic(db: Session, general_logic: GeneralEventLogic,story_text_list:list[StoryTextData]=None):
    if story_text_list:#move to outside
        general_logic.set_story_text(story_text_list)
    db.commit() 

def create_general_logic(db: Session, event_id: int, story_text: str = []):
    general_logic = GeneralEventLogic(event_id=event_id,
                                      story_text=story_text,
                                      condition_json=[])
    db.add(general_logic)
    db.commit()
    db.flush(general_logic)
    return general_logic


def create_event_result(db: Session, name: str, reward_pool_id: int = None):
    event_result = EventResult(name=name,
                               reward_pool_id=reward_pool_id
                               )
    db.add(event_result)
    db.commit()
    db.flush(event_result)
    return event_result
