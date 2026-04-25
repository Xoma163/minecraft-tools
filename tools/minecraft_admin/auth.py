from __future__ import annotations

import secrets

from collections.abc import Callable

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from tools.minecraft_admin.config import Settings


security = HTTPBasic()


def require_admin(
    settings: Settings, credentials: HTTPBasicCredentials = Depends(security)
) -> None:
    valid_username = secrets.compare_digest(
        credentials.username, settings.admin_username
    )
    valid_password = secrets.compare_digest(
        credentials.password, settings.admin_password
    )
    if not (valid_username and valid_password):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )


def make_admin_dependency(settings: Settings) -> Callable[[HTTPBasicCredentials], None]:
    def dependency(credentials: HTTPBasicCredentials = Depends(security)) -> None:
        require_admin(settings, credentials)

    return dependency
