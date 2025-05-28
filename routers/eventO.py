import json
from typing import List
from models.event import ConditionData
from schemas.event import AddEventResultRequest, CreateEventRequest
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from dependencies.db import get_db
from services.event_service import create_event_service, create_general_logic, edit_general_logic, get_general_logic_by_event_id, create_event_result, edit_event_logic,edit_event_result
from services.reward_pool_service import add_reward_pool
router = APIRouter()


@router.post("/CreateEvent")
def create_event(data: CreateEventRequest, db: Session = Depends(get_db)):
    event_id = create_event_service(db=db,
                                    name=data.name,
                                    event_type=data.event_type,
                                    description=data.description
                                    )
    general_logic = create_general_logic(event_id=event_id,
                         story_text=data.story_text,
                         )
    edit_general_logic(db=db,general_logic=general_logic,story_text_list=data.story_text)
    return {"message": "success"}


@router.post("/AddEventResult")
def add_event_result(data: AddEventResultRequest, db: Session = Depends(get_db)):
    event_logic = get_general_logic_by_event_id(db=db, event_id=data.event_id)
    reward_pool_id = add_reward_pool(db=db, name=f"{data.name}_pool")
    event_result = create_event_result(db=db, name=data.name,
                                          reward_pool_id=reward_pool_id)

    condition_data = ConditionData(result_id=event_result.id,
                                   condition=data.condition_list,
                                   prior=data.prior)
    
    edit_event_result(db=db,event_result=event_result,story_text_list=data.story_text)
    edit_event_logic(db=db, event_logic=event_logic,
                     condition_data=condition_data,
                     )
    return {"message": "success"}
