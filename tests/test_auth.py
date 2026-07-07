import os
import asyncio

import httpx
import pyotp

from bi_dashboard._password import hash_password


def test_first_login_enrolls_totp(monkeypatch, tmp_path):
    async def run_flow():
        monkeypatch.setenv("ADMIN_PW_HASH", hash_password("pw"))
        monkeypatch.setenv("COOKIE_SESSION_SECRET", "test-secret")
        monkeypatch.setenv("COOKIE_SECURE", "false")
        monkeypatch.setenv("SECRET_STORE_PATH", str(tmp_path / "secrets.json"))
        monkeypatch.setenv("REDIS_URL", "")

        from bi_dashboard import config as config_module
        from bi_dashboard import secret_store
        from bi_dashboard import service

        config_module.config.ADMIN_PW_HASH = os.environ["ADMIN_PW_HASH"]
        config_module.config.COOKIE_SESSION_SECRET = "test-secret"
        config_module.config.COOKIE_SECURE = False
        config_module.config.SECRET_STORE_PATH = str(tmp_path / "secrets.json")
        config_module.config.REDIS_URL = ""
        service._serializer = None
        service._redis = None

        transport = httpx.ASGITransport(app=service.app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            enroll = await client.post("/login", json={"password": "pw"})
            assert enroll.status_code == 200
            data = enroll.json()
            assert data["enroll"] is True

            code = pyotp.TOTP(secret_store.get_pending_totp_secret()).now()
            login = await client.post("/login", json={"password": "pw", "code": code})
            assert login.status_code == 200
            assert "bi_session" in login.cookies

            session = await client.get("/session")
            assert session.status_code == 204
            assert session.headers["x-auth-user"] == "admin"

    asyncio.run(run_flow())
