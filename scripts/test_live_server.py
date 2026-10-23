import urllib.request
import json

def test():
    endpoints = [
        ("Health", "http://127.0.0.1:8000/api/health"),
        ("Photogrammetry System", "http://127.0.0.1:8000/api/photogrammetry/availability"),
        ("Deterioration Models", "http://127.0.0.1:8000/api/deterioration/models"),
        ("Material Models", "http://127.0.0.1:8000/api/materials/models"),
        ("Sites", "http://127.0.0.1:8000/api/sites"),
        ("Frontend UI", "http://localhost:5174/"),
    ]
    for name, url in endpoints:
        try:
            with urllib.request.urlopen(url) as resp:
                raw = resp.read().decode("utf-8")
                print(f"[OK] {name}: status={resp.status}")
                if name == "Photogrammetry System":
                    data = json.loads(raw)
                    print(f"     colmap_available={data.get('colmap_available')}, open3d={data.get('open3d_version')}")
                elif name in ["Deterioration Models", "Material Models"]:
                    data = json.loads(raw)
                    print(f"     models count={len(data)}, names={[m.get('name') for m in data]}")
                elif name == "Frontend UI":
                    print(f"     Vite HTML served successfully ({len(raw)} bytes).")
        except Exception as e:
            print(f"[ERR] {name} ({url}): {e}")

if __name__ == "__main__":
    test()
