import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from database.session import get_session
from main import app

TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture
def client():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

    # Reset database schema before running tests
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    yield TestClient(app)
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def test_user():
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123",
        "full_name": "Test User",
    }


@pytest.fixture
def auth_headers(client, test_user):
    client.post("/register", json=test_user)
    res = client.post(
        "/login",
        data={"username": test_user["username"], "password": test_user["password"]},
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
