"""API endpoint tests - FastAPI."""
import pytest


def test_health(client):
    """Health check returns 200."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register(client):
    """Registration creates user and returns token."""
    r = client.post("/api/auth/register", json={
        "username": "newuser",
        "email": "new@example.com",
        "password": "password123",
    })
    assert r.status_code in (200, 201), f"Got {r.status_code}: {r.json()}"
    data = r.json()
    assert "token" in data
    assert data["user"]["email"] == "new@example.com"


def test_login(client, test_user):
    """Login returns token."""
    r = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "password123",
    })
    assert r.status_code == 200, r.json()
    data = r.json()
    assert "token" in data


def test_login_invalid(client, test_user):
    """Login with wrong password returns 401."""
    r = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "wrongpassword",
    })
    assert r.status_code == 401


def test_me(client, test_user, auth_headers):
    """Get current user with valid token."""
    r = client.get("/api/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["user"]["username"] == "testuser"
    assert "onboarding_completed" in r.json()["user"]


def test_onboarding_complete(client, test_user, auth_headers):
    """Mark onboarding complete updates user."""
    r = client.post("/api/auth/onboarding/complete", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["user"]["onboarding_completed"] is True


def test_patch_profile(client, test_user, auth_headers):
    """PATCH profile updates fields."""
    r = client.patch(
        "/api/auth/profile",
        headers=auth_headers,
        json={"first_name": "Updated", "age": 30},
    )
    assert r.status_code == 200
    u = r.json()["user"]
    assert u["first_name"] == "Updated"
    assert u["age"] == 30


def test_search(client, test_user, auth_headers):
    """Search requires auth and query."""
    r = client.get("/api/search?q=apple", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "results" in data


def test_recommendations(client, test_user, auth_headers):
    """Engine returns user-centered guidance, weekly plan, and glucose context (no raw scores)."""
    r = client.get("/api/recommendations", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data.get("engine_version") == "3.0"
    assert "guidance" in data
    g = data["guidance"]
    assert g.get("current_state") in ("high", "low", "normal", "unknown")
    assert "next_action" in g and g["next_action"].get("meal")
    assert "alternatives" in g and isinstance(g["alternatives"], list)
    assert "avoid" in g and isinstance(g["avoid"], list)
    assert "explanation" in g and len(g["explanation"]) > 10
    assert "weekly_plan" in data and isinstance(data["weekly_plan"], list)
    assert "glucose_context" in data
    ctx = data["glucose_context"]
    assert ctx.get("tier") in ("unknown", "below_range", "in_range", "above_range", "high")
    assert "glucose_state" in ctx
    assert "meal_logic" not in ctx


def test_recommendation_engine_meta(client, test_user, auth_headers):
    """Engine diagnostics endpoint."""
    r = client.get("/api/recommendations/engine", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data.get("engine_version") == "3.0"
    assert "cache" in data and "ttl_sec" in data["cache"]


def test_recommendations_repeat_ok(client, test_user, auth_headers):
    """Repeated recommendations calls return consistent guidance shape."""
    r1 = client.get("/api/recommendations?limit=8", headers=auth_headers)
    r2 = client.get("/api/recommendations?limit=8", headers=auth_headers)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json().get("guidance") and r2.json().get("guidance")


def test_recommendation_feedback(client, test_user, auth_headers):
    """Feedback endpoint records like/skip."""
    r0 = client.get("/api/recommendations?limit=1", headers=auth_headers)
    assert r0.status_code == 200
    fid = r0.json()["guidance"]["next_action"]["feedback_food_id"]
    assert fid is not None
    fid = int(fid)
    r = client.post(
        "/api/recommendations/feedback",
        headers=auth_headers,
        json={"food_id": fid, "action": "like"},
    )
    assert r.status_code == 200
    assert r.json().get("ok") is True


@pytest.fixture
def chat_session(client, auth_headers):
    r = client.post("/api/chatbot/sessions", headers=auth_headers)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_chatbot_sessions_list_create_delete(client, auth_headers):
    r = client.post("/api/chatbot/sessions", headers=auth_headers)
    assert r.status_code == 200
    sid = r.json()["id"]
    lst = client.get("/api/chatbot/sessions", headers=auth_headers)
    assert lst.status_code == 200
    assert any(x["id"] == sid for x in lst.json())
    d = client.delete(f"/api/chatbot/sessions/{sid}", headers=auth_headers)
    assert d.status_code == 204


def test_chatbot_stability_question_not_greeting(client, auth_headers, chat_session):
    """'which' contains substring 'hi' — must not be classified as a greeting."""
    r = client.post(
        "/api/chatbot/message",
        headers=auth_headers,
        json={"message": "which food can keep my sugar level stable", "session_id": chat_session},
    )
    assert r.status_code == 200
    text = r.json()["response"]
    assert "glycemic" in text.lower() or "fiber" in text.lower()
    assert "Ask about foods, blood sugar, or meal ideas" not in text


def test_chatbot_typo_greeting(client, auth_headers, chat_session):
    r = client.post(
        "/api/chatbot/message",
        headers=auth_headers,
        json={"message": "hlo", "session_id": chat_session},
    )
    assert r.status_code == 200
    assert "nutrition assistant" in r.json()["response"].lower()


def test_chatbot_high_reading_not_same_as_food_list(client, auth_headers, chat_session):
    """High BG questions must not reuse the low-GI food examples reply."""
    r = client.post(
        "/api/chatbot/message",
        headers=auth_headers,
        json={"message": "what if my sugar level is high", "session_id": chat_session},
    )
    assert r.status_code == 200
    text = r.json()["response"]
    assert "clinician" in text.lower() or "care plan" in text.lower() or "correction" in text.lower()
    assert "Examples from this app's food list" not in text


def test_chatbot_numeric_glucose_70_vs_120(client, auth_headers, chat_session):
    """Same template must not answer ~70 (low) and ~120 (near-target) the same way."""
    r70 = client.post(
        "/api/chatbot/message",
        headers=auth_headers,
        json={
            "message": "which kind of food should i eat when my sugar levels are at 70",
            "session_id": chat_session,
        },
    )
    r120 = client.post(
        "/api/chatbot/message",
        headers=auth_headers,
        json={
            "message": "what if my sugar level is at 120, what am i supposed to eat",
            "session_id": chat_session,
        },
    )
    assert r70.status_code == 200 and r120.status_code == 200
    t70 = r70.json()["response"]
    t120 = r120.json()["response"]
    assert "70" in t70 and "120" in t120
    assert t70 != t120
    assert "fast-acting" in t70.lower() or "15 g" in t70 or "15g" in t70.replace(" ", "")
    assert "reasonable" in t120.lower() or "balanced" in t120.lower() or "target" in t120.lower()


def test_sensor_demo_requires_auth(client):
    r = client.get("/api/sensor-demo/meta")
    assert r.status_code == 401


def test_sensor_demo_meta_patients_series_summary(client, auth_headers):
    meta = client.get("/api/sensor-demo/meta", headers=auth_headers)
    assert meta.status_code == 200
    body = meta.json()
    assert "row_count" in body and "columns" in body and "csv_path" in body
    if body.get("row_count", 0) == 0:
        pytest.skip("SmartSensor CSV missing in test env: " + str(body.get("load_error")))

    p = client.get("/api/sensor-demo/patients?limit=5", headers=auth_headers)
    assert p.status_code == 200
    ids = p.json().get("patients") or []
    if not ids:
        pytest.fail(
            "sensor-demo returned no patient IDs while meta row_count > 0 — "
            f"row_count={body.get('row_count')} load_error={body.get('load_error')} csv_path={body.get('csv_path')}"
        )

    pid = str(ids[0])

    s = client.get("/api/sensor-demo/series", params={"patient_id": pid, "limit": 10}, headers=auth_headers)
    assert s.status_code == 200
    readings = s.json().get("readings") or []
    assert len(readings) >= 1
    assert "glucose_level" in readings[0]

    bad = client.get(
        "/api/sensor-demo/series",
        params={"patient_id": "__no_such_patient__", "limit": 10},
        headers=auth_headers,
    )
    assert bad.status_code == 404

    summ = client.get(
        "/api/sensor-demo/summary",
        params={"patient_id": pid, "last_n": 20},
        headers=auth_headers,
    )
    assert summ.status_code == 200
    sj = summ.json()
    assert str(sj.get("patient_id")) == pid
    assert sj.get("points", 0) >= 1


def test_chatbot_what_of_120_short_query(client, auth_headers, chat_session):
    """'what of 120' must match glucose context regex and give near-target guidance, not a generic greeting."""
    r = client.post(
        "/api/chatbot/message",
        headers=auth_headers,
        json={"message": "what of 120", "session_id": chat_session},
    )
    assert r.status_code == 200
    text = r.json()["response"]
    assert "120" in text
    assert "reasonable" in text.lower() or "balanced" in text.lower() or "target" in text.lower()
