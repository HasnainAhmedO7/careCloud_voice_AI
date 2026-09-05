from typing import Any


def ok(data: Any) -> dict:
    return {"data": data, "error": None}


def fail(message: str) -> dict:
    return {"data": None, "error": {"message": message}}
