import re
from datetime import UTC, datetime

from pydantic import field_validator
from sqlmodel import Field, Relationship, SQLModel

# ==========================================
# Database Models (table=True)
# ==========================================


class Category(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, min_length=2, max_length=50)
    description: str | None = Field(default=None, max_length=200)

    # Relationships
    products: list[Product] = Relationship(back_populates="category")


class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, min_length=2, max_length=100)
    description: str = Field(min_length=10, max_length=500)
    price: float = Field(gt=0)
    stock: int = Field(ge=0, default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Foreign Keys & Relationships
    category_id: int | None = Field(default=None, foreign_key="category.id")
    category: Category | None = Relationship(back_populates="products")


# ==========================================
# Request / Response Schemas (DTOs)
# ==========================================


class ProductCreate(SQLModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=10, max_length=500)
    price: float = Field(gt=0, le=1000000)
    stock: int = Field(ge=0, le=10000)
    category_id: int | None = None

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
    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = Field(None, min_length=10, max_length=500)
    price: float | None = Field(None, gt=0)
    stock: int | None = Field(None, ge=0)


class CategoryCreate(SQLModel):
    name: str = Field(min_length=2, max_length=50)
    description: str | None = Field(None, max_length=200)
