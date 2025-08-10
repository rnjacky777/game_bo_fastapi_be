from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ===================================================================
#   Base & Shared Schemas
# ===================================================================

class CharTempBase(BaseModel):
    """角色模板的基礎欄位，用於繼承。"""
    name: str = Field(..., description="角色模板名稱")
    rarity: int = Field(..., description="稀有度 (例如 1-6 星)")
    description: Optional[str] = Field(None, description="角色介紹")
    image_sm_url: Optional[str] = Field(None, description="角色小圖 URL")
    image_lg_url: Optional[str] = Field(None, description="角色大圖 URL")
    base_hp: int = Field(..., description="基礎生命值")
    base_mp: int = Field(..., description="基礎魔力值")
    base_atk: int = Field(..., description="基礎攻擊力")
    base_spd: int = Field(..., description="基礎速度")
    base_def: int = Field(..., description="基礎防禦力")


# ===================================================================
#   Schemas for API Responses
# ===================================================================

class CharTempData(BaseModel):
    """用於角色模板列表的精簡資料結構。"""
    id: int
    name: str
    rarity: int

    model_config = ConfigDict(from_attributes=True)


class ListCharTempResponse(BaseModel):
    """GET /char-templates/ 的回應模型。"""
    last_id: Optional[int] = None
    char_temp_list: List[CharTempData] = []


class CharTempResponse(CharTempBase):
    """用於單一角色模板查詢、建立、更新的完整回應模型。"""
    id: int
    model_config = ConfigDict(from_attributes=True)


# ===================================================================
#   Schemas for API Requests (Create/Update)
# ===================================================================

class CharTempCreate(CharTempBase):
    """POST /char-templates/ 的請求模型，用於建立新角色模板。"""
    pass


class CharTempInfoUpdate(BaseModel):
    """PATCH /char-templates/info/{id} 的請求模型，用於更新角色一般資訊。"""
    name: Optional[str] = None
    rarity: Optional[int] = None
    description: Optional[str] = None
    image_sm_url: Optional[str] = None
    image_lg_url: Optional[str] = None


class CharTempStatsUpdate(BaseModel):
    """PATCH /char-templates/stats/{id} 的請求模型，用於更新角色基礎數值。"""
    base_hp: Optional[int] = None
    base_mp: Optional[int] = None
    base_atk: Optional[int] = None
    base_spd: Optional[int] = None
    base_def: Optional[int] = None
