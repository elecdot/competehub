from competehub_api import create_app


def test_health_endpoint() -> None:
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "data": {
            "service": "competehub-api",
            "status": "ok",
        },
        "error": None,
    }
