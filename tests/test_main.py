def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "uptime" in data


def test_404_error(client):
    response = client.get("/non-existent-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data  # Adjust if using standard FastAPI exception structure
