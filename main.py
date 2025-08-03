from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core_system.models.database import Base, engine
from routers import loginO
from routers import userO
from routers import monsterO, itemO, monsterRewardO, eventO,mapO
import logging

# 設定 root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = FastAPI(title="Modular FastAPI Project")

origins = [
    "http://localhost",  # Vite React 開發環境
    "http://127.0.0.1",  # 有時瀏覽器會用 127.0.0.1
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],             # 可允許的來源
    allow_credentials=True,           # 是否允許攜帶 cookie
    # 允許所有 HTTP 方法 (GET, POST, PUT, DELETE...)
    allow_methods=["*"],
    allow_headers=["*"],              # 允許所有 headers
)
Base.metadata.create_all(bind=engine)
# 將不同路由模組註冊到主應用
app.include_router(router=loginO.router, prefix="/bo_api/auth")
app.include_router(router=userO.router, prefix="/bo_api/user")
app.include_router(router=monsterO.router, prefix="/bo_api/monster")
app.include_router(router=monsterRewardO.router,
                   prefix="/bo_api/monster_reward")
app.include_router(router=itemO.router, prefix="/bo_api/item")
app.include_router(router=eventO.router, prefix="/bo_api/event")
app.include_router(router=mapO.router, prefix="/bo_api")


# BO
# app.include_router(router=users.router,prefix="/admin/users")
