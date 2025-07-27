from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core_system.models.user import User
from core_system.services.auth_service import authenticate_user, AuthenticationError
from dependencies.db import get_db
from dependencies.user import get_current_user
from schemas.login import LoginRequest, Token


router = APIRouter()


@router.post("/login", response_model=Token)
async def login(form_data: LoginRequest, db: Session = Depends(get_db)):
    try:
        access_token = authenticate_user(
            db, form_data.username, form_data.password)
        return {"access_token": access_token, "token_type": "bearer"}
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


