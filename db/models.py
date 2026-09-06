"""
models.py
SQLAlchemy моделі для сутностей Колеса Ароматів, парфумерного каталогу та кешу метчингу.
Сумісні як з SQLite, так і з PostgreSQL.
"""

from datetime import datetime
from typing import List
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class WheelFamilyModel(Base):
    __tablename__ = "wheel_families"

    code = Column(String(20), primary_key=True)
    name_uk = Column(String(100), nullable=False)
    name_en = Column(String(100), nullable=False)
    color_hex = Column(String(7), nullable=False)
    profile = Column(Text, nullable=True)

    subfamilies = relationship("WheelSubfamilyModel", back_populates="family")


class WheelSubfamilyModel(Base):
    __tablename__ = "wheel_subfamilies"

    id = Column(String(50), primary_key=True)
    ring_index = Column(Integer, unique=True, nullable=False)
    family_code = Column(String(20), ForeignKey("wheel_families.code"), nullable=False)
    name_uk = Column(String(100), nullable=False)
    name_en = Column(String(100), nullable=False)
    color_hex = Column(String(7), nullable=False)
    profile = Column(Text, nullable=True)
    key_ingredients = Column(JSON, default=list)  # Список нот

    family = relationship("WheelFamilyModel", back_populates="subfamilies")
    fragrances = relationship("FragranceModel", back_populates="subfamily")


class BrandModel(Base):
    __tablename__ = "brands"

    id = Column(String(50), primary_key=True)
    name = Column(String(150), nullable=False)
    country = Column(String(100), nullable=True)
    is_niche = Column(Boolean, default=False)

    fragrances = relationship("FragranceModel", back_populates="brand")


class FragranceModel(Base):
    __tablename__ = "fragrances"

    id = Column(String(100), primary_key=True)
    brand_id = Column(String(50), ForeignKey("brands.id"), nullable=False)
    name = Column(String(255), nullable=False)
    gender = Column(String(30), default="unisex")
    concentration = Column(String(50), nullable=True)
    primary_subfamily_id = Column(String(50), ForeignKey("wheel_subfamilies.id"), nullable=False)

    # Ольфакторна піраміда
    top_notes = Column(JSON, default=list)
    heart_notes = Column(JSON, default=list)
    base_notes = Column(JSON, default=list)

    price_uah = Column(Float, nullable=True)
    product_sku = Column(String(100), nullable=True)
    product_url = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    brand = relationship("BrandModel", back_populates="fragrances")
    subfamily = relationship("WheelSubfamilyModel", back_populates="fragrances")

    def to_dict(self):
        return {
            "id": self.id,
            "brand_id": self.brand_id,
            "brand_name": self.brand.name if self.brand else self.brand_id,
            "name": self.name,
            "gender": self.gender,
            "concentration": self.concentration,
            "primary_subfamily_id": self.primary_subfamily_id,
            "family_code": self.subfamily.family_code if self.subfamily else None,
            "top_notes": self.top_notes or [],
            "heart_notes": self.heart_notes or [],
            "base_notes": self.base_notes or [],
            "price_uah": self.price_uah,
            "product_sku": self.product_sku,
            "product_url": self.product_url,
            "image_url": self.image_url
        }


class RecommendationCacheModel(Base):
    __tablename__ = "recommendation_cache"

    source_fragrance_id = Column(String(100), ForeignKey("fragrances.id", ondelete="CASCADE"), primary_key=True)
    target_fragrance_id = Column(String(100), ForeignKey("fragrances.id", ondelete="CASCADE"), primary_key=True)
    match_type = Column(String(20), nullable=False)  # exact, adjacent, complementary
    ring_distance = Column(Integer, nullable=False)
    similarity_score = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)
