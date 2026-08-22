"""로그인·회원가입·Google OAuth 라우트."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, Response, jsonify, redirect, render_template, request, session, url_for

from ads import public_ads_config
from auth.user_store import create_local_user, upsert_google_user, verify_local_user
from engagement.hooks import on_user_login
from utils.i18n import t
from utils.variables import env_bool, env_str, get_variable

auth_bp = Blueprint("auth", __name__)
oauth = OAuth()


def _google_client_id() -> str:
    return env_str("GOOGLE_CLIENT_ID") or str(get_variable("auth", "google_client_id", "") or "")


def _google_client_secret() -> str:
    return env_str("GOOGLE_CLIENT_SECRET") or str(get_variable("auth", "google_client_secret", "") or "")


def init_oauth(app: Any) -> OAuth:
    """Flask 앱에 OAuth 클라이언트 등록."""
    oauth.init_app(app)
    client_id = _google_client_id()
    client_secret = _google_client_secret()
    if client_id and client_secret:
        oauth.register(
            name="google",
            client_id=client_id,
            client_secret=client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
    return oauth


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    """세션 로그인 필수."""

    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if not session.get("login_id"):
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "message": t("auth.login_required")}), 401
            return redirect(url_for("auth.login_page"))
        return view(*args, **kwargs)

    return wrapped


def _google_enabled() -> bool:
    enabled = env_bool("GOOGLE_ENABLED", bool(get_variable("auth", "google_enabled", False)))
    if not enabled:
        return False
    return bool(_google_client_id()) and bool(_google_client_secret())


@auth_bp.route("/login")
def login_page() -> str:
    """로그인 UI."""
    if session.get("login_id"):
        return redirect("/")
    return render_template(
        "login.html",
        google_enabled=_google_enabled(),
        ads_config=public_ads_config(),
    )


@auth_bp.route("/api/auth/register", methods=["POST"])
def register() -> Response:
    """JSON 회원가입 → users.json 저장 후 자동 로그인."""
    payload = request.get_json(silent=True) or {}
    login_id = str(payload.get("login_id", ""))
    name = str(payload.get("name", ""))
    password = str(payload.get("password", ""))
    ok, message = create_local_user(login_id, name, password)
    if not ok:
        return jsonify({"ok": False, "message": message})
    user = verify_local_user(login_id, password)
    if user is None:
        return jsonify({"ok": True, "message": message, "auto_login": False})
    session["login_id"] = user["login_id"]
    session["name"] = user.get("name", user["login_id"])
    player = on_user_login(session["login_id"])
    return jsonify(
        {
            "ok": True,
            "message": message,
            "auto_login": True,
            "name": session["name"],
            "player": player,
        }
    )


@auth_bp.route("/api/auth/login", methods=["POST"])
def login() -> Response:
    """JSON 로그인."""
    payload = request.get_json(silent=True) or {}
    login_id = str(payload.get("login_id", ""))
    password = str(payload.get("password", ""))
    user = verify_local_user(login_id, password)
    if user is None:
        return jsonify({"ok": False, "message": t("auth.bad_credentials")}), 401
    session["login_id"] = user["login_id"]
    session["name"] = user.get("name", user["login_id"])
    player = on_user_login(session["login_id"])
    return jsonify(
        {
            "ok": True,
            "message": t("auth.login_ok"),
            "name": session["name"],
            "player": player,
        }
    )


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout() -> Response:
    """세션 종료."""
    session.clear()
    return jsonify({"ok": True, "message": t("auth.logout_ok")})


@auth_bp.route("/api/auth/me")
def me() -> Response:
    """현재 세션 사용자."""
    if not session.get("login_id"):
        return jsonify({"ok": False, "authenticated": False}), 401
    return jsonify(
        {
            "ok": True,
            "authenticated": True,
            "login_id": session.get("login_id"),
            "name": session.get("name"),
        }
    )


@auth_bp.route("/auth/google")
def google_login() -> Response:
    """Google OAuth 시작."""
    if not _google_enabled():
        return jsonify({"ok": False, "message": t("auth.google_not_configured")}), 503
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/auth/google/callback")
def google_callback() -> Response:
    """Google OAuth 콜백."""
    if not _google_enabled():
        return redirect(url_for("auth.login_page"))
    token = oauth.google.authorize_access_token()
    userinfo = token.get("userinfo")
    if not userinfo:
        resp = oauth.google.get("userinfo")
        userinfo = resp.json()
    email = userinfo.get("email")
    sub = userinfo.get("sub", "")
    name = userinfo.get("name") or email or "Google User"
    if not email:
        return redirect(url_for("auth.login_page"))
    login_id = email.split("@")[0].lower()
    user = upsert_google_user(login_id, name, sub)
    session["login_id"] = user["login_id"]
    session["name"] = user.get("name", name)
    on_user_login(user["login_id"])
    return redirect("/")
