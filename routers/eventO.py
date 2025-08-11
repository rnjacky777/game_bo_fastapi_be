import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from dependencies.db import get_db
from schemas.event import (
    AddEventResultRequest, AddItemToEventResultRequest, CreateEventRequest, 
    EditEventRequest, EditEventResultItemProbRequest, EditEventResultRequest, 
    EventData, ListEventsResponse
)
from core_system.services.event_service import (
    create_event_result_service, create_event_service, create_general_logic, 
    delete_event, delete_event_result, edit_event_result_service, 
    edit_event_service, fetch_events, get_event_by_event_id, get_event_result
)
from core_system.services.reward_pool_service import (
    add_reward_pool, add_reward_pool_item, edit_reward_pool_item, remove_reward_pool_item
)

router = APIRouter(
    prefix="/events",
    tags=["Events"]
)

# -------------------------- Event APIs -------------------------- #

@router.get("/list-event", response_model=ListEventsResponse)
def get_event_list(
    prev_id: Optional[int] = Query(None),
    next_id: Optional[int] = Query(None, description="從此 ID 之後的項目"),
    limit: int = Query(20, ge=1, le=100, description="每頁項目數"),
    db: Session = Depends(get_db)
):
    direction = "prev" if prev_id else "next"
    started_id = prev_id if prev_id else next_id
    fetch_limit = limit + 1

    events = fetch_events(db, started_id, fetch_limit, direction)
    has_more = len(events) == fetch_limit

    if has_more:
        events.pop()

    last_id = events[-1].id if events else None

    return ListEventsResponse(
        last_id=last_id,
        event_list=[
            EventData(
                event_id=event.id,
                name=event.name,
                description=event.description
            ) for event in events
        ]
    )


@router.get("/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = get_event_by_event_id(db=db, event_id=event_id)
    return EventData(
        event_id=event.id,
        name=event.name,
        description=event.description
    )


@router.post("/CreateEvent")
def create_event(data: CreateEventRequest, db: Session = Depends(get_db)):
    logging.debug('Go in to CreateEvent')
    for event_data in data.event_datas:
        event = create_event_service(
            db=db,
            name=event_data.name,
            event_type=event_data.event_type,
            description=event_data.description
        )
        logging.debug(f'event id :{event.id}')
        create_general_logic(db=db, event_id=event.id)
    db.commit()  # 在所有操作成功後，提交整個交易
    return {"message": "success"}


@router.put("/{event_id}")
def edit_event(event_id: int, data: EditEventRequest, db: Session = Depends(get_db)):
    edit_event_service(
        db=db,
        event_id=event_id,
        story_text=data.story_text,
        description=data.description,
        name=data.name
    )
    db.commit()
    return {"message": "success"}


@router.get("/detail/{event_id}")
def get_event_detail(event_id: int, db: Session = Depends(get_db)):
    event = get_event_by_event_id(db=db, event_id=event_id)
    return {
        "event_id": event.id,
        "name": event.name,
        "type": event.type,
        "description": event.description,
        "story_text": event.general_logic.get_story_text(),
        "result_list": [
            {"name": result.name, "result_id": result.id}
            for result in event.general_logic.event_results
        ]
    }


@router.delete("/{event_id}")
def remove_event(event_id: int, db: Session = Depends(get_db)):
    delete_event(db=db, event_id=event_id)
    db.commit()
    return {"message": "success"}

# ---------------------- Event Result APIs ---------------------- #

@router.post("/AddEventResult")
def create_event_result(data: AddEventResultRequest, db: Session = Depends(get_db)):
    event = get_event_by_event_id(db=db, event_id=data.event_id)
    reward_pool_id = add_reward_pool(db=db, name=f"{data.name}_pool")
    create_event_result_service(
        db=db,
        name=data.name,
        reward_pool_id=reward_pool_id,
        general_event_logic_id=event.general_logic.id
    )
    db.commit()
    return {"message": "success"}


@router.put("/result/{result_id}")
def edit_event_result(result_id: int, data: EditEventResultRequest, db: Session = Depends(get_db)):
    logging.info("Check go to edit_event_result")
    edit_event_result_service(
        db=db,
        name=data.name,
        event_result_id=result_id,
        prior=data.prior,
        story_text=data.story_text,
        condition=data.condition_list,
        status_effects_json=data.status_effects_json
    )
    db.commit()
    return {"message": "success"}


@router.get("/result/{event_result_id}")
def get_event_result_detail(event_result_id: int, db: Session = Depends(get_db)):
    event_result = get_event_result(db=db, event_result_id=event_result_id)
    return {
        "event_result_id": event_result.id,
        "name": event_result.name,
        "prior": event_result.prior,
        "story_text": event_result.get_story_text(),
        "condition": event_result.get_condition_list(),
        "status_effects": event_result.get_status_effects_json(),
        "reward_pool": [
            {
                "name": item.item_detail.name,
                "item_id": item.item_id,
                "probability": item.probability
            } for item in event_result.reward_pool.items
        ]
    }


@router.delete("/result/{event_result_id}")
def remove_event_result(event_result_id: int, db: Session = Depends(get_db)):
    delete_event_result(db=db, result_id=event_result_id)
    db.commit()
    return {"message": "success"}

# ---------------------- Reward Pool Item APIs ---------------------- #

@router.post("/add-event-result-item")
def add_item_to_event_result(data: AddItemToEventResultRequest, db: Session = Depends(get_db)):
    event_result = get_event_result(db=db, event_result_id=data.result_id)
    add_reward_pool_item(
        db=db,
        pool_id=event_result.reward_pool_id,
        item_id=data.item_id,
        probability=data.probability
    )
    db.commit()
    return {"message": "success"}


@router.delete("/result/{result_id}/items/{item_id}")
def remove_item_from_event_result(result_id: int, item_id: int, db: Session = Depends(get_db)):
    event_result = get_event_result(db=db, event_result_id=result_id)
    remove_reward_pool_item(
        db=db,
        pool_id=event_result.reward_pool_id,
        item_id=item_id
    )
    db.commit()
    return {"message": "success"}


@router.put("/result/{result_id}/items/{item_id}")
def edit_event_result_item_probability(result_id: int, item_id: int, data: EditEventResultItemProbRequest, db: Session = Depends(get_db)):
    event_result = get_event_result(db=db, event_result_id=result_id)
    edit_reward_pool_item(
        db=db,
        pool_id=event_result.reward_pool_id,
        item_id=item_id,
        probability=data.probability
    )
    db.commit()
    return {"message": "success"}
