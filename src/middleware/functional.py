import asyncio

from fastapi import Request, status
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware


class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    This middleware class extends the BaseHTTPMiddleware class and implements a timeout mechanism for handling requests.
    The middleware class takes a timeout parameter that specifies the maximum time allowed
    for a request to be processed.

    :param BaseHTTPMiddleware: A base class for implementing HTTP middleware.
    :rtype BaseHTTPMiddleware: BaseHTTPMiddleware
    :param timeout: The maximum time allowed for a request to be processed.
    :rtype timeout: int

    example: app.add_middleware(TimeoutMiddleware, timeout=5)
    """

    def __init__(self, app, timeout: int):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            return PlainTextResponse(status_code=status.HTTP_504_GATEWAY_TIMEOUT, content="Request timed out")
