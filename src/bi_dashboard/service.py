import secrets
import time
from pathlib import Path

import pyotp
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from bi_dashboard import secret_store
from bi_dashboard._password import verify_password
from bi_dashboard.config import config

WEB_DIR = Path(__file__).resolve().parents[2] / "dashboard"
SESSION_PREFIX = "bi:session:"
LOGIN_FAIL_PREFIX = "bi:login-fail:ip:"
LOGIN_LOCK_PREFIX = "bi:login-lock:ip:"

app = FastAPI(
    title="Berlin Events BI auth gateway",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

_serializer = None
_redis = None
_mem_sessions = {}
_mem_login_failures = {}
_mem_login_locks = {}


def _get_serializer():
    global _serializer
    if _serializer is None:
        _serializer = URLSafeTimedSerializer(
            secret_store.get_session_secret(), salt="bi-session"
        )
    return _serializer


def _store():
    global _redis
    if not config.REDIS_URL:
        return None
    if _redis is None:
        import redis

        url = config.REDIS_URL.rstrip("/") + f"/{config.BI_REDIS_DB}"
        _redis = redis.from_url(url, decode_responses=True)
    return _redis


def create_session():
    sid = secrets.token_urlsafe(32)
    store = _store()
    if store is not None:
        store.setex(SESSION_PREFIX + sid, config.SESSION_TTL_SECONDS, config.BI_USER_NAME)
    else:
        _mem_sessions[sid] = time.time() + config.SESSION_TTL_SECONDS
    return _get_serializer().dumps(sid)


def read_session(cookie):
    if not cookie:
        return None
    try:
        sid = _get_serializer().loads(cookie, max_age=config.SESSION_TTL_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    store = _store()
    if store is not None:
        return config.BI_USER_NAME if store.exists(SESSION_PREFIX + sid) else None
    expires = _mem_sessions.get(sid)
    if expires and expires > time.time():
        return config.BI_USER_NAME
    _mem_sessions.pop(sid, None)
    return None


def destroy_session(cookie):
    if not cookie:
        return
    try:
        sid = _get_serializer().loads(cookie, max_age=config.SESSION_TTL_SECONDS)
    except (BadSignature, SignatureExpired):
        return
    store = _store()
    if store is not None:
        store.delete(SESSION_PREFIX + sid)
    else:
        _mem_sessions.pop(sid, None)


def verify_totp(code, secret=None):
    if not code:
        return False
    if secret is None:
        secret = secret_store.get_active_totp_secret()
    if not secret:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def request_origin(request: Request):
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("host") or request.url.netloc
    return f"{proto}://{host}".rstrip("/")


def require_same_origin(request: Request):
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != request_origin(request):
        raise HTTPException(status_code=403, detail="bad origin")


def client_ip(request: Request):
    return (
        request.headers.get("x-real-ip")
        or request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        or (request.client.host if request.client else "")
        or "unknown"
    )


def login_is_locked(ip):
    store = _store()
    if store is not None:
        return bool(store.exists(LOGIN_LOCK_PREFIX + ip))
    now = time.time()
    expires = _mem_login_locks.get(ip)
    if expires and expires > now:
        return True
    _mem_login_locks.pop(ip, None)
    return False


def record_login_failure(ip):
    store = _store()
    if store is not None:
        key = LOGIN_FAIL_PREFIX + ip
        count = int(store.incr(key))
        if count == 1:
            store.expire(key, config.LOGIN_FAILURE_WINDOW_SECONDS)
        if count >= config.LOGIN_MAX_FAILURES:
            store.setex(LOGIN_LOCK_PREFIX + ip, config.LOGIN_LOCKOUT_SECONDS, "1")
        return count
    now = time.time()
    count, expires = _mem_login_failures.get(ip, (0, 0))
    if expires <= now:
        count = 0
    count += 1
    _mem_login_failures[ip] = (count, now + config.LOGIN_FAILURE_WINDOW_SECONDS)
    if count >= config.LOGIN_MAX_FAILURES:
        _mem_login_locks[ip] = now + config.LOGIN_LOCKOUT_SECONDS
    return count


def clear_login_failures(ip):
    store = _store()
    if store is not None:
        store.delete(LOGIN_FAIL_PREFIX + ip)
        store.delete(LOGIN_LOCK_PREFIX + ip)
        return
    _mem_login_failures.pop(ip, None)
    _mem_login_locks.pop(ip, None)


async def read_json_object(request: Request):
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid JSON") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")
    return body


def _set_session():
    response = JSONResponse({"ok": True})
    response.set_cookie(
        config.SESSION_COOKIE,
        create_session(),
        max_age=config.SESSION_TTL_SECONDS,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return response


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/login.html")
async def login_page():
    return FileResponse(WEB_DIR / "login.html")


@app.get("/login.css")
async def login_css():
    return FileResponse(WEB_DIR / "login.css")


@app.get("/qrcode.js")
async def qrcode_js():
    return FileResponse(WEB_DIR / "qrcode.min.js")


@app.get("/material-symbols.woff2")
async def material_symbols_font():
    return FileResponse(
        WEB_DIR / "material-symbols.woff2",
        media_type="font/woff2",
        headers={"Cache-Control": "public, max-age=604800"},
    )


@app.get("/session")
async def session(request: Request):
    user = read_session(request.cookies.get(config.SESSION_COOKIE))
    if not user:
        return Response(status_code=401)
    return Response(status_code=204, headers={"X-Auth-User": user})


@app.post("/login")
async def login(request: Request):
    require_same_origin(request)
    ip = client_ip(request)
    if login_is_locked(ip):
        return JSONResponse({"error": "Too many failed attempts."}, status_code=429)
    try:
        body = await read_json_object(request)
    except HTTPException:
        return JSONResponse({"error": "Bad request."}, status_code=400)

    password = body.get("password") or ""
    code = (body.get("code") or "").strip()

    if not verify_password(password, config.ADMIN_PW_HASH):
        record_login_failure(ip)
        return JSONResponse({"error": "Wrong password."}, status_code=401)

    active_secret = secret_store.get_active_totp_secret()
    if not active_secret:
        pending = secret_store.get_pending_totp_secret()
        if not code:
            if not pending:
                pending = pyotp.random_base32()
                secret_store.set_pending_totp_secret(pending)
            uri = pyotp.TOTP(pending).provisioning_uri(
                name=config.BI_USER_NAME, issuer_name="Berlin Events BI"
            )
            return JSONResponse({"enroll": True, "otpauth_uri": uri, "secret": pending})

        if pending and verify_totp(code, pending):
            secret_store.promote_pending_totp()
            clear_login_failures(ip)
            return _set_session()

        secret_store.clear_pending_totp()
        record_login_failure(ip)
        return JSONResponse({"error": "Wrong code. Try again."}, status_code=401)

    if not verify_totp(code, active_secret):
        record_login_failure(ip)
        return JSONResponse({"error": "Wrong code."}, status_code=401)
    clear_login_failures(ip)
    return _set_session()


@app.post("/logout")
async def logout(request: Request):
    require_same_origin(request)
    destroy_session(request.cookies.get(config.SESSION_COOKIE))
    response = JSONResponse({"ok": True})
    response.delete_cookie(config.SESSION_COOKIE, path="/")
    return response
