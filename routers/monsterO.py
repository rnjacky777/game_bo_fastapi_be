from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import RewardPoolItem
from models.monsters import Monster
from dependencies.db import get_db
from schemas.monster import AddDropItemSchema, MonsterSchema
from schemas.reward import RewardPoolItemSchema, RewardPoolSchema, UpdateDropProbabilitySchema
from schemas.rewarditem import MonsterRewardSchema  # 你可以建立一個 UserOut schema


router = APIRouter()


@router.get("/ListAllMonsters", response_model=List[MonsterSchema])
def get_monsters(db: Session = Depends(get_db)):
    monsters = db.query(Monster).all()

    # 手動填入 item_name
    result = []
    for m in monsters:
        result.append(MonsterSchema(
            id=m.id,
            name=m.name,
        ))

    return result


@router.get("/rewards/{monster_id}")
def get_monster_rewards(monster_id: int, db: Session = Depends(get_db)):
    monster = db.query(Monster).filter(Monster.id == monster_id).first()
    if not monster or not monster.drop_pool:
        raise HTTPException(
            status_code=404, detail="Monster or reward pool not found")

    rewards = []
    for item in monster.drop_pool.items:
        rewards.append(MonsterRewardSchema(
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


# @router.post("/admin/monsters/{monster_id}/drops")
# def add_monster_drop(monster_id: int, data: AddDropItemSchema, db: Session = Depends(get_db)):
#     monster = db.query(Monster).filter(Monster.id == monster_id).first()
#     if not monster or not monster.drop_pool:
#         raise HTTPException(
#             status_code=404, detail="Monster or drop pool not found")

#     # 確認是否已存在相同 item_id
#     exists = db.query(RewardPoolItem).filter(
#         RewardPoolItem.pool_id == monster.drop_pool.id,
#         RewardPoolItem.item_id == data.item_id
#     ).first()
#     if exists:
#         raise HTTPException(
#             status_code=400, detail="Item already exists in drop pool")

#     drop = RewardPoolItem(
#         pool_id=monster.drop_pool.id,
#         item_id=data.item_id,
#         probability=data.probability
#     )
#     db.add(drop)
#     db.commit()
#     db.refresh(drop)
#     return {"message": "Drop item added", "drop_id": drop.id}


# @router.delete("/admin/monsters/{monster_id}/drops/{item_id}")
# def delete_monster_drop(monster_id: int, item_id: int, db: Session = Depends(get_db)):
#     monster = db.query(Monster).filter(Monster.id == monster_id).first()
#     if not monster or not monster.drop_pool:
#         raise HTTPException(
#             status_code=404, detail="Monster or drop pool not found")

#     drop = db.query(RewardPoolItem).filter(
#         RewardPoolItem.pool_id == monster.drop_pool.id,
#         RewardPoolItem.item_id == item_id
#     ).first()
#     if not drop:
#         raise HTTPException(status_code=404, detail="Drop item not found")

#     db.delete(drop)
#     db.commit()
#     return {"message": "Drop item deleted"}
