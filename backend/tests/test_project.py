def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0.0"


def test_api_v2_health_check(client):
    response = client.get("/api/v2/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0.0"


def test_project_crud_lifecycle(client, tmp_path):
    proj_path = tmp_path / "Test_CRUD_Project"

    # 1. Create project
    create_resp = client.post(
        "/api/v2/projects",
        json={"name": "Initial Project Name", "path": str(proj_path)}
    )
    assert create_resp.status_code == 201
    proj_data = create_resp.json()
    proj_id = proj_data["project_id"]
    assert proj_data["name"] == "Initial Project Name"
    assert (proj_path / "project.json").exists()

    # 2. Get project
    get_resp = client.get(f"/api/v2/projects/{proj_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Initial Project Name"

    # 3. List projects
    list_resp = client.get("/api/v2/projects")
    assert list_resp.status_code == 200
    projs = list_resp.json()
    assert any(p["project_id"] == proj_id for p in projs)

    # 4. Patch project (update name and settings)
    patch_resp = client.patch(
        f"/api/v2/projects/{proj_id}",
        json={
            "name": "Updated Project Name",
            "settings": {
                "detection": {"sensitivity": 0.85, "profile": "dense_woodcut"},
                "editor": {"default_padding_top": 50},
                "export": {"archive_format": "PNG"},
                "vector": {"vectorizer": "vtracer", "colormode": "color"}
            }
        }
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["name"] == "Updated Project Name"
    assert updated["settings"]["detection"]["sensitivity"] == 0.85
    assert updated["settings"]["editor"]["default_padding_top"] == 50

    # 5. Delete project
    del_resp = client.delete(f"/api/v2/projects/{proj_id}?delete_files=false")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted_id"] == proj_id

    # 6. Verify get after delete returns 404
    get_after_del = client.get(f"/api/v2/projects/{proj_id}")
    assert get_after_del.status_code == 404
