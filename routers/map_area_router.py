import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from dependencies.db import get_db
from core_system.models.maps import MapArea
from core_system.services.map_area_service import (
    delete_map_area_service,
    get_area_or_raise,
    patch_map_area_basic_service,
    update_map_area_event_associations,
)
from schemas.common import MessageResponse
from schemas.map import EventAssociationsUpdate

from schemas.map_area import (
    EventAssociationOut,
    MapAreaCreate,
    MapAreaOut,
    MapAreaUpdate,
    NPCInfo,
)

router = APIRouter(prefix="/maps/{map_id}/areas", tags=["Map Areas"])


# ====== Create ======
@router.post(
    "/",
    summary="新增一筆地區",
    response_model=MapAreaOut,
    status_code=status.HTTP_201_CREATED,
)
def create_map_area(
    map_id: int,
    area_data: MapAreaCreate,
    db: Session = Depends(get_db),
):
    """在指定的地圖下建立一個新的地圖區域。"""
    from core_system.services.map_service import create_map_area_service

    try:
        new_area = create_map_area_service(
            db=db,
            map_id=map_id,
            name=area_data.name,
            description=area_data.description,
            image_url=area_data.image_url,
        )
        db.commit()
        db.refresh(new_area)
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A map area with this name may already exist for this map.")

    return build_map_area_out_response(new_area)


# ====== Read ======
@router.get(
    "/{area_id}",
    response_model=MapAreaOut,
    summary="取得單一地圖區域詳細資訊",
    description="根據 map_id 與 area_id 取得地圖區域的詳細資訊，包括初始 NPC 與事件關聯。",
    responses={404: {"description": "找不到指定的地圖或地圖區域"}},
)
def get_map_area_detail(
    map_id: int,
    area_id: int,
    db: Session = Depends(get_db),
):
    try:
        area = get_area_or_raise(db, map_id, area_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="MapArea not found")

    return build_map_area_out_response(area)


# ====== Update ======
@router.patch(
    "/{area_id}/events",
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
        upsert_data = [
            {"event_id": e.event_id, "probability": e.probability}
            for e in (payload.upsert or [])
        ]
        dto_list = update_map_area_event_associations(
            db=session,
            map_id=map_id,
            area_id=area_id,
            upsert=upsert_data,
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
    "/{area_id}",
    response_model=MapAreaOut,
    summary="更新地圖區域基本屬性",
    description="只更新地圖區域的基本屬性：名稱 / 敘述 / 圖片 URL。",
    responses={
        404: {"description": "找不到指定 ID 的地圖或地圖區域"},
        400: {"description": "更新失敗 (例如違反資料完整性)"},
    },
)
def patch_map_area_basic(
    map_id: int,
    area_id: int,
    payload: MapAreaUpdate,
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


# ====== Delete ======
@router.delete(
    "/{area_id}",
    status_code=200,
    summary="刪除地圖區域",
    description="根據 map_id 與 area_id 刪除一個地圖區域。會同時刪除與該區域相關的所有事件等關聯資料。",
    response_model=MessageResponse,
    responses={404: {"description": "找不到指定 ID 的地圖或地圖區域"}},
)
def remove_map_area(
    map_id: int,
    area_id: int,
    db: Session = Depends(get_db),
):
    if not delete_map_area_service(db=db, map_id=map_id, area_id=area_id):
        raise HTTPException(status_code=404, detail="Map or MapArea not found")
    db.commit()
    return MessageResponse(message="MapArea removed successfully")


# ====== Helper ======
def build_map_area_out_response(area: MapArea) -> MapAreaOut:
    """轉換 SQLAlchemy MapArea 實例為 MapAreaOut"""
    init_npc_list = [NPCInfo(**npc) for npc in (area.init_npc or [])]

    events = [
        EventAssociationOut(
            event_id=assoc.event.id,
            event_name=assoc.event.name,
            probability=assoc.probability,
        )
        for assoc in area.event_associations
    ]

    return MapAreaOut(
        id=area.id,
        map_id=area.map_id,
        name=area.name,
        description=area.description,
        image_url=area.image_url,
        init_npc=init_npc_list or None,
        event_associations=events,
    )
