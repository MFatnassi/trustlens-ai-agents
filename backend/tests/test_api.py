"""
API endpoint tests for the /analyze endpoint.

Starts the FastAPI server, then runs 3 test cases:
  1. Valid request -- should return 200 with proper response.
  2. Empty input -- should return 400.
  3. Oversized input -- should return 400.

Usage:
    cd backend
    python -m tests.test_api
"""

import asyncio
import sys
import time
from pathlib import Path

import httpx
import uvicorn
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

BASE_URL = "http://127.0.0.1:8000"


async def wait_for_server(timeout: int = 15):
    """Wait until the server is ready."""
    async with httpx.AsyncClient() as client:
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = await client.get(f"{BASE_URL}/health")
                if r.status_code == 200:
                    return True
            except httpx.ConnectError:
                pass
            await asyncio.sleep(0.5)
    return False


async def run_tests():
    async with httpx.AsyncClient(timeout=180) as client:
        print("=" * 60)
        print("API Endpoint Tests")
        print("=" * 60)

        # --- Test 1: Valid request ---
        print("\n--- Test 1: Valid request ---")
        r1 = await client.post(
            f"{BASE_URL}/analyze",
            json={"input": "Is this true: the new vaccine causes infertility?"},
        )
        print(f"  Status: {r1.status_code}")
        if r1.status_code == 200:
            data = r1.json()
            print(f"  Mode: {data['mode']}")
            if data["mode"] == "public":
                print(f"  Trust score: {data['result']['trust_score']}/100")
            print(f"  Sources used: {len(data['sources_used'])}")
            has_fields = "mode" in data and "result" in data and "sources_used" in data
            print(f"  [PASS] Valid response with correct structure" if has_fields else "  [FAIL] Missing fields")
        else:
            print(f"  [FAIL] Expected 200, got {r1.status_code}: {r1.text[:200]}")

        # --- Test 2: Empty input ---
        print("\n--- Test 2: Empty input ---")
        r2 = await client.post(
            f"{BASE_URL}/analyze",
            json={"input": ""},
        )
        print(f"  Status: {r2.status_code}")
        if r2.status_code == 400:
            print(f"  Detail: {r2.json().get('detail', '')}")
            print("  [PASS] Empty input rejected with 400")
        else:
            print(f"  [FAIL] Expected 400, got {r2.status_code}")

        # --- Test 3: Oversized input ---
        print("\n--- Test 3: Oversized input (15,000 chars) ---")
        r3 = await client.post(
            f"{BASE_URL}/analyze",
            json={"input": "x" * 15_000},
        )
        print(f"  Status: {r3.status_code}")
        if r3.status_code == 400:
            print(f"  Detail: {r3.json().get('detail', '')}")
            print("  [PASS] Oversized input rejected with 400")
        else:
            print(f"  [FAIL] Expected 400, got {r3.status_code}")

        print("\n" + "=" * 60)
        print("All API tests completed.")
        print("=" * 60)


async def main():
    # Start server in background
    config = uvicorn.Config("api:app", host="127.0.0.1", port=8000, log_level="warning")
    server = uvicorn.Server(config)

    server_task = asyncio.create_task(server.serve())

    try:
        print("Starting server...")
        if not await wait_for_server():
            print("Server failed to start within 15s")
            sys.exit(1)
        print("Server ready.\n")

        await run_tests()
    finally:
        server.should_exit = True
        await server_task


if __name__ == "__main__":
    asyncio.run(main())
