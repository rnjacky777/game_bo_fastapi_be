import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from core_system.models.database import Base, engine
from routers import (
    char_temp_route,
    eventO,
    itemO,
    loginO,
    mapO,
    monsterO,
    monsterRewardO,
    userO,
)
import logging
load_dotenv()
# 設定 root logger
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = FastAPI(title="Modular FastAPI Project",
              openapi_version="3.1.0",
              root_path="/bo_api")
origins = os.getenv("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],             # 可允許的來源
    allow_credentials=True,           # 是否允許攜帶 cookie
    # 允許所有 HTTP 方法 (GET, POST, PUT, DELETE...)
    allow_methods=["*"],
    allow_headers=["*"],              # 允許所有 headers
)
if os.getenv("INIT_DB", "false").lower() == "true":
    Base.metadata.create_all(bind=engine)

# 將不同路由模組註冊到主應用
app.include_router(loginO.router)
app.include_router(userO.router)
app.include_router(monsterO.router)
app.include_router(monsterRewardO.router)
app.include_router(itemO.router)
app.include_router(eventO.router)
app.include_router(mapO.router)
app.include_router(char_temp_route.router)

# BO
# app.include_router(router=users.router,prefix="/admin/users")
