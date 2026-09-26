import io
from PIL import Image


def test_site_and_survey_lifecycle(client):
    # 1. Create Site
    site_payload = {
        "name": "Amber Fort Outer Bastion",
        "location": "Jaipur, Rajasthan, India",
        "description": "Historic hill fortification featuring yellow and pink sandstone masonry.",
        "historical_period": "16th Century",
        "primary_material": "Sandstone & Lime Mortar",
        "latitude": 26.9855,
        "longitude": 75.8513,
    }
    site_res = client.post("/api/sites", json=site_payload)
    assert site_res.status_code == 201
    site_data = site_res.json()
    site_id = site_data["id"]
    assert site_data["name"] == site_payload["name"]
    assert site_data["survey_count"] == 0

    # 2. List Sites
    list_res = client.get("/api/sites")
    assert list_res.status_code == 200
    sites = list_res.json()
    assert any(s["id"] == site_id for s in sites)

    # 3. Create Survey under Site
    survey_payload = {
        "site_id": site_id,
        "survey_code": "AMB-2026-Q1",
        "survey_date": "2026-03-15T09:30:00Z",
        "description": "Baseline photogrammetric survey of the lower sandstone rampart.",
        "operator": "Dr. R. Sharma",
        "camera_info": "Sony A7 IV, 35mm f/2.8",
        "environmental_info": {
            "temp_c": 31.5,
            "humidity_pct": 42.0,
            "rainfall_mm": 0.0,
            "uv_index": 8.0,
        },
    }
    srv_res = client.post("/api/surveys", json=survey_payload)
    assert srv_res.status_code == 201
    survey_data = srv_res.json()
    survey_id = survey_data["id"]
    assert survey_data["survey_code"] == "AMB-2026-Q1"
    assert survey_data["status"] == "created"

    # 4. Upload an in-memory generated test image
    img = Image.new("RGB", (1000, 800), color=(180, 140, 100))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    img_byte_arr.seek(0)

    upload_res = client.post(
        f"/api/surveys/{survey_id}/images/upload",
        files=[("files", ("rampart_01.jpg", img_byte_arr, "image/jpeg"))],
    )
    assert upload_res.status_code == 201
    upload_data = upload_res.json()
    assert upload_data["total_uploaded"] == 1
    assert len(upload_data["uploaded_images"]) == 1

    uploaded_img_id = upload_data["uploaded_images"][0]["id"]
    assert upload_data["uploaded_images"][0]["width"] == 1000
    assert upload_data["uploaded_images"][0]["height"] == 800

    # 5. Verify Survey Detail contains uploaded image
    detail_res = client.get(f"/api/surveys/{survey_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["image_count"] == 1
    assert len(detail["images"]) == 1
    assert detail["images"][0]["id"] == uploaded_img_id

    # 6. Check Quality Summary Endpoint
    qs_res = client.get(f"/api/surveys/{survey_id}/quality-summary")
    assert qs_res.status_code == 200
    qs = qs_res.json()
    assert qs["total_images"] == 1
    assert "ready_for_photogrammetry" in qs
