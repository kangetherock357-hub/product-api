import os

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

# Load environment variables from the .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Echo=True lets us see the generated SQL queries in our terminal (great for development!)
engine = create_engine(DATABASE_URL, echo=True)


def init_db():
    """Create the database tables if they do not exist."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency injection helper to yield database sessions."""
    with Session(engine) as session:
        yield session
