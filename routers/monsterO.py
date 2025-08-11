import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from core_system.models.monsters import Monster
from dependencies.db import get_db
from schemas.monster import AddMonsterRequest, EditMonsterRequest, GetMonsterDetailResponse, MonsterListSchema, MonsterSchema
from core_system.services.monster_service import fetch_monsters, get_monster_by_id
from core_system.services.reward_pool_service import add_reward_pool, remove_reward_pool

router = APIRouter(
    prefix="/monsters",
    tags=["Monsters"]
)


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


@router.get("/list_monster", response_model=MonsterListSchema)
def get_list_monsters(
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
    monsters = fetch_monsters(db, started_id, fetch_limit, direction)

    # 判斷是否還有更多資料
    has_more = len(monsters) == fetch_limit

    # 若有更多資料，移除額外多取的項目
    if has_more:
        monsters.pop()

    # 如果資料少於 limit，表示沒有更多資料，last_id 設為 None
    if not prev_id and not has_more:
        last_id = None
    else:
        last_id = monsters[-1].id

    return MonsterListSchema(
        last_id=last_id,  # 返回最後一筆資料的 ID
        monster_data=[  # 返回項目資料
            MonsterSchema(
                monster_id=monster.id,
                name=monster.name,
                drop_pool_ids=monster.drop_pool_id
            )
            for monster in monsters
        ]
    )


@router.get("/{monster_id}", response_model=MonsterSchema)
def get_monster(
    monster_id: int,
    db: Session = Depends(get_db)
):
    monster = get_monster_by_id(db=db, monster_id=monster_id)
    if not monster:
        raise HTTPException(status_code=404, detail="monster not found")

    return MonsterSchema(
        monster_id=monster.id,
        name=monster.name,
        drop_pool_ids=monster.drop_pool_id
    )


@router.get("/monster_detail/{monster_id}", response_model=GetMonsterDetailResponse)
def get_monster_detail(monster_id: int, db: Session = Depends(get_db)):
    monster = get_monster_by_id(db=db, monster_id=monster_id)
    logging.info(monster.drop_pool_id)
    a = GetMonsterDetailResponse.model_validate(monster)
    logging.info(a.drop_pool_id)

    return GetMonsterDetailResponse.model_validate(monster)


@router.put("/edit_monster/{monster_id}")
def edit_monster(monster_id: int, data: EditMonsterRequest, db: Session = Depends(get_db)):
    monster = get_monster_by_id(db, monster_id)
    if not monster:
        raise HTTPException(status_code=404, detail="Monster not found")

    # 將 data 的值更新到 item 上
    update_data = data.model_dump()
    for key, value in update_data.items():
        setattr(monster, key, value)

    db.commit()
    db.refresh(monster)

    return {"message": "Monster updated successfully", "monster_id": monster.id}


@router.post("/AddMonster")
def add_monster(data: AddMonsterRequest, db: Session = Depends(get_db)):
    for monster in data.monster_data:
        if data.auto_add_reward_pool:
            monster.drop_pool_id = add_reward_pool(
                db=db, name=f'{monster.name}_pool')
        drop = Monster(**monster.model_dump(by_alias=True))
        db.add(drop)
        db.commit()
    db.refresh(drop)
    return {"message": "success"}


@router.delete("/RemoveMonster/{monster_id}")
def remove_monster(monster_id: int, delete_pool: bool=Query(default=False), db: Session = Depends(get_db)):
    monster = get_monster_by_id(db=db, monster_id=monster_id)
    if delete_pool and monster.drop_pool_id:
        remove_reward_pool(db=db,pool_id=monster.drop_pool_id)

    if monster:
        db.delete(monster)
        db.commit()
        return {"message": "success"}
    return {"message": "Failed"}
