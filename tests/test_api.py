"""Integration tests for Flask API endpoints."""

import json
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


ADT_VALID = (
    "MSH|^~\\&|ADMIT_SYS|CITY_HOSP|HIS|OPTUM|20260418120000||ADT^A01|"
    "APITEST001|P|2.5\r"
    "EVN|A01|20260418120000\r"
    "PID|1||PAT999||Smith^Jane||19900101|F\r"
    "PV1|1|I|WARD1"
)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "healthy"


def test_parse_valid_message(client):
    r = client.post(
        "/api/hl7/parse",
        data=json.dumps({"message": ADT_VALID}),
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert data["message_type"] == "ADT^A01"
    assert data["ack_code"] == "AA"
    assert "MSA|AA" in data["ack_message"]


def test_parse_missing_body(client):
    r = client.post(
        "/api/hl7/parse",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert r.status_code == 400


def test_validate_only(client):
    r = client.post(
        "/api/hl7/validate",
        data=json.dumps({"message": ADT_VALID}),
        content_type="application/json",
    )
    assert r.status_code == 200
    assert r.get_json()["valid"] is True


def test_list_messages(client):
    client.post(
        "/api/hl7/parse",
        data=json.dumps({"message": ADT_VALID}),
        content_type="application/json",
    )
    r = client.get("/api/hl7/messages")
    assert r.status_code == 200
    data = r.get_json()
    assert "messages" in data
    assert data["count"] >= 1


def test_stats(client):
    r = client.get("/api/hl7/stats")
    assert r.status_code == 200
    assert "total" in r.get_json()