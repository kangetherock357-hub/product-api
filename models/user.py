from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True)
    hashed_password: str
    full_name: str
    role: str = Field(default="staff")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserCreate(SQLModel):
    username: str
    email: str
    password: str
    full_name: str
    role: str = "staff"


class UserResponse(SQLModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
