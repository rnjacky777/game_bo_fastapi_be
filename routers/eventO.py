from schemas.event import AddEventResultRequest, CreateEventRequest, EditEventRequest, EditEventResultRequest
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from dependencies.db import get_db
from services.event_service import create_event_result_service, create_event_service, create_general_logic, edit_event_result_service, edit_event_service, edit_general_logic, get_event_by_event_id, get_event_result
from services.reward_pool_service import add_reward_pool
router = APIRouter()


@router.post("/CreateEvent")
def create_event(data: CreateEventRequest, db: Session = Depends(get_db)):
    event = create_event_service(db=db,
                                 name=data.name,
                                 event_type=data.event_type,
                                 description=data.description
                                 )

    create_general_logic(db=db,
                         event_id=event.id,
                         )
    return {"message": "success"}


@router.put("/EditEvent")
def edit_event(data: EditEventRequest, db: Session = Depends(get_db)):
    edit_event_service(db=db, event_id=data.event_id,
                       story_text=data.story_text,
                       description=data.description)

    return {"message": "success"}


@router.get("/{event_id}")
def get_event_detail(event_id: int, db: Session = Depends(get_db)):
    event = get_event_by_event_id(db=db, event_id=event_id)
    return {
        "event_id": event.id,
        "name": event.name,
        "type": event.type,
        "description": event.description,
        "story_text": event.general_logic.get_story_text(),
        "condition": event.general_logic.get_condition_list()
    }


@router.post("/AddEventResult")
def create_event_result(data: AddEventResultRequest, db: Session = Depends(get_db)):
    event = get_event_by_event_id(db=db, event_id=data.event_id)
    reward_pool_id = add_reward_pool(db=db, name=f"{data.name}_pool")
    create_event_result_service(db=db,
                                name=data.name,
                                reward_pool_id=reward_pool_id,
                                general_event_logic_id=event.general_logic.id)
    return {"message": "success"}


@router.put("/EditEventResult")
def edit_event_result(data: EditEventResultRequest, db: Session = Depends(get_db)):
    edit_event_result_service(db=db,
                              event_result_id=data.event_result_id,
                              prior=data.prior,
                              story_text=data.story_text,
                              condition=data.condition_list
                              )

    return {"message": "success"}
