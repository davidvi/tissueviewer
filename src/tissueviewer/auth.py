"""HTTP Basic authentication middleware.

When enabled, every request to the FastAPI app must carry a valid
``Authorization: Basic ...`` header matching the configured single
username/password pair. There is no session state and no login form;
the browser's native dialog handles the prompt.

Note: Basic auth transmits credentials on every request encoded (not
encrypted) in the header. Only deploy this behind HTTPS.
"""

from __future__ import annotations

import base64
import binascii
import secrets
from typing import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import Response


_REALM = "TissueViewer"


def _challenge() -> Response:
    return Response(
        "Unauthorized",
        status_code=401,
        headers={"WWW-Authenticate": f'Basic realm="{_REALM}"'},
    )


def make_basic_auth_middleware(
    username: str, password: str
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    """Build a Starlette HTTP middleware enforcing Basic auth.

    The closure pre-encodes the expected credentials so each request
    only does a base64 decode and two constant-time comparisons.
    """
    expected_user = username.encode("utf-8")
    expected_pass = password.encode("utf-8")

    async def middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        header = request.headers.get("authorization", "")
        if header[:6].lower() == "basic ":
            try:
                decoded = base64.b64decode(header[6:].encode("ascii"), validate=True)
            except (ValueError, binascii.Error):
                return _challenge()
            user, sep, pwd = decoded.partition(b":")
            if sep:
                ok_user = secrets.compare_digest(user, expected_user)
                ok_pass = secrets.compare_digest(pwd, expected_pass)
                if ok_user and ok_pass:
                    return await call_next(request)
        return _challenge()

    return middleware


__all__ = ["make_basic_auth_middleware"]
