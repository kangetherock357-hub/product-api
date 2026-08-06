from datetime import datetime, timezone
import re
from typing import List, Optional

from pydantic import field_validator
from sqlmodel import Field, Relationship, SQLModel


# ==========================================
# Database Models (table=True)
# ==========================================

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, min_length=2, max_length=50)
    description: Optional[str] = Field(default=None, max_length=200)

    # Relationships
    products: List["Product"] = Relationship(back_populates="category")


class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, min_length=2, max_length=100)
    description: str = Field(min_length=10, max_length=500)
    price: float = Field(gt=0)
    stock: int = Field(ge=0, default=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Foreign Keys & Relationships
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    category: Optional[Category] = Relationship(back_populates="products")


# ==========================================
# Request / Response Schemas (DTOs)
# ==========================================

class ProductCreate(SQLModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=10, max_length=500)
    price: float = Field(gt=0, le=1000000)
    stock: int = Field(ge=0, le=10000)
    category_id: Optional[int] = None

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty or whitespace")
        if not v[0].isupper():
            raise ValueError("Name must start with a capital letter")
        if re.search(r"[^a-zA-Z0-9\s]", v):
            raise ValueError("Name cannot contain special characters")
        return v

    @field_validator("price")
    def validate_price(cls, v: float) -> float:
        if 0 < v < 1:
            raise ValueError("Price must be at least 1")
        return round(v, 2)


class ProductUpdate(SQLModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, min_length=10, max_length=500)
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)


class CategoryCreate(SQLModel):
    name: str = Field(min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=200)