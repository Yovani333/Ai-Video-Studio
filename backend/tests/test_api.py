def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_project_lifecycle_and_scene_plan(client):
    payload = {
        "prompt": "An astronaut explores an unknown planet",
        "duration_seconds": 60,
        "quality": "draft",
    }

    created_response = client.post("/api/projects", json=payload)
    assert created_response.status_code == 201
    created = created_response.json()
    assert created["status"] == "created"
    assert created["prompt"] == payload["prompt"]
    assert len(created["scenes"]) == 12
    assert all(scene["duration_seconds"] == 5 for scene in created["scenes"])
    assert all(scene["status"] == "waiting" for scene in created["scenes"])

    project_id = created["id"]
    fetched_response = client.get(f"/api/projects/{project_id}")
    assert fetched_response.status_code == 200
    assert fetched_response.json()["id"] == project_id

    listed_response = client.get("/api/projects")
    assert listed_response.status_code == 200
    assert [project["id"] for project in listed_response.json()] == [project_id]


def test_project_validation_and_not_found(client):
    invalid_response = client.post(
        "/api/projects",
        json={"prompt": "x", "duration_seconds": 1, "quality": "draft"},
    )
    assert invalid_response.status_code == 422
    assert client.get("/api/projects/missing").status_code == 404
