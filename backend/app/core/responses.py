from typing import Any

from fastapi.responses import JSONResponse


def ok(data: Any = None, message: str = "ok", code: int = 200) -> dict:
    return {
        "code": code,
        "message": message,
        "data": data,
    }


def auth_ok(data: Any = None, message: str = "success") -> dict:
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def auth_fail(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "success": False,
            "message": message,
        },
    )
