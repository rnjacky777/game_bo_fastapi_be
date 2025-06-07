from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core_system.models import RewardPoolItem, Item
from core_system.models.monsters import Monster
from dependencies.db import get_db
from schemas.monster import AddDropItemSchema, MonsterSchema, RemoveDropItemSchema
from schemas.reward import UpdateDropProbabilitySchema
from schemas.rewarditem import MonsterRewardSchema


router = APIRouter()


@router.get("/rewards/{monster_id}")
def get_monster_rewards(monster_id: int, db: Session = Depends(get_db)):
    monster = db.query(Monster).filter(Monster.id == monster_id).first()
    if not monster or not monster.drop_pool:
        raise HTTPException(
            status_code=404, detail="Monster or reward pool not found")

    rewards = []
    for item in monster.drop_pool.items:
        rewards.append(MonsterRewardSchema(
            drop_id=item.id,
            item_id=item.item_detail.id,
            item_name=item.item_detail.name,
            probability=item.probability
        ))
    return {"monster_id": monster.id, "monster_name": monster.name, "drop_pool": rewards}


@router.put("/probability")
def update_drop_probability(
    data: UpdateDropProbabilitySchema,
    db: Session = Depends(get_db)
):
    monster_id = data.monster_id
    item_id = data.item_id
    # 找到怪物
    monster = db.query(Monster).filter(Monster.id == monster_id).first()
    if not monster:
        raise HTTPException(status_code=404, detail="Monster not found")

    # 確保怪物有掉落池
    if not monster.drop_pool:
        raise HTTPException(
            status_code=400, detail="This monster has no drop pool.")

    # 找到對應的掉落物關聯
    drop = (
        db.query(RewardPoolItem)
        .filter(
            RewardPoolItem.pool_id == monster.drop_pool.id,
            RewardPoolItem.item_id == item_id
        )
        .first()
    )
    if not drop:
        raise HTTPException(
            status_code=404, detail="Drop item not found in this monster's drop pool.")

    # 更新機率
    drop.probability = data.probability
    db.commit()

    return {"message": "Probability updated successfully", "item_id": item_id, "new_probability": data.probability}


@router.post("/addRewardItem")
def add_monster_drop(data: AddDropItemSchema, db: Session = Depends(get_db)):
    monster_id = data.monster_id
    monster = db.query(Monster).filter(Monster.id == monster_id).first()
    if not monster or not monster.drop_pool:
        raise HTTPException(
            status_code=404, detail="Monster or drop pool not found")

    # 確認是否已存在相同 item_id
    exists = db.query(RewardPoolItem).filter(
        RewardPoolItem.pool_id == monster.drop_pool.id,
        RewardPoolItem.item_id == data.item_id
    ).first()
    if exists:
        raise HTTPException(
            status_code=400, detail="Item already exists in drop pool")

    drop = RewardPoolItem(
        pool_id=monster.drop_pool.id,
        item_id=data.item_id,
        probability=data.probability
    )
    db.add(drop)
    db.commit()
    db.refresh(drop)
    item_detail = db.query(Item).filter(Item.id == data.item_id).first()
    return {"message": "Drop item added", "drop_id": drop.id, 'probability': data.probability, 'item_name': item_detail.name, 'item_id': item_detail.id}


@router.delete("/removeRewardItem")
def delete_monster_drop(data: RemoveDropItemSchema, db: Session = Depends(get_db)):
    drop_id = data.drop_id
    data = db.query(RewardPoolItem).filter(
        RewardPoolItem.id == drop_id).first()
    if data:
        db.query(RewardPoolItem).filter(RewardPoolItem.id == drop_id).delete()
        db.commit()
        return {"message": "Drop item deleted"}
    else:
        raise HTTPException(
            status_code=404, detail="drop pool not found")
