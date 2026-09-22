import json
import time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "benchmark" / "video_demo_case"
BASE = "http://127.0.0.1:8765/api"

with httpx.Client(timeout=300) as client:
    existing = client.get(BASE + "/cases").json()
    old = next((c for c in existing if c["name"] == "锦庭酒店案 · 视频演示样例"), None)
    if old:
        print(json.dumps({"existing_case": old}, ensure_ascii=False))
        raise SystemExit(0)

    case = client.post(BASE + "/cases", json={
        "name": "锦庭酒店案 · 视频演示样例",
        "description": "完全虚构 · 11份材料 · 覆盖前后供述、证人证言、监控、聊天记录、网约车与银行记录",
    }).json()
    case_id = case["id"]

    handles = []
    try:
        files = []
        for path in sorted(SOURCE.glob("*.pdf")):
            handle = path.open("rb")
            handles.append(handle)
            files.append(("files", (path.name, handle, "application/pdf")))
        upload = client.post(BASE + f"/cases/{case_id}/documents", files=files)
        upload.raise_for_status()
        print(json.dumps(upload.json(), ensure_ascii=False))
    finally:
        for h in handles:
            h.close()

    persons = client.get(BASE + f"/cases/{case_id}/persons").json()
    target = next(p for p in persons if p["canonical_name"] == "陈某")
    client.patch(BASE + f"/cases/{case_id}/target-person", json={"person_id": target["id"]}).raise_for_status()

    client.post(BASE + f"/cases/{case_id}/analyze").raise_for_status()
    while True:
        time.sleep(2)
        current = client.get(BASE + f"/cases/{case_id}").json()
        print(current["analysis_status"], current["progress"])
        if current["analysis_status"] in ("COMPLETED", "FAILED"):
            break

    result = {
        "case": current,
        "persons": client.get(BASE + f"/cases/{case_id}/persons").json(),
        "documents": client.get(BASE + f"/cases/{case_id}/documents").json(),
        "facts": client.get(BASE + f"/cases/{case_id}/facts").json(),
        "relations": client.get(BASE + f"/cases/{case_id}/relations").json(),
    }
    out = ROOT / "benchmark" / "video_demo_result.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("RESULT", out)
