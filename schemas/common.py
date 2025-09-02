from pydantic import BaseModel


class MessageResponse(BaseModel):
    """通用的訊息回應模型"""
    message: str