import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from core_system.models.maps import Map, MapArea
from core_system.services.map_service import (
    create_maps_service,
    delete_map_area_service,
    delete_map_service,
    fetch_maps,
    get_map_by_id,
    patch_map_area_basic_service,
    patch_map_basic_service,
    patch_map_connections_service,
    update_map_area_event_associations,
    update_map_event_associations,
)
from dependencies.db import get_db
from schemas.map import (
    ConnectionsUpdate,
    CreateMapRequest,
    CreateMapResponse,
    CreatedMapInfo,
    EventAssociationOut,
    EventAssociationsUpdate,
    ListMapsResponse,
    MapAreaCreate,
    MapAreaOut,
    MapAreaUpdate,
    MapData,
    MapNeighborOut,
    MapOut,
    MapUpdate,
    MessageResponse,
    NPCInfo,
)

router = APIRouter(prefix="/maps", tags=["Maps"])


# -------------------------- Map CRUD APIs -------------------------- #

@router.get(
    "/",
    response_model=ListMapsResponse,
    summary="列出地圖 (分頁)",
    description="""
使用 cursor-based 分頁來獲取地圖列表。

- **next_id**: 提供上次請求回傳的 `next_cursor` 來獲取下一頁。
- **prev_id**: 提供列表第一項的 ID 來獲取上一頁 (如果有的話)。
- 同時提供 `prev_id` 和 `next_id` 是不合法的。
""",
)
def get_map_list(
    prev_id: Optional[int] = Query(None),
    next_id: Optional[int] = Query(None, description="從此 ID 之後的項目"),
    limit: int = Query(20, ge=1, le=100, description="每頁項目數"),
    db: Session = Depends(get_db),
):
    if prev_id is not None and next_id is not None:
        raise HTTPException(status_code=400, detail="prev_id 和 next_id 不能同時提供")

    direction = "prev" if prev_id is not None else "next"
    cursor = prev_id if prev_id is not None else next_id

    maps, next_cursor, prev_cursor, has_more = fetch_maps(
        db, cursor, limit, direction)

    return ListMapsResponse(
        next_cursor=next_cursor,
        prev_cursor=prev_cursor,
        map_list=[
            MapData(
                map_id=m.id,
                name=m.name,
                description=m.description,
            )
            for m in maps
        ],
    )


@router.post(
    "/",
    status_code=201,
    summary="建立新地圖",
    description="批量建立一或多個新地圖。",
    response_model=CreateMapResponse,
)
def create_map(data: CreateMapRequest, db: Session = Depends(get_db)):
    try:
        created = create_maps_service(db=db, map_datas=data.map_datas)
        db.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    created_maps = [CreatedMapInfo(id=c.id, name=c.name) for c in created]
    return CreateMapResponse(message="Maps created successfully", created_maps=created_maps)


@router.get(
    "/{map_id}",
    response_model=MapOut,
    summary="取得單一地圖詳細資訊",
    description="根據地圖 ID 獲取其詳細資料，包含相鄰的地圖及其連線狀態與事件。",  # 擴充說明
    responses={404: {"description": "找不到指定 ID 的地圖"}},
)
def get_map_details(map_id: int, db: Session = Depends(get_db)):
    map_obj = get_map_by_id(db=db, map_id=map_id)
    if not map_obj:
        raise HTTPException(status_code=404, detail="Map not found")

    return build_map_out_response(map_obj)


# -------------------------- Map Feature APIs -------------------------- #

@router.patch(
    "/{map_id}/events",
    response_model=List[EventAssociationOut],
    summary="更新地圖的事件關聯",
    description="""
批量更新地圖與事件的關聯。

- **upsert**: 新增或更新事件關聯，包含其出現機率。
- **remove**: 根據 event ID 列表移除關聯。
- **normalize**: 如果設為 `true`，操作完成後會將所有剩餘事件的機率總和正規化為 1。
""",
    responses={
        404: {"description": "找不到指定 ID 的地圖"},
        400: {"description": "請求無效 (例如：事件 ID 不存在、upsert 和 remove 中有重複的 ID)"},
    },
)
def update_map_events(
    map_id: int,
    payload: EventAssociationsUpdate,
    session: Session = Depends(get_db),
):
    try:
        dto_list = update_map_event_associations(
            db=session,
            map_id=map_id,
            upsert=[{"event_id": e.event_id, "probability": e.probability}
                    for e in (payload.upsert or [])],
            remove=payload.remove,
            normalize=payload.normalize or False,
        )
        session.commit()
    except ValueError as ve:
        raise HTTPException(
            status_code=404 if "not found" in str(ve).lower() else 400,
            detail=str(ve),
        )
    except RuntimeError as re:
        raise HTTPException(status_code=400, detail=str(re))

    return [
        EventAssociationOut(
            event_id=d.event_id,
            event_name=d.event_name,
            probability=d.probability,
        )
        for d in dto_list
    ]


@router.patch(
    "/{map_id}",
    response_model=MapOut,
    summary="更新地圖基本屬性",
    description="""
只更新地圖的基本屬性：名稱 / 敘述 / 圖片 URL，不處理鄰居連線。
""",
    responses={
        404: {"description": "找不到指定 ID 的地圖"},
        400: {"description": "更新失敗 (例如違反資料完整性)"},
    },
)
def patch_map_basic(
    map_id: int,
    payload: MapUpdate,
    session: Session = Depends(get_db),
):
    try:
        map_obj = patch_map_basic_service(
            db=session,
            map_id=map_id,
            name=payload.name,
            description=payload.description,
            image_url=payload.image_url,
        )
        session.commit()
    except ValueError:
        raise HTTPException(status_code=404, detail="Map not found")
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return build_map_out_response(map_obj)


@router.patch(
    "/{map_id}/connections",
    response_model=List[MapNeighborOut],
    summary="更新地圖鄰居連線（新增/修改/移除）",
    description="""
針對某張地圖的鄰居連線做 upsert 或移除。  
- **connections**: 新增或更新無方向連線（含條件）。  
- **remove_connections**: 移除指定 neighbor 的連線。
""",
    responses={
        404: {"description": "找不到指定 ID 的地圖"},
        400: {"description": "連線操作失敗（例如 neighbor 不存在）"},
    },
)
def patch_map_connections(
    map_id: int,
    payload: ConnectionsUpdate,
    session: Session = Depends(get_db),
):
    try:
        patch_map_connections_service(
            db=session,
            map_id=map_id,
            connections=[c.model_dump() for c in (payload.connections or [])],
            remove_connections=payload.remove_connections,
        )
        session.commit()
    except ValueError as ve:
        detail = str(ve)
        status = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status, detail=detail)
    except RuntimeError as re:
        raise HTTPException(status_code=400, detail=str(re))

    map_obj = get_map_by_id(db=session, map_id=map_id)
    if not map_obj:
        raise HTTPException(
            status_code=404, detail="Map not found after update")

    neighbors_out: List[MapNeighborOut] = []
    for conn in map_obj.connections_a:
        neighbors_out.append(
            MapNeighborOut.model_validate(
                conn.map_b, context={"connection": conn})
        )
    for conn in map_obj.connections_b:
        neighbors_out.append(
            MapNeighborOut.model_validate(
                conn.map_a, context={"connection": conn})
        )

    return neighbors_out


@router.delete(
    "/{map_id}",
    status_code=200,
    summary="刪除地圖",
    description="根據 ID 刪除一個地圖。此操作會一併刪除所有與此地圖相關的連線。",
    response_model=MessageResponse,
    responses={404: {"description": "找不到指定 ID 的地圖"}},
)
def remove_map(map_id: int, db: Session = Depends(get_db)):
    if not delete_map_service(db=db, map_id=map_id):
        raise HTTPException(status_code=404, detail="Map not found")
    db.commit()
    return MessageResponse(message="Map removed successfully")


# ---------------------- Helper Functions ---------------------- #


def build_map_out_response(map_obj: Map) -> MapOut:
    """
    Helper to build the MapOut response model from a Map ORM object.
    """
    neighbors_out: List[MapNeighborOut] = []
    for conn in map_obj.connections_a:
        neighbor_map = conn.map_b
        neighbors_out.append(
            MapNeighborOut(
                id=neighbor_map.id,
                name=neighbor_map.name,
                is_locked=conn.is_locked,
                required_item=conn.required_item,
                required_level=conn.required_level,
            )
        )
    for conn in map_obj.connections_b:
        neighbor_map = conn.map_a
        neighbors_out.append(
            MapNeighborOut(
                id=neighbor_map.id,
                name=neighbor_map.name,
                is_locked=conn.is_locked,
                required_item=conn.required_item,
                required_level=conn.required_level,
            )
        )

    events_out: List[EventAssociationOut] = []
    for assoc in map_obj.event_associations:
        events_out.append(
            EventAssociationOut(
                event_id=assoc.event.id,
                event_name=assoc.event.name,
                probability=assoc.probability,
            )
        )

    return MapOut(
        id=map_obj.id,
        name=map_obj.name,
        description=map_obj.description,
        image_url=map_obj.image_url,
        neighbors=neighbors_out,
        events=events_out,
    )


# for test

@router.post("/map-areas", summary="新增一筆地區")
def create_map_area(map_area: MapAreaCreate, db: Session = Depends(get_db)):
    new_area = MapArea(
        map_id=map_area.map_id,
        name=map_area.name,
        description=map_area.description,
        image_url=map_area.image_url
    )
    db.add(new_area)
    try:
        db.commit()
        db.refresh(new_area)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "地區新增成功", "id": new_area.id}


@router.patch(
    "/maps/{map_id}/areas/{area_id}/events",
    response_model=List[EventAssociationOut],
    summary="更新地圖區域的事件關聯",
    description="""
批量更新指定地圖區域的事件關聯。

- **upsert**: 新增或更新事件關聯，包含其出現機率。
- **remove**: 根據 event ID 列表移除關聯。
- **normalize**: 如果設為 `true`，操作完成後會將所有剩餘事件的機率總和正規化為 1。
""",
    responses={
        404: {"description": "找不到指定 ID 的地圖或地圖區域"},
        400: {"description": "請求無效 (例如：事件 ID 不存在、upsert 和 remove 中有重複的 ID)"},
    },
)
def update_map_area_events(
    map_id: int,
    area_id: int,
    payload: EventAssociationsUpdate,
    session: Session = Depends(get_db),
):
    try:
        dto_list = update_map_area_event_associations(
            db=session,
            map_id=map_id,
            area_id=area_id,
            upsert=[{"event_id": e.event_id, "probability": e.probability}
                    for e in (payload.upsert or [])],
            remove=payload.remove,
            normalize=payload.normalize or False,
        )
        session.commit()
    except ValueError as ve:
        raise HTTPException(
            status_code=404 if "not found" in str(ve).lower() else 400,
            detail=str(ve),
        )
    except RuntimeError as re:
        raise HTTPException(status_code=400, detail=str(re))

    return [
        EventAssociationOut(
            event_id=d.event_id,
            event_name=d.event_name,
            probability=d.probability,
        )
        for d in dto_list
    ]


def build_map_area_out_response(area: MapArea) -> MapAreaOut:
    # 轉換 init_npc JSON list 為 List[NPCInfo]
    init_npc_list = []
    if area.init_npc:
        for npc in area.init_npc:
            init_npc_list.append(NPCInfo(**npc))

    # 轉換事件關聯
    events = []
    for assoc in area.event_associations:
        events.append(EventAssociationOut(
            event_id=assoc.event.id,
            event_name=assoc.event.name,
            probability=assoc.probability,
        ))

    return MapAreaOut(
        id=area.id,
        map_id=area.map_id,
        name=area.name,
        description=area.description,
        image_url=area.image_url,
        init_npc=init_npc_list or None,
        event_associations=events,
    )


@router.patch(
    "/maps/{map_id}/areas/{area_id}",
    response_model=MapAreaOut,  # 你要自行定義 Pydantic 輸出模型
    summary="更新地圖區域基本屬性",
    description="""
只更新地圖區域的基本屬性：名稱 / 敘述 / 圖片 URL。
""",
    responses={
        404: {"description": "找不到指定 ID 的地圖或地圖區域"},
        400: {"description": "更新失敗 (例如違反資料完整性)"},
    },
)
def patch_map_area_basic(
    map_id: int,
    area_id: int,
    payload: MapAreaUpdate,  # 你要定義 MapAreaUpdate Pydantic 模型，包含 name, description, image_url
    session: Session = Depends(get_db),
):
    try:
        map_area_obj = patch_map_area_basic_service(
            db=session,
            map_id=map_id,
            area_id=area_id,
            name=payload.name,
            description=payload.description,
            image_url=payload.image_url,
        )
        session.commit()
    except ValueError:
        raise HTTPException(status_code=404, detail="Map or MapArea not found")
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return build_map_area_out_response(map_area_obj)


@router.delete(
    "/maps/{map_id}/areas/{area_id}",
    status_code=200,
    summary="刪除地圖區域",
    description="根據 map_id 與 area_id 刪除一個地圖區域。此操作會一併刪除所有與此區域相關的事件等關聯資料。",
    response_model=MessageResponse,
    responses={404: {"description": "找不到指定 ID 的地圖或地圖區域"}},
)
def remove_map_area(map_id: int, area_id: int, db: Session = Depends(get_db)):
    if not delete_map_area_service(db=db, map_id=map_id, area_id=area_id):
        raise HTTPException(status_code=404, detail="Map or MapArea not found")
    db.commit()
    return MessageResponse(message="MapArea removed successfully")
