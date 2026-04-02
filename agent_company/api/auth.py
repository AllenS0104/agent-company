"""GitHub Device Flow OAuth 认证"""

from __future__ import annotations

import httpx
from fastapi import APIRouter

from ..config import config

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _get_client_id() -> str:
    """获取 GitHub Client ID，未配置时使用 GitHub CLI 的公开 client_id"""
    return config.GITHUB_CLIENT_ID or "Iv1.b507a08c87ecfe98"


@router.post("/github/device-code")
async def request_device_code():
    """Step 1: 请求 Device Code"""
    client_id = _get_client_id()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://github.com/login/device/code",
            data={"client_id": client_id, "scope": "read:user"},
            headers={"Accept": "application/json"},
        )
        data = resp.json()
        return {
            "device_code": data["device_code"],
            "user_code": data["user_code"],
            "verification_uri": data["verification_uri"],
            "expires_in": data["expires_in"],
            "interval": data.get("interval", 5),
        }


@router.post("/github/poll-token")
async def poll_for_token(body: dict):
    """Step 2: 轮询检查用户是否已授权"""
    device_code = body.get("device_code", "")
    client_id = _get_client_id()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": client_id,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={"Accept": "application/json"},
        )
        data = resp.json()

        if "access_token" in data:
            config.GITHUB_TOKEN = data["access_token"]

            user_resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {data['access_token']}"},
            )
            user_data = user_resp.json()

            return {
                "status": "success",
                "access_token": data["access_token"][:8] + "...",
                "user": {
                    "login": user_data.get("login", ""),
                    "avatar_url": user_data.get("avatar_url", ""),
                    "name": user_data.get("name", ""),
                },
            }
        elif data.get("error") == "authorization_pending":
            return {"status": "pending"}
        elif data.get("error") == "slow_down":
            return {"status": "slow_down", "interval": data.get("interval", 10)}
        elif data.get("error") == "expired_token":
            return {"status": "expired"}
        else:
            return {"status": "error", "error": data.get("error", "unknown")}
