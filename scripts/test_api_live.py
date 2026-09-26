import httpx

def main():
    base_url = "http://127.0.0.1:8000"
    client = httpx.Client(base_url=base_url, timeout=10.0)

    # 1. Health
    h = client.get("/api/health")
    print("Health Status:", h.status_code, h.json().get("status"))

    # 2. Sites
    sites = client.get("/api/sites").json()
    print(f"Sites: {len(sites)} registered site(s).")
    for s in sites:
        print(f" - {s['name']} (ID: {s['id']})")

    # 3. Surveys
    surveys = client.get("/api/surveys").json()
    print(f"Surveys: {len(surveys)} survey(s).")
    if surveys:
        s0 = surveys[0]
        s_id = s0['id']
        print(f" - Code: {s0['survey_code']}, Images: {s0['image_count']}, Avg Quality: {s0['average_quality_score']}")
        
        # 4. Survey Quality Summary (Phase 1 Preserved)
        q = client.get(f"/api/surveys/{s_id}/quality-summary").json()
        print("Survey Quality Summary (Phase 1):")
        print(f"   Pass Count: {q['pass_count']}, Blur Failures: {q['blur_failures']}, Pass Rate: {q['pass_percentage']}%")

        # 5. Get Survey Images for Pairwise Matching (Phase 2)
        images = client.get(f"/api/surveys/{s_id}/images").json()
        if len(images) >= 2:
            img_a = images[0]
            img_b = images[1]
            print(f"\n[*] Testing Phase 2 Pairwise Feature Match ({img_a['filename']} <-> {img_b['filename']})...")
            match_res = client.post(
                "/api/image-quality/match",
                json={"image_a_id": img_a["id"], "image_b_id": img_b["id"]}
            )
            print("   Match Status Code:", match_res.status_code)
            m_data = match_res.json()
            print(f"   Keypoints: A={m_data['keypoints_a']}, B={m_data['keypoints_b']}")
            print(f"   Candidate Matches: {m_data['candidate_matches']}, Good Matches: {m_data['good_matches']}")
            print(f"   Match Ratio: {m_data['match_ratio']}, Status: {m_data['status']}")
            print(f"   Overlap Indicator: {m_data['estimated_overlap']}")
            print(f"   Recommendation: {m_data['recommendation']}")

        # 6. Test Survey Collection Analysis & Connectivity Graph (Phase 2)
        print(f"\n[*] Triggering Phase 2 Survey Collection Analysis for '{s0['survey_code']}'...")
        ana_res = client.post(f"/api/image-quality/surveys/{s_id}/analyze")
        print("   Analysis Status Code:", ana_res.status_code)
        ana_data = ana_res.json()
        print(f"   Images Analyzed: {ana_data['images_analyzed']}, Pairs Analyzed: {ana_data['pairs_analyzed']}")
        print(f"   Good Pairs: {ana_data['good_pairs']}, Warning Pairs: {ana_data['warning_pairs']}, Poor Pairs: {ana_data['poor_pairs']}")
        print(f"   Readiness Status: {ana_data['readiness_status']}")
        print(f"   Isolated Images: {ana_data['isolated_image_ids']}")
        print(f"   Weakly Connected: {ana_data['weakly_connected_image_ids']}")
        print(f"   Recommendations:")
        for r in ana_data['recommendations']:
            print(f"     - {r}")

        # 7. Test Cached Readiness
        readiness_res = client.get(f"/api/image-quality/surveys/{s_id}/readiness")
        print("\n[*] Retrieved Cached Readiness Status Code:", readiness_res.status_code)

        # 8. Test Pairs List
        pairs_res = client.get(f"/api/image-quality/surveys/{s_id}/pairs")
        print(f"[*] Retrieved Analyzed Pairs Count: {len(pairs_res.json())}")

if __name__ == "__main__":
    main()
