from contextvars import ContextVar
from typing import Optional

request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)

def get_request_id() -> Optional[str]:
    return request_id_var.get()

def set_request_id(request_id: str) -> None:
    request_id_var.set(request_id)

def get_user_id() -> Optional[str]:
    return user_id_var.get()

def set_user_id(user_id: str) -> None:
    user_id_var.set(user_id)