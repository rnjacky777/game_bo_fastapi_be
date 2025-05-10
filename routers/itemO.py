from fastapi import Query
from typing import List, Optional
from services.item_service import fetch_items, get_item_by_id
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import Item
from dependencies.db import get_db
from models.items import RewardPoolItem
from schemas.item import AddItemRequest, EditItemRequest, GetItemDetailResponse, ItemListSchema, ItemSchema
import logging


router = APIRouter()


@router.get("/list_items", response_model=ItemListSchema)
def get_list_items(
    prev_id: Optional[int] = Query(None),
    next_id: Optional[int] = Query(None, description="從此 ID 之後的項目"),
    item_type: Optional[str] = Query(None, description="項目類型"),
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
    items = fetch_items(db, item_type, started_id, fetch_limit, direction)

    # 判斷是否還有更多資料
    has_more = len(items) == fetch_limit

    # 若有更多資料，移除額外多取的項目
    if has_more:
        items.pop()

    # 如果資料少於 limit，表示沒有更多資料，last_id 設為 None
    if not prev_id and not has_more:
        last_id = None
    else:
        last_id = items[-1].id

    return ItemListSchema(
        last_id=last_id,  # 返回最後一筆資料的 ID
        item_data=[  # 返回項目資料
            ItemSchema(
                item_id=item.id,
                item_type=item.item_type,
                name=item.name,
                description=item.description
            )
            for item in items
        ]
    )


@router.get("/{item_id}", response_model=ItemSchema)
def get_item(
    item_id: int,
    db: Session = Depends(get_db)
):
    item = get_item_by_id(db=db, item_id=item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return ItemSchema(
        item_id=item.id,
        item_type=item.item_type,
        name=item.name,
        description=item.description
    )


@router.get("/item_detail/{item_id}", response_model=GetItemDetailResponse)
def get_item_detail(item_id: int, db: Session = Depends(get_db)):
    item = get_item_by_id(db=db, item_id=item_id)
    logging.info(f"Item data: {type(item)}")
    return GetItemDetailResponse.model_validate(item)


@router.delete("/RemoveItem")
def remove_item(item_id: int = Query(...), db: Session = Depends(get_db)):
    db.query(RewardPoolItem).filter(RewardPoolItem.item_id == item_id).delete()
    db.commit()
    db.query(Item).filter(Item.id == item_id).delete()
    db.commit()
    return {"message": "success"}


@router.post("/AddItem")
def add_item(data: List[AddItemRequest], db: Session = Depends(get_db)):
    for item in data:
        drop = Item(**item.model_dump(by_alias=True))
        db.add(drop)
        db.commit()
    db.refresh(drop)
    return {"message": "success"}


@router.put("/edit_item/{item_id}")
def edit_item(item_id: int, data: EditItemRequest, db: Session = Depends(get_db)):
    logging.info(item_id)
    item = get_item_by_id(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # 將 data 的值更新到 item 上
    update_data = data.model_dump()
    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)

    return {"message": "Item updated successfully", "item_id": item.id}
