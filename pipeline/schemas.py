"""
schemas.py
Pydantic схеми для Data Contract та валідації якості даних (Data Quality Gate).
Кожен парфум повинен пройти сувору перевірку перед записом у базу даних.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class RawFragranceInput(BaseModel):
    """Вхідна схема продукту з парсера / API брендів."""
    id: str = Field(..., min_length=2, description="Унікальний ідентифікатор парфуму")
    name: str = Field(..., min_length=2, description="Назва парфуму")
    brand_name: str = Field(..., min_length=2, description="Назва бренду")
    brand_id: Optional[str] = None
    gender: Optional[str] = "unisex"
    concentration: Optional[str] = "EDP"
    top_notes: List[str] = Field(default_factory=list)
    heart_notes: List[str] = Field(default_factory=list)
    base_notes: List[str] = Field(default_factory=list)
    declared_family: Optional[str] = None
    price_uah: Optional[float] = None
    product_sku: Optional[str] = None
    product_url: Optional[str] = None
    image_url: Optional[str] = None

    @field_validator("name", "brand_name")
    def strip_whitespace(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Поле не може бути порожнім")
        return clean


class ValidatedFragrance(BaseModel):
    """Схема валідованого парфуму після проходження Data Quality Gate та класифікації."""
    id: str
    brand_id: str
    brand_name: str
    name: str
    gender: str
    concentration: str
    primary_subfamily_id: str
    family_code: str
    top_notes: List[str]
    heart_notes: List[str]
    base_notes: List[str]
    price_uah: Optional[float] = None
    product_sku: Optional[str] = None
    product_url: Optional[str] = None
    image_url: Optional[str] = None
