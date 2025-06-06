from schemas.event import AddEventResultRequest, AddItemToEventResultRequest, CreateEventRequest, EditEventRequest, EditEventResultRequest, RemoveEventRequest, RemoveEventResultRequest, RemoveItemFromEventResultRequest
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from dependencies.db import get_db
from core_system.services.event_service import create_event_result_service, create_event_service, create_general_logic, delete_event, delete_event_result, edit_event_result_service, edit_event_service, edit_general_logic, get_event_by_event_id, get_event_result
from core_system.services.reward_pool_service import add_reward_pool, add_reward_pool_item, remove_reward_pool_item
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
        "result_list": [{"name": result.name,
                         "result_id": result.id} for result in event.general_logic.event_results]
    }


@router.delete("/remove-event")
def remove_event_result(data: RemoveEventRequest, db: Session = Depends(get_db)):
    delete_event(db=db,
                 event_id=data.event_id)

    return {"message": "success"}


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


@router.get("/result/{event_result_id}")
def get_event_detail(event_result_id: int, db: Session = Depends(get_db)):
    event_result = get_event_result(db=db, event_result_id=event_result_id)
    return {
        "event_result_id": event_result.id,
        "name": event_result.name,
        "story_text": event_result.get_story_text(),
        "condition": event_result.get_condition_list(),
        "reward_pool": [{"name": item.item_detail.name,
                         "item_id": item.item_id}for item in event_result.reward_pool.items]
    }


@router.delete("/remove-event-result")
def remove_event_result(data: RemoveEventResultRequest, db: Session = Depends(get_db)):
    delete_event_result(db=db,
                        result_id=data.result_id)

    return {"message": "success"}


@router.post("/add-event-result-item")
def add_item_to_event_result(data: AddItemToEventResultRequest, db: Session = Depends(get_db)):
    event_result = get_event_result(db=db, event_result_id=data.result_id)
    add_reward_pool_item(db=db,
                         pool_id=event_result.reward_pool_id,
                         item_id=data.item_id,
                         probability=data.probability)

    return {"message": "success"}


@router.delete("/remove-event-result-item")
def remove_item_from_event_result(data: RemoveItemFromEventResultRequest, db: Session = Depends(get_db)):
    event_result = get_event_result(db=db, event_result_id=data.result_id)
    remove_reward_pool_item(db=db,
                            pool_id=event_result.reward_pool_id,
                            item_id=data.item_id)

    return {"message": "success"}
