import logging
from typing import Optional
from schemas.event import AddEventResultRequest, AddItemToEventResultRequest, CreateEventRequest, EditEventRequest, EditEventResultItemProbRequest, EditEventResultRequest, EventData, ListEventsResponse, RemoveEventRequest, RemoveEventResultRequest, RemoveItemFromEventResultRequest
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Query
from dependencies.db import get_db
from core_system.services.event_service import create_event_result_service, create_event_service, create_general_logic, delete_event, delete_event_result, edit_event_result_service, edit_event_service, edit_general_logic, fetch_events, get_event_by_event_id, get_event_result
from core_system.services.reward_pool_service import add_reward_pool, add_reward_pool_item, edit_reward_pool_item, remove_reward_pool_item
router = APIRouter()


@router.get("/list-event", response_model=ListEventsResponse)
def get_event_list(
    prev_id: Optional[int] = Query(None),
    next_id: Optional[int] = Query(None, description="從此 ID 之後的項目"),
    limit: int = Query(20, ge=1, le=100, description="每頁項目數"),
    db: Session = Depends(get_db)
):
    # 設定方向為 next，始終使用 next_id 進行分頁
    if prev_id:
        direction = "prev"
        started_id = prev_id
    else:
        direction = "next"
        started_id = next_id

    # 增加額外一筆資料來判斷是否有更多
    fetch_limit = limit + 1

    # 獲取項目
    events = fetch_events(db, started_id, fetch_limit, direction)

    # 判斷是否還有更多資料
    has_more = len(events) == fetch_limit

    # 若有更多資料，移除額外多取的項目
    if has_more:
        events.pop()

    # 如果資料少於 limit，表示沒有更多資料，last_id 設為 None
    if not prev_id and not has_more:
        last_id = None
    else:
        last_id = events[-1].id

    return ListEventsResponse(
        last_id=last_id,  # 返回最後一筆資料的 ID
        event_list=[  # 返回項目資料
            EventData(
                event_id=event.id,
                name=event.name,
                description=event.description
            )
            for event in events
        ]
    )


@router.get("/{event_id}")
def get_event(event_id: Optional[int], db: Session = Depends(get_db)):
    event = get_event_by_event_id(db=db, event_id=event_id)
    return EventData(
        event_id=event.id,
        name=event.name,
        description=event.description
    )


@router.post("/CreateEvent")
def create_event(data: CreateEventRequest, db: Session = Depends(get_db)):
    for event_data in data.event_datas:
        event = create_event_service(db=db,
                                     name=event_data.name,
                                     event_type=event_data.event_type,
                                     description=event_data.description
                                     )

        create_general_logic(db=db,
                             event_id=event.id,
                             )
    return {"message": "success"}


@router.put("/{event_id}")
def edit_event(event_id: int, data: EditEventRequest, db: Session = Depends(get_db)):
    edit_event_service(db=db,
                       event_id=event_id,
                       story_text=data.story_text,
                       description=data.description,
                       name=data.name)

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
        "result_list": [{"name": result.name,
                         "result_id": result.id} for result in event.general_logic.event_results]
    }


@router.delete("/{event_id}")
def remove_event_result(event_id: int, db: Session = Depends(get_db)):
    delete_event(db=db,
                 event_id=event_id)

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


@router.put("/result/{result_id}")
def edit_event_result(result_id: int, data: EditEventResultRequest, db: Session = Depends(get_db)):
    logging.info(f"Check go to edit_event_result")
    edit_event_result_service(db=db,
                              name = data.name,
                              event_result_id=result_id,
                              prior=data.prior,
                              story_text=data.story_text,
                              condition=data.condition_list,
                              status_effects_json=data.status_effects_json
                              )

    return {"message": "success"}


@router.get("/result/{event_result_id}")
def get_event_detail(event_result_id: int, db: Session = Depends(get_db)):
    event_result = get_event_result(db=db, event_result_id=event_result_id)
    return {
        "event_result_id": event_result.id,
        "name": event_result.name,
        "prior":event_result.prior,
        "story_text": event_result.get_story_text(),
        "condition": event_result.get_condition_list(),
        "status_effects": event_result.get_status_effects_json(),
        "reward_pool": [{"name": item.item_detail.name,
                         "item_id": item.item_id,
                         "probability": item.probability}for item in event_result.reward_pool.items]
    }


@router.delete("/result/{event_result_id}")
def remove_event_result(event_result_id: int, db: Session = Depends(get_db)):
    delete_event_result(db=db,
                        result_id=event_result_id)

    return {"message": "success"}


@router.post("/add-event-result-item")
def add_item_to_event_result(data: AddItemToEventResultRequest, db: Session = Depends(get_db)):
    event_result = get_event_result(db=db, event_result_id=data.result_id)
    add_reward_pool_item(db=db,
                         pool_id=event_result.reward_pool_id,
                         item_id=data.item_id,
                         probability=data.probability)

    return {"message": "success"}


@router.delete("/result/{result_id}/items/{item_id}")
def remove_item_from_event_result(result_id: int, item_id: int, db: Session = Depends(get_db)):
    event_result = get_event_result(db=db, event_result_id=result_id)
    remove_reward_pool_item(db=db,
                            pool_id=event_result.reward_pool_id,
                            item_id=item_id)

    return {"message": "success"}


@router.put("/result/{result_id}/items/{item_id}")
def edit_event_result_item_probability(result_id: int, item_id: int, data: EditEventResultItemProbRequest, db: Session = Depends(get_db)):
    event_result = get_event_result(db=db, event_result_id=result_id)
    edit_reward_pool_item(db=db,
                          pool_id=event_result.reward_pool_id,
                          item_id=item_id,
                          probability=data.probability
                          )

    return {"message": "success"}
