import logging
from typing import Optional
from sqlalchemy.exc import IntegrityError
from core_system.services.char_temp_service import create_char_temp, delete_char_temp, fetch_char_temps, get_char_temp, update_char_temp
from schemas.char_temp import CharTempCreate, CharTempData, CharTempResponse, CharTempUpdate, ListCharTempResponse
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from dependencies.db import get_db

router = APIRouter(
    prefix="/char-templates",
    tags=["Character Templates"]
)


@router.post("/", response_model=CharTempResponse, status_code=status.HTTP_201_CREATED)
def create_char_template(char_data: CharTempCreate, db: Session = Depends(get_db)):
    """
    建立一個新的角色模板。

    這個端點允許使用其基本屬性來建立新的角色模板。
    建議為每個模板提供唯一的名稱，以避免資料庫衝突。
    """
    try:
        char = create_char_temp(db, char_data)
        db.commit()
        return char
    except IntegrityError:
        db.rollback()
        # 如果違反了唯一性約束（例如，已存在同名的角色模板），通常會發生此錯誤。
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"具有所提供詳細資訊（例如名稱 '{char_data.name}'）的角色模板可能已存在。"
        )
    except Exception:
        db.rollback()
        # 為了安全起見，捕獲任何其他意外錯誤並回傳通用的伺服器錯誤。
        # 在生產環境中，您應該在此處記錄錯誤。
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="建立角色模板時發生意外錯誤。"
        )


@router.get("/", response_model=ListCharTempResponse)
def list_char_templates(
    prev_id: Optional[int] = Query(None),
    next_id: Optional[int] = Query(None, description="從此 ID 之後的項目"),
    limit: int = Query(20, ge=1, le=100, description="每頁項目數"),
    db: Session = Depends(get_db)
):
    direction = "prev" if prev_id else "next"
    started_id = prev_id if prev_id else next_id
    fetch_limit = limit + 1

    chars = fetch_char_temps(db, started_id, fetch_limit, direction)
    has_more = len(chars) == fetch_limit

    if has_more:
        chars.pop()

    if chars:
        char_ids = [char.id for char in chars]
        logging.debug(
            f"Fetched character template IDs for the response: {char_ids}")
    else:
        logging.debug(
            "No character templates to return for the given criteria.")

    last_id = chars[-1].id if len(chars) >= limit else None

    return ListCharTempResponse(
        last_id=last_id,
        char_temp_list=[
            CharTempData(
                id=char.id,
                name=char.name,
                rarity=char.rarity,  # 如果有這些欄位
            ) for char in chars
        ],
        # has_more = has_more
    )


@router.get("/{char_id}", response_model=CharTempResponse)
def get_char_template(char_id: int, db: Session = Depends(get_db)):
    char = get_char_temp(db, char_id)
    if not char:
        raise HTTPException(status_code=404, detail="角色模板不存在")
    return char


@router.put("/{char_id}", response_model=CharTempResponse)
def update_char_template(char_id: int, char_data: CharTempUpdate, db: Session = Depends(get_db)):
    char = update_char_temp(db, char_id, char_data)
    if not char:
        raise HTTPException(status_code=404, detail="角色模板不存在")
    try:
        db.commit()
        db.refresh(char)
        return char
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="更新失敗")


@router.delete("/{char_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_char_template(char_id: int, db: Session = Depends(get_db)):
    char = delete_char_temp(db, char_id)
    if not char:
        raise HTTPException(status_code=404, detail="角色模板不存在")
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="刪除失敗")
