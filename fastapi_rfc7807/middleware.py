"""FastAPI middleware and error handlers for RFC7807-compliant Problem responses.

For details on the Problem format, see: https://tools.ietf.org/html/rfc7807
"""

import asyncio
import http
import json
from typing import Any, Awaitable, Callable, Dict, Optional, Sequence, Union

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class ProblemResponse(Response):
    """A Response for RFC7807 Problems."""

    media_type: str = 'application/problem+json'

    def __init__(self, *args, debug: bool = False, **kwargs) -> None:
        self.debug: bool = debug
        super(ProblemResponse, self).__init__(*args, **kwargs)

    def render(self, content: Any) -> bytes:
        """Render the provided content as an RFC-7807 Problem JSON-serialized bytes."""
        if isinstance(content, Problem):
            p = content
        elif isinstance(content, dict):
            p = from_dict(content)
        elif isinstance(content, HTTPException):
            p = from_http_exception(content)
        elif isinstance(content, RequestValidationError):
            p = from_request_validation_error(content)
        elif isinstance(content, Exception):
            p = from_exception(content)
        else:
            p = Problem(
                status=500,
                title='Application Error',
                detail='Got unexpected content when trying to generate error response',
                content=str(content),
            )

        p.debug = self.debug

        # Dynamically set the response status_code to match
        # the status code of the Problem.
        self.status_code = p.status

        return p.to_bytes()


class Problem(Exception):
    """An RFC 7807 Problem exception.

    This models a "problem" as defined in RFC 7807 (https://tools.ietf.org/html/rfc7807).
    It is intended to be subclassed to create application-specific instances of
    problems which, when raised, can be trapped by the application error handler
    and converted into HTTP responses with properly-formatted JSON response bodies.

    Default values are applied to the `type`, `status`, and `title` field if
    they are left unspecified.

    It is generally not recommended to modify the Problem instance members
    post-initialization, but nothing prevents you from doing so if you need
    more granular control over how/when values are set.
    """

    def __init__(
            self,
            type: Optional[str] = None,
            title: Optional[str] = None,
            status: Optional[int] = None,
            detail: Optional[str] = None,
            instance: Optional[str] = None,
            **kwargs,
    ) -> None:
        self.type: str = type or 'about:blank'
        self.status: int = status or 500
        self.title: str = title or http.HTTPStatus(self.status).phrase
        self.detail: Optional[str] = detail
        self.instance: Optional[str] = instance
        self.kwargs: Dict = kwargs

        # The debug flag determines whether or not the response JSON is pretty-printed,
        # making it easier for humans to read while debugging.
        self.debug: bool = False

    def to_bytes(self) -> bytes:
        """Render the Problem as JSON-serialized bytes.

        Returns:
            The JSON-serialized bytes representing the Problem response.
        """
        if self.debug:
            return json.dumps(
                self.to_dict(),
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
            ).encode('utf-8')
        else:
            return json.dumps(
                self.to_dict(),
                ensure_ascii=False,
                allow_nan=False,
                indent=None,
                separators=(',', ':'),
            ).encode('utf-8')

    def to_dict(self) -> Dict[str, Any]:
        """Get a dictionary representation of the Problem response.

        Returns:
            A dictionary representation of the Problem exception. This can be serialized
            out to JSON and used as the response body.
        """
        d = {}

        # Update the problem dict with kwargs first. In the unlikely event that
        # a Problem instance has its kwargs supplemented with keys which conflict
        # with the keys defined in RFC7807, we do not want the kwargs to override.
        d.update(self.kwargs)

        if self.type:
            d['type'] = str(self.type)
        if self.title:
            d['title'] = str(self.title)
        if self.status:
            d['status'] = int(self.status)
        if self.detail:
            d['detail'] = str(self.detail)
        if self.instance:
            d['instance'] = str(self.instance)
        return d

    def __str__(self) -> str:
        return str(f'Problem:<{self.to_dict()}>')

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Problem):
            return False
        return self.__dict__ == other.__dict__


def from_dict(data: Dict[str, Any]) -> Problem:
    """Create a new Problem instance from a dictionary.

    This uses the dictionary as keyword arguments for the Problem constructor.
    If the given dictionary does not contain any fields matching those defined
    in the RFC7807 spec, it will use defaults where appropriate (e.g. status
    code 500) and use the dictionary members as supplemental context in the
    Problem response.

    Args:
        data: The dictionary to convert into a Problem exception.

    Returns:
        A new Problem instance populated from the dictionary fields.
    """
    return Problem(
        **data,
    )


def from_http_exception(exc: HTTPException) -> Problem:
    """Create a new Problem instance from an HTTPException.

    The Problem will take on the status code of the HTTPException and generate
    a title based on that status code. If the HTTPException specifies any details,
    those will be used as the problem details.

    Args:
        exc: The HTTPException to convert into a Problem exception.

    Returns:
        A new Problem instance populated from the HTTPException.
    """
    return Problem(
        status=exc.status_code,
        detail=exc.detail,
    )


def from_request_validation_error(exc: RequestValidationError) -> Problem:
    """Create a new Problem instance from a RequestValidationError.

    The Problem will take on a status code of 400 Bad Request, indicating that
    the user provided data which the server will not process. The title will
    be "Validation Error". The specifics of which fields failed validation
    checks are included as additional Problem context.

    Args:
        exc: The RequestValidationError to convert into a Problem exception.

    Returns:
         A new Problem instance populated from the RequestValidationError.
    """
    return Problem(
        title='Validation Error',
        status=400,
        detail='One or more user-provided parameters are invalid',
        errors=exc.errors(),
    )


def from_exception(exc: Exception) -> Problem:
    """Create a new Problem instance from a broad-class Exception.

    Converting a general Exception into a Problem is indicative of a server
    error, where some exception is not handled explicitly or not wrapped in
    a Problem/HTTPException.

    When creating a Problem from Exception, the Problem will always use the
    500 Server Error status code, however instead of "Server Error" as the
    title, "Unexpected Server Error" is used to indicate that an exception
    was not properly wrapped/raised.

    The exception class is provided as additional Problem context, and the
    exception message is used as Problem details.

    Args:
        exc: The general Exception to convert into a Problem exception.

    Returns:
        A new Problem instance populated from the Exception.
    """
    return Problem(
        title='Unexpected Server Error',
        status=500,
        detail=str(exc),
        exc_type=exc.__class__.__name__,
    )


def get_exception_handler(
        debug: bool = False,
        hooks: Optional[Sequence[Union[
            Callable[[Request, Exception], Any],
            Callable[[Request, Exception], Awaitable[Any]]
        ]]] = None,
) -> Callable:
    """A custom FastAPI exception handler constructor.

    The exception handler which this returns is used to return an RFC7807
    compliant ProblemResponse for the given exception.

    The constructor function lets you specify whether the application is running
    in debug mode, which will cause the error JSON to be pretty-printed for
    easier readability. Otherwise, the JSON response is serialized in a more
    compact format.

    Hooks can be specified for the handler as well. These hooks run before the
    exception is converted into a ProblemResponse and returned. Hooks must take
    a request (starlette.requests.Request) and an Exception as its arguments.
    If the hook raises an exception, the exception is ignored. Hooks can be used
    to add additional logging around exception handling, to collect application
    metrics for error counts, or for any other reason deemed suitable.

    Args:
        debug: Configure the handler for pretty-printing response JSON.
        hooks: Functions which are run prior to generating a response.
    """
    hooks = hooks or []

    async def exception_handler(request: Request, exc: Exception) -> ProblemResponse:
        nonlocal debug, hooks
        if hooks:
            for hook in hooks:
                try:
                    if asyncio.iscoroutinefunction(hook):
                        await hook(request, exc)
                    else:
                        hook(request, exc)
                except:  # noqa
                    # Ignore any exceptions raised by the hook. It is up to the
                    # developer to ensure hooks do not error, or that they log their
                    # own errors for visibility.
                    pass

        return ProblemResponse(exc, debug=debug)
    return exception_handler


def register(
    app: FastAPI,
    hooks: Optional[Sequence[Union[
        Callable[[Request, Exception], Any],
        Callable[[Request, Exception], Awaitable[Any]]
    ]]] = None,
) -> None:
    """Register the FastAPI RFC7807 middleware with a FastAPI application instance.

    This function registers three things:

    1. An exception handler for HTTPExceptions. This ensures that any HTTPException
       raised by the application is properly converted to an RFC7807 Problem response.
    2. An exception handler for RequestValidationError. This ensures that any validation
       errors (e.g. incorrect params) are formatted into an RFC7807 Problem response.
    3. ProblemMiddleware. This middleware handles all other exceptions raised by the
       application and converts them to RFC7807 Problem responses.

    It is important to note that the ProblemMiddleware which gets registered with
    the application overrides starlette's internal default ServerErrorMiddleware
    by capturing all exceptions before they make it to that handler. As such, this
    means that all errors should return as JSON, but also that previous behavior, e.g.
    of having debug tracebacks for errors displayed in HTML will no longer occur.

    If the FastAPI application is configured for debug mode, this will
    pretty-print the JSON output, making it more human-readable and easier
    to debug. Otherwise, the JSON response is serialized in a more compact
    format.

    Args:
        app: The FastAPI application instance to register with.
        hooks: Functions to run prior to returning a ProblemResponse.
    """
    _handler = get_exception_handler(debug=app.debug, hooks=hooks)

    app.add_exception_handler(HTTPException, _handler)
    app.add_exception_handler(RequestValidationError, _handler)
    app.add_middleware(ProblemMiddleware, debug=app.debug, hooks=hooks)


class ProblemMiddleware:
    """Middleware to catch all unhandled exceptions in the stack and return
    a corresponding RFC7807 JSON-formatted response.

    If 'debug' is set, the response JSON will be serialized in a more
    human-readable format, making it easier for debugging. Otherwise, the
    response JSON is serialized in a more compact format.
    """

    def __init__(
            self,
            app: ASGIApp,
            debug: bool = False,
            hooks: Optional[Sequence[Union[
                Callable[[Request, Exception], Any],
                Callable[[Request, Exception], Awaitable[Any]]
            ]]] = None,
    ) -> None:
        self.app: ASGIApp = app
        self.hooks = hooks or []
        self.debug: bool = debug

        self._handler = get_exception_handler(
            debug=self.debug,
            hooks=self.hooks,
        )

    # See: starlette.middleware.errors.ServerErrorMiddleware
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        response_started = False

        async def _send(message: Message) -> None:
            nonlocal response_started, send

            if message['type'] == 'http.response.start':
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, _send)
        except Exception as exc:
            if not response_started:
                response = await self._handler(Request(scope), exc)
                # response = await request_exception_handler(Request(scope), exc)
                await response(scope, receive, send)

            # Continue to raise the exception. This allows the exception to
            # be logged, or optionally allows test clients to raise the error
            # in test cases.
            raise exc from None
