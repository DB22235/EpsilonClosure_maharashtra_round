"""
Simulated challenge flow against a running Uvicorn API.
Requires JWT + campaign UUID. Does not import Dhruv's database.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

import httpx


def generate_mock_landmarks_for_thumbs_up() -> list[list[float]]:
    landmarks = [[500.0, 700.0] for _ in range(21)]
    landmarks[0] = [500.0, 700.0]
    landmarks[2] = [450.0, 600.0]
    landmarks[3] = [430.0, 480.0]
    landmarks[4] = [400.0, 320.0]
    landmarks[5] = [520.0, 580.0]
    landmarks[6] = [530.0, 620.0]
    landmarks[8] = [535.0, 650.0]
    landmarks[10] = [570.0, 620.0]
    landmarks[12] = [575.0, 650.0]
    landmarks[14] = [610.0, 620.0]
    landmarks[16] = [615.0, 650.0]
    landmarks[18] = [650.0, 620.0]
    landmarks[20] = [655.0, 650.0]
    return landmarks


def telemetry_for(gesture: str, hand: str) -> dict[str, Any]:
    thumbs = generate_mock_landmarks_for_thumbs_up()
    swipe = [[100.0 + i * 40.0, 400.0] for i in range(12)]
    move = [[200.0 + i * 20.0, 300.0 + i * 15.0] for i in range(12)]
    metadata: dict[str, Any] = {"landmarks": thumbs, "trajectory": []}
    if gesture == "SWIPE":
        metadata = {"trajectory": swipe}
    elif gesture == "MOVE":
        metadata = {"trajectory": move}
    return metadata


async def run_tests(token: str, campaign_id: str, base_url: str) -> bool:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    create_payload = {
        "campaign_id": campaign_id,
        "type": "MEDIAPIPE",
        "operation": "REGISTER",
        "requested_reason": "MEDIUM_RISK",
    }

    async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=15.0) as client:
        print("--- 1. Create MEDIAPIPE challenge ---")
        res = await client.post("challenges", json=create_payload)
        if res.status_code != 201:
            print(f"[FAIL] create: HTTP {res.status_code} {res.text}")
            return False
        data = res.json()
        challenge_id = data["challenge_id"]
        nonce = data["nonce"]
        instructions = data.get("instructions") or {}
        required_hand = str(instructions.get("hand", "LEFT")).upper()
        required_gesture = str(instructions.get("gesture", "THUMBS_UP")).upper()
        print(f"[OK] issued {challenge_id} gesture={required_gesture} hand={required_hand}")

        print("--- 2. Verify matching hand + telemetry ---")
        verify_payload = {
            "nonce": nonce,
            "type": "MEDIAPIPE",
            "result": "SUCCESS",
            "confidence": 0.92,
            "duration_ms": 1450,
            "implementation_version": data["implementation_version"],
            "hand_used": required_hand,
            "model_metadata": telemetry_for(required_gesture, required_hand),
        }
        v_res = await client.post(f"challenges/{challenge_id}/verify", json=verify_payload)
        if v_res.status_code != 200:
            print(f"[FAIL] verify: HTTP {v_res.status_code} {v_res.text}")
            return False
        v_data = v_res.json()
        if v_data.get("status") != "PASSED":
            print(f"[FAIL] expected PASSED, got {v_data}")
            return False
        print(f"[OK] verification PASSED reason={v_data.get('reason_code')}")

        print("--- 3. Hand mismatch rejection ---")
        res2 = await client.post("challenges", json=create_payload)
        if res2.status_code != 201:
            print(f"[FAIL] mismatch create: HTTP {res2.status_code} {res2.text}")
            return False
        data2 = res2.json()
        req_hand2 = str(data2.get("instructions", {}).get("hand", "LEFT")).upper()
        wrong_hand = "RIGHT" if req_hand2 == "LEFT" else "LEFT"
        mismatch_payload = {
            "nonce": data2["nonce"],
            "type": "MEDIAPIPE",
            "result": "SUCCESS",
            "confidence": 0.95,
            "duration_ms": 1200,
            "implementation_version": data2["implementation_version"],
            "hand_used": wrong_hand,
            "model_metadata": {"landmarks": generate_mock_landmarks_for_thumbs_up()},
        }
        v_res2 = await client.post(f"challenges/{data2['challenge_id']}/verify", json=mismatch_payload)
        v_data2 = v_res2.json() if v_res2.status_code == 200 else {}
        if not (v_data2.get("status") == "FAILED" or v_data2.get("reason_code") == "HAND_MISMATCH"):
            print(f"[FAIL] expected HAND_MISMATCH/FAILED, got HTTP {v_res2.status_code} {v_res2.text}")
            return False
        print(f"[OK] hand mismatch rejected status={v_data2.get('status')} reason={v_data2.get('reason_code')}")

        print("--- 4. Cooldown after 3 MOCK failures ---")
        mock_create = {
            "campaign_id": campaign_id,
            "type": "MOCK",
            "operation": "REGISTER",
            "requested_reason": "MEDIUM_RISK",
        }
        for i in range(3):
            c_res = await client.post("challenges", json=mock_create)
            if c_res.status_code == 429:
                print("[OK] cooldown already active during failure seeding")
                print("[PASS] Simulated integration flow completed")
                return True
            if c_res.status_code != 201:
                print(f"[FAIL] mock create {i + 1}: HTTP {c_res.status_code} {c_res.text}")
                return False
            body = c_res.json()
            await client.post(
                f"challenges/{body['challenge_id']}/verify",
                json={
                    "nonce": body["nonce"],
                    "type": "MOCK",
                    "result": "FAILURE",
                    "confidence": 0.0,
                    "duration_ms": 1000,
                    "implementation_version": "mock-v1",
                },
            )
        c4 = await client.post("challenges", json=mock_create)
        if c4.status_code != 429:
            print(f"[FAIL] expected HTTP 429 COOLDOWN_ACTIVE, got {c4.status_code} {c4.text}")
            return False
        err = c4.json().get("error") or c4.json().get("detail") or {}
        if isinstance(err, dict) and err.get("error"):
            err = err["error"]
        code = err.get("code") if isinstance(err, dict) else None
        if code != "COOLDOWN_ACTIVE":
            # FastAPI may wrap HTTPException.detail
            detail = c4.json().get("detail")
            if isinstance(detail, dict):
                code = (detail.get("error") or {}).get("code")
        if code != "COOLDOWN_ACTIVE":
            print(f"[FAIL] cooldown envelope missing COOLDOWN_ACTIVE: {c4.json()}")
            return False
        print("[OK] cooldown returned HTTP 429 COOLDOWN_ACTIVE")

    print("[PASS] Simulated integration flow completed")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate challenge create/verify against Uvicorn")
    parser.add_argument("--token", required=True, help="Bearer JWT")
    parser.add_argument("--campaign-id", required=True, help="Campaign UUID")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1/", help="API base URL")
    args = parser.parse_args()
    ok = asyncio.run(run_tests(args.token, args.campaign_id, args.base_url))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
