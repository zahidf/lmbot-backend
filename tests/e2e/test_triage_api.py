import pytest


class TestTriageConfigAPI:
    """Tests for GET /api/v1/chat/triage/config"""

    def test_get_triage_config_success(self, client):
        """Config endpoint returns all static triage options"""
        response = client.get("/api/v1/chat/triage/config")

        assert response.status_code == 200
        data = response.json()

        assert "burner_series" in data
        assert "issue_categories" in data
        assert "serial_number_example" in data
        assert "serial_number_tooltip" in data

        assert "TX" in data["burner_series"]
        assert "FD" in data["burner_series"]
        assert "DB" in data["burner_series"]
        assert "FDB" in data["burner_series"]

        assert data["serial_number_example"] == "J123456"

        # All 7 categories A-G must be present
        for key in ["A", "B", "C", "D", "E", "F", "G"]:
            assert key in data["issue_categories"], f"Missing category {key}"


class TestTriageFollowUpsAPI:
    """Tests for GET /api/v1/chat/triage/follow-ups/{category} (no auth required)"""

    def test_get_follow_ups_category_A(self, client):
        """Category A follow-ups are returned with correct structure"""
        response = client.get("/api/v1/chat/triage/follow-ups/A")

        assert response.status_code == 200
        data = response.json()

        assert data["category"] == "A"
        assert data["category_label"] == "Burner Will Not Start"
        assert isinstance(data["follow_ups"], list)
        assert len(data["follow_ups"]) >= 1

        for prompt in data["follow_ups"]:
            assert "question" in prompt
            assert "field_key" in prompt
            assert "input_type" in prompt

    def test_get_follow_ups_category_E(self, client):
        """Category E (Documentation Request) returns follow-up prompts"""
        response = client.get("/api/v1/chat/triage/follow-ups/E")

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "E"
        assert isinstance(data["follow_ups"], list)

    def test_get_follow_ups_all_valid_categories(self, client):
        """All valid categories A-G return 200"""
        for category in ["A", "B", "C", "D", "E", "F", "G"]:
            response = client.get(f"/api/v1/chat/triage/follow-ups/{category}")
            assert response.status_code == 200, f"Category {category} returned {response.status_code}"

    def test_get_follow_ups_invalid_category(self, client):
        """Invalid category returns 400 with descriptive error"""
        response = client.get("/api/v1/chat/triage/follow-ups/Z")

        assert response.status_code == 400
        assert "Invalid category" in response.json()["detail"]
        assert "Z" in response.json()["detail"]


class TestTriageSubmitAPI:
    """Tests for POST /api/v1/chat/triage/submit (auth required)"""

    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer test-token"}

    def test_submit_triage_creates_new_session(self, client, auth_headers):
        """Submitting triage with no session_id creates a new session"""
        payload = {
            "issue_category": "A",
            "burner_series": "TX",
            "has_serial_number": False,
        }

        response = client.post(
            "/api/v1/chat/triage/submit",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        assert "triage_id" in data
        assert "session_id" in data
        assert data["issue_category"] == "A"
        assert data["burner_series"] == "TX"
        assert "TX Series" in data["context_summary"]

    def test_submit_triage_with_serial_number(self, client, auth_headers):
        """Serial number is stored and returned when has_serial_number is True"""
        payload = {
            "issue_category": "B",
            "burner_series": "FD",
            "has_serial_number": True,
            "serial_number": "J123456",
        }

        response = client.post(
            "/api/v1/chat/triage/submit",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["serial_number"] == "J123456"

    def test_submit_triage_with_follow_up_answers(self, client, auth_headers):
        """Follow-up answers are included in the context summary"""
        payload = {
            "issue_category": "A",
            "follow_up_answers": {"has_power": "Yes", "fault_codes": "E1"},
        }

        response = client.post(
            "/api/v1/chat/triage/submit",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert "has_power" in data["context_summary"]

    def test_submit_triage_unknown_burner(self, client, auth_headers):
        """Triage with no burner series and unknown identification is valid"""
        payload = {
            "issue_category": "C",
            "burner_series": None,
            "burner_identified_via": "unknown",
            "has_serial_number": False,
        }

        response = client.post(
            "/api/v1/chat/triage/submit",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["burner_series"] is None
        assert "Unknown" in data["context_summary"]

    def test_submit_triage_category_G_with_free_text(self, client, auth_headers):
        """Category G free-text description appears in context summary"""
        payload = {
            "issue_category": "G",
            "issue_free_text": "Unusual vibration noise from burner head",
        }

        response = client.post(
            "/api/v1/chat/triage/submit",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert "Unusual vibration noise from burner head" in data["context_summary"]

    def test_submit_triage_invalid_category(self, client, auth_headers):
        """Invalid issue category raises 400"""
        payload = {"issue_category": "Z"}

        response = client.post(
            "/api/v1/chat/triage/submit",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "Invalid issue category" in response.json()["detail"]

    def test_submit_triage_invalid_burner_series(self, client, auth_headers):
        """Invalid burner series raises 400"""
        payload = {
            "issue_category": "A",
            "burner_series": "INVALID",
        }

        response = client.post(
            "/api/v1/chat/triage/submit",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "Invalid burner series" in response.json()["detail"]

    def test_submit_triage_invalid_serial_number_format(self, client, auth_headers):
        """Serial number starting with a digit is rejected with 400"""
        payload = {
            "issue_category": "A",
            "has_serial_number": True,
            "serial_number": "12345",  # digits-only, no leading letter
        }

        response = client.post(
            "/api/v1/chat/triage/submit",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "Invalid serial number format" in response.json()["detail"]

    def test_submit_triage_unauthenticated(self, client):
        """Submit without auth returns 401"""
        payload = {"issue_category": "A"}

        response = client.post("/api/v1/chat/triage/submit", json=payload)

        assert response.status_code == 401


class TestTriageSessionAPI:
    """Tests for GET /api/v1/chat/triage/session/{session_id} (auth required)"""

    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer test-token"}

    def test_get_session_triage_success(self, client, auth_headers):
        """After submitting triage, its data can be retrieved by session_id"""
        # Get session id by submitting triage
        submit_response = client.post(
            "/api/v1/chat/triage/submit",
            json={"issue_category": "D", "burner_series": "DB"},
            headers=auth_headers,
        )
        assert submit_response.status_code == 201
        session_id = submit_response.json()["session_id"]
        triage_id = submit_response.json()["triage_id"]

        # Retrieve the triage by session_id
        response = client.get(
            f"/api/v1/chat/triage/session/{session_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["triage_id"] == triage_id
        assert data["issue_category"] == "D"

    def test_get_session_triage_not_found(self, client, auth_headers):
        """Non-existent session_id returns 404"""
        response = client.get(
            "/api/v1/chat/triage/session/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "No triage found" in response.json()["detail"]

    def test_get_session_triage_unauthenticated(self, client):
        """Accessing session triage without auth returns 401"""
        response = client.get(
            "/api/v1/chat/triage/session/00000000-0000-0000-0000-000000000000"
        )

        assert response.status_code == 401
