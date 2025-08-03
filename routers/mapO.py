import logging
from sqlite3 import IntegrityError
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from core_system.models.association_tables import MapConnection, MapEventAssociation
from core_system.models.event import Event
from core_system.models.maps import Map
from dependencies.db import get_db
from schemas.event import (
    EditEventRequest
)
from schemas.map import CreateMapRequest, EventAssociationOut, EventAssociationsUpdate, ListMapsResponse, MapData, MapNeighborOut, MapOut, MapUpdate
from core_system.services.event_service import (
    edit_event_service
)
from core_system.services.map_service import create_map_service, delete_map_service, fetch_maps, get_map_by_id

router = APIRouter()

# -------------------------- Event APIs -------------------------- #

@router.get("/list-map", response_model=ListMapsResponse)
def get_map_list(
    prev_id: Optional[int] = Query(None),
    next_id: Optional[int] = Query(None, description="從此 ID 之後的項目"),
    limit: int = Query(20, ge=1, le=100, description="每頁項目數"),
    db: Session = Depends(get_db)
):
    direction = "prev" if prev_id else "next"
    started_id = prev_id if prev_id else next_id
    fetch_limit = limit + 1

    maps = fetch_maps(db, started_id, fetch_limit, direction)
    has_more = len(maps) == fetch_limit

    if has_more:
        maps.pop()

    last_id = maps[-1].id if maps else None

    return ListMapsResponse(
        last_id=last_id,
        map_list=[
            MapData(
                map_id=map_item.id,
                name=map_item.name,
                description=map_item.description
            ) for map_item in maps
        ]
    )


@router.get("/{map_id}", response_model=MapData)
def get_map(map_id: int, db: Session = Depends(get_db)):
    map_obj = get_map_by_id(db=db, map_id=map_id)
    if not map_obj:
        raise HTTPException(status_code=404, detail="Map not found")
    return MapData(
        map_id=map_obj.id,
        name=map_obj.name,
        description=map_obj.description
    )


@router.post("/create-map")
def create_map(data: CreateMapRequest, db: Session = Depends(get_db)):
    created_maps = []
    for map_data in data.map_datas:
        new_map = create_map_service(
            db=db,
            name=map_data.name,
            description=map_data.description,
            image_url=map_data.image_url
        )
        created_maps.append({"id": new_map.id, "name": new_map.name})
    db.commit()
    return {"message": "Maps created successfully", "created_maps": created_maps}

@router.patch("/{map_id}/events", response_model=List[EventAssociationOut])
def update_map_events(
    map_id: int,
    payload: EventAssociationsUpdate,
    session: Session = Depends(get_db),
):
    map_obj = session.get(Map, map_id)
    if not map_obj:
        raise HTTPException(status_code=404, detail="Map not found")

    # Upsert
    if payload.upsert:
        for ev in payload.upsert:
            # 驗證 event 存在
            event_obj = session.get(Event, ev.event_id)
            if not event_obj:
                raise HTTPException(status_code=400, detail=f"Event id {ev.event_id} does not exist")
            existing = (
                session.query(MapEventAssociation)
                .filter_by(map_id=map_obj.id, event_id=ev.event_id)
                .one_or_none()
            )
            if existing:
                existing.probability = ev.probability
            else:
                new_assoc = MapEventAssociation(
                    map=map_obj,
                    event=event_obj,
                    probability=ev.probability,
                )
                session.add(new_assoc)

    # Remove
    if payload.remove:
        for eid in payload.remove:
            assoc = (
                session.query(MapEventAssociation)
                .filter_by(map_id=map_obj.id, event_id=eid)
                .one_or_none()
            )
            if assoc:
                session.delete(assoc)

    # Optional normalization: 將所有 probability 總和調整成 1（如果需要）
    if payload.normalize:
        assocs = (
            session.query(MapEventAssociation)
            .filter_by(map_id=map_obj.id)
            .all()
        )
        total = sum(a.probability for a in assocs)
        if total > 0:
            for a in assocs:
                a.probability = a.probability / total

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Failed to update event associations")

    session.refresh(map_obj)

    # 回傳目前的 associations
    out = []
    for assoc in map_obj.event_associations:
        event_obj = assoc.event  # 假設 relationship
        out.append(
            EventAssociationOut(
                event_id=event_obj.id,
                event_name=event_obj.name,
                probability=assoc.probability,
            )
        )
    return out
@router.put("/{map_id}", response_model=MapOut)
def update_map(
    map_id: int,
    payload: MapUpdate,
    session: Session = Depends(get_db),
):
    map_obj = session.get(Map, map_id)
    if not map_obj:
        raise HTTPException(status_code=404, detail="Map not found")

    # 這整段包在 transaction（假設 get_db session 是同一 transaction 直到 commit）
    if payload.name is not None:
        map_obj.name = payload.name
    if payload.description is not None:
        map_obj.description = payload.description
    if payload.image_url is not None:
        map_obj.image_url = payload.image_url

    # 處理新增/更新連線
    if payload.connections:
        for conn_in in payload.connections:
            if conn_in.neighbor_id == map_obj.id:
                continue
            neighbor = session.get(Map, conn_in.neighbor_id)
            if not neighbor:
                raise HTTPException(
                    status_code=400,
                    detail=f"Neighbor map id {conn_in.neighbor_id} does not exist"
                )
            upsert_connection(
                session,
                map_obj,
                neighbor,
                is_locked=conn_in.is_locked,
                required_item=conn_in.required_item,
                required_level=conn_in.required_level,
            )

    # 處理移除連線
    if payload.remove_connections:
        for nid in payload.remove_connections:
            if nid == map_obj.id:
                continue
            neighbor = session.get(Map, nid)
            if neighbor:
                remove_connection(session, map_obj, neighbor)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Failed to update map due to integrity error")

    session.refresh(map_obj)

    # 組出 neighbors response
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

    return MapOut(
        id=map_obj.id,
        name=map_obj.name,
        description=map_obj.description,
        image_url=map_obj.image_url,
        neighbors=neighbors_out,
    )


@router.delete("/{map_id}")
def remove_map(map_id: int, db: Session = Depends(get_db)):
    if not delete_map_service(db=db, map_id=map_id):
        raise HTTPException(status_code=404, detail="Map not found")
    return {"message": "Map removed successfully"}

# ---------------------- Event Result APIs ---------------------- #

def get_ordered_pair(id1: int, id2: int) -> tuple[int, int]:
    return (id1, id2) if id1 < id2 else (id2, id1)

def upsert_connection(session: Session, map_obj: Map, neighbor: Map, **kwargs) -> MapConnection:
    a, b = (map_obj, neighbor) if map_obj.id < neighbor.id else (neighbor, map_obj)
    conn = (
        session.query(MapConnection)
        .filter_by(map_a_id=a.id, map_b_id=b.id)
        .one_or_none()
    )
    if conn is None:
        conn = MapConnection(map_a=a, map_b=b, **kwargs)
        session.add(conn)
    else:
        for key, val in kwargs.items():
            setattr(conn, key, val)
    return conn

def remove_connection(session: Session, map_obj: Map, neighbor: Map):
    a_id, b_id = get_ordered_pair(map_obj.id, neighbor.id)
    conn = (
        session.query(MapConnection)
        .filter_by(map_a_id=a_id, map_b_id=b_id)
        .one_or_none()
    )
    if conn:
        session.delete(conn)