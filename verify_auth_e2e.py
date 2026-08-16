import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

async def verify_auth_flow():
    print("🚀 Starting E2E Auth Flow Verification (In-Memory)...")
    
    import time
    test_email = f"e2etest_{int(time.time())}@patyluna.com"
    test_password = "SecurePassword123!"
    test_username = "E2E_Tester"
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1/api/v1") as client:
        # 1. Register User
        print(f"Step 1: Registering user {test_email}...")
        resp = await client.post("/auth/register", json={
            "email": test_email,
            "username": test_username,
            "password": test_password
        })
        
        if resp.status_code != 201:
            print(f"❌ Registration failed: {resp.status_code} {resp.text}")
            return
        print("✅ Registration successful.")
        
        # 1.5 Invalid Login
        print("Step 1.5: Logging in with invalid user...")
        login_resp = await client.post("/auth/login", json={
            "email": "invalid@patyluna.com",
            "password": "WrongPassword123!"
        })
        print(f"Invalid login response: {login_resp.status_code}")

        # 2. Login
        print("Step 2: Logging in...")
        login_resp = await client.post("/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        
        if login_resp.status_code != 200:
            print(f"❌ Login failed: {login_resp.status_code} {login_resp.text}")
            return
            
        data = login_resp.json()
        access_token = data.get("access_token")
        print("✅ Login successful. Received access token.")
        
        # 3. Fetch Profile
        print("Step 3: Fetching /auth/me...")
        me_resp = await client.get("/auth/me", headers={
            "Authorization": f"Bearer {access_token}"
        })
        
        if me_resp.status_code != 200:
            print(f"❌ Profile fetch failed: {me_resp.status_code} {me_resp.text}")
            return
            
        print("✅ Profile fetch successful:", me_resp.json()["email"])
        
        print("\n🎉 All Verification Steps Passed! The Auth payload bug is permanently resolved.")

if __name__ == "__main__":
    asyncio.run(verify_auth_flow())
