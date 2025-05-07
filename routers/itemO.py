from fastapi import Query
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import Item
from dependencies.db import get_db
from models.items import RewardPoolItem
from schemas.item import AddItemRequest, GetItemDetailRequest, GetItemDetailResponse, ItemSchema
import logging


router = APIRouter()


@router.get("/ListAllItem", response_model=List[ItemSchema])
def get_all_items(db: Session = Depends(get_db)):
    items = db.query(Item).all()
    result = []
    for item in items:
        result.append(ItemSchema(
            id=item.id,
            name=item.name,
        ))
    return result


@router.get("/ListItems", response_model=List[ItemSchema])
def get_items(item_type: str= Query(...), db: Session = Depends(get_db)):
    items = db.query(Item).filter(Item.item_type == item_type)
    result = []
    for item in items:
        result.append(ItemSchema(
            id=item.id,
            name=item.name,
        ))
    return result


@router.get("/ItemDetail", response_model=GetItemDetailResponse)
def get_item_detail(item_id: int = Query(...), db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # 建議使用 model 的 mapper keys 過濾內部欄位
    logging.error(f"Item data: {item}")

    return GetItemDetailResponse.model_validate(item)


@router.delete("/RemoveItem")
def remove_item(item_id: int = Query(...), db: Session = Depends(get_db)):
    db.query(RewardPoolItem).filter(RewardPoolItem.item_id == item_id).delete()
    db.commit()
    db.query(Item).filter(Item.id == item_id).delete()
    db.commit()
    return {"message": "success"}


@router.post("/AddItem")
def add_item(data: AddItemRequest, db: Session = Depends(get_db)):
    drop = Item(**data.model_dump(by_alias=True))
    db.add(drop)
    db.commit()
    db.refresh(drop)
    return {"message": "success"}
