from pydantic import BaseModel, Field
class MonsterRewardSchema(BaseModel):
    drop_id: int
    item_id: int
    probability: float

    # 使用 alias 來自動對應 `item_name`
    item_name: str = Field(alias="item_name")  # 在 Pydantic 中設置別名

    class Config:
        from_attributes = True

    # @property
    # def item_name(self):
    #     # 這裡返回 `item.name`，使得 item_name 欄位顯示為對應的 `Item` 名稱
    #     return self.item.name if self.item else ""