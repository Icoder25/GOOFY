from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns service info"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Goofy Backend API"
    assert data["status"] == "running"
    assert "version" in data


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "services" in data
    assert "gemini" in data["services"]


def test_command_parse_screenshot():
    """Test screenshot command parsing."""
    response = client.post(
        "/api/v1/commands/parse",
        json={"transcript": "take a screenshot", "context": None}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["intent"] == "system.screenshot"
    assert data["strategy"] == "regex"


def test_command_parse_volume():
    """Test volume command parsing."""
    response = client.post(
        "/api/v1/commands/parse",
        json={"transcript": "volume up", "context": None}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["intent"] == "system.volume"
    assert data["parameters"]["action"] == "up"


def test_command_parse_open_app():
    """Test open app command parsing."""
    response = client.post(
        "/api/v1/commands/parse",
        json={"transcript": "open notepad", "context": None}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["intent"] == "system.open_app"
    assert "notepad" in data["parameters"]["app_name"].lower()


def test_command_parse_search():
    """Test search command parsing extracts query."""
    response = client.post(
        "/api/v1/commands/parse",
        json={"transcript": "search for weather tomorrow", "context": None}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["intent"] == "search.google"
    assert "weather" in data["parameters"]["query"].lower()


def test_command_parse_type():
    """Test typing command."""
    response = client.post(
        "/api/v1/commands/parse",
        json={"transcript": "type hello world", "context": None}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["intent"] == "system.type"
    assert data["parameters"]["text"] == "hello world"


def test_command_parse_no_match():
    """Unknown commands should fail gracefully."""
    response = client.post(
        "/api/v1/commands/parse",
        json={"transcript": "xyz123abc random text", "context": None}
    )
    assert response.status_code == 200
    data = response.json()
    # Should either be False or fallback to Gemini conversation
    if data["success"]:
        assert data["strategy"] == "gemini"
    else:
        assert data["strategy"] == "none"


def test_summarize_endpoint_exists():
    """Summarize endpoint should exist and handle empty text."""
    response = client.post(
        "/api/v1/commands/summarize",
        json={"text": "", "url": "", "title": ""}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
