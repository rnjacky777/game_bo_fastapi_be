import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from core_system.models.database import Base, engine
from routers import loginO
from routers import userO
from routers import monsterO, itemO, monsterRewardO, eventO, mapO
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
app.include_router(router=loginO.router, prefix="/auth")
app.include_router(router=userO.router, prefix="/user")
app.include_router(router=monsterO.router, prefix="/monster")
app.include_router(router=monsterRewardO.router,
                   prefix="/monster_reward")
app.include_router(router=itemO.router, prefix="/item")
app.include_router(router=eventO.router, prefix="/event")
app.include_router(router=mapO.router, prefix="")


# BO
# app.include_router(router=users.router,prefix="/admin/users")
