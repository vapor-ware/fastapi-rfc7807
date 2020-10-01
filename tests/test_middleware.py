
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.requests import Request
from fastapi.responses import PlainTextResponse, Response
from fastapi.testclient import TestClient
from pydantic.error_wrappers import ErrorWrapper

from fastapi_rfc7807 import middleware


class TestProblemResponse:

    def test_render_problem(self):
        resp = middleware.ProblemResponse(
            middleware.Problem(),
        )

        assert resp.media_type == 'application/problem+json'
        assert resp.debug is False
        assert resp.status_code == 500
        assert json.loads(resp.body) == {
            'type': 'about:blank',
            'status': 500,
            'title': 'Internal Server Error',
        }

    def test_render_dict(self):
        resp = middleware.ProblemResponse(
            {'foo': 'bar'},
        )

        assert resp.media_type == 'application/problem+json'
        assert resp.debug is False
        assert resp.status_code == 500
        assert json.loads(resp.body) == {
            'type': 'about:blank',
            'status': 500,
            'title': 'Internal Server Error',
            'foo': 'bar',
        }

    def test_render_http_exception(self):
        resp = middleware.ProblemResponse(
            HTTPException(400, 'test error'),
        )

        assert resp.media_type == 'application/problem+json'
        assert resp.debug is False
        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'type': 'about:blank',
            'status': 400,
            'title': 'Bad Request',
            'detail': 'test error',
        }

    def test_render_request_validation_error(self):
        resp = middleware.ProblemResponse(
            RequestValidationError(
                errors=[ErrorWrapper(ValueError('foo'), 'bar')],
            ),
        )

        assert resp.media_type == 'application/problem+json'
        assert resp.debug is False
        assert resp.status_code == 400
        assert json.loads(resp.body) == {
            'type': 'about:blank',
            'status': 400,
            'title': 'Validation Error',
            'detail': 'One or more user-provided parameters are invalid',
            'errors': [
                {
                    'loc': ['bar'],
                    'msg': 'foo',
                    'type': 'value_error',
                },
            ],
        }

    def test_render_exception(self):
        resp = middleware.ProblemResponse(
            ValueError('test error'),
        )

        assert resp.media_type == 'application/problem+json'
        assert resp.debug is False
        assert resp.status_code == 500
        assert json.loads(resp.body) == {
            'type': 'about:blank',
            'status': 500,
            'title': 'Unexpected Server Error',
            'detail': 'test error',
            'exc_type': 'ValueError',
        }

    def test_render_other(self):
        resp = middleware.ProblemResponse(
            ['some', 'other', 'data'],
        )

        assert resp.media_type == 'application/problem+json'
        assert resp.debug is False
        assert resp.status_code == 500
        assert json.loads(resp.body) == {
            'type': 'about:blank',
            'status': 500,
            'title': 'Application Error',
            'detail': 'Got unexpected content when trying to generate error response',
            'content': "['some', 'other', 'data']",
        }


class TestProblem:

    def test_init(self):
        problem = middleware.Problem()

        assert problem.type == 'about:blank'
        assert problem.status == 500
        assert problem.title == 'Internal Server Error'
        assert problem.detail is None
        assert problem.instance is None
        assert problem.kwargs == {}
        assert problem.debug is False

    def test_to_bytes(self):
        problem = middleware.Problem()
        assert problem.to_bytes() == b'{"type":"about:blank","title":"Internal Server Error","status":500}'  # noqa

    def test_to_bytes_debug(self):
        problem = middleware.Problem()
        problem.debug = True
        assert problem.to_bytes() == b'{\n  "type": "about:blank",\n  "title": "Internal Server Error",\n  "status": 500\n}'  # noqa

    def test_to_dict_all_values(self):
        problem = middleware.Problem(
            type='problem-type',
            title='Problem',
            status=500,
            detail='Something happened',
            instance='foo',
            other='bar',
        )
        assert problem.to_dict() == {
            'type': 'problem-type',
            'title': 'Problem',
            'status': 500,
            'detail': 'Something happened',
            'instance': 'foo',
            'other': 'bar',
        }

    def test_to_dict_default_values(self):
        problem = middleware.Problem()
        assert problem.to_dict() == {
            'type': 'about:blank',
            'title': 'Internal Server Error',
            'status': 500,
        }

    def test_str(self):
        assert str(middleware.Problem()) == "Problem:<{'type': 'about:blank', 'title': 'Internal Server Error', 'status': 500}>"  # noqa


class TestProblemMiddleware:

    @pytest.fixture(scope='class')
    def app(self) -> FastAPI:
        app = FastAPI()
        app.add_middleware(middleware.ProblemMiddleware, debug=False)

        @app.get('/foo/{value}')
        async def foo(value: int):
            return PlainTextResponse('foo')

        @app.get('/valueerror')
        async def valueerror():
            raise ValueError('test error')

        @app.get('/httperror')
        async def httperror():
            raise HTTPException(404, 'test error')

        @app.get('/problem')
        async def problem():
            raise middleware.Problem()

        return app

    @pytest.fixture()
    def client(self, app) -> TestClient:
        return TestClient(app, raise_server_exceptions=False)

    def test_init(self):
        app = FastAPI()
        pm = middleware.ProblemMiddleware(app, debug=True)

        assert pm.debug is True
        assert pm.app == app

    def test_call_no_exception(self, client):
        async def app(scope, receive, send):
            resp = Response(b"", status_code=204)
            return await resp(scope, receive, send)

        app = middleware.ProblemMiddleware(app)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get('/')

        assert response.status_code == 204
        assert response.content.decode() == ''

    def test_call_problem_exception(self):
        async def app(scope, receive, send):
            raise middleware.Problem()

        app = middleware.ProblemMiddleware(app)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get('/')

        assert response.status_code == 500
        assert response.headers['Content-Type'] == 'application/problem+json'
        assert response.json() == {
            'status': 500,
            'title': 'Internal Server Error',
            'type': 'about:blank',
        }

    def test_call_http_exception(self, client):
        async def app(scope, receive, send):
            raise HTTPException(404, 'test error')

        app = middleware.ProblemMiddleware(app)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get('/')

        assert response.status_code == 404
        assert response.headers['Content-Type'] == 'application/problem+json'
        assert response.json() == {
            'status': 404,
            'title': 'Not Found',
            'type': 'about:blank',
            'detail': 'test error',
        }

    def test_call_request_validation_error(self, client):
        async def app(scope, receive, send):
            raise RequestValidationError(
                errors=[ErrorWrapper(ValueError('foo'), 'bar')],
            )

        app = middleware.ProblemMiddleware(app)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get('/')

        assert response.status_code == 400
        assert response.headers['Content-Type'] == 'application/problem+json'
        assert response.json() == {
            'status': 400,
            'title': 'Validation Error',
            'type': 'about:blank',
            'detail': 'One or more user-provided parameters are invalid',
            'errors': [
                {
                    'loc': ['bar'],
                    'msg': 'foo',
                    'type': 'value_error',
                },
            ],
        }

    def test_call_exception(self, client):
        async def app(scope, receive, send):
            raise ValueError('test error')

        app = middleware.ProblemMiddleware(app)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get('/')

        assert response.status_code == 500
        assert response.headers['Content-Type'] == 'application/problem+json'
        assert response.json() == {
            'status': 500,
            'title': 'Unexpected Server Error',
            'type': 'about:blank',
            'detail': 'test error',
            'exc_type': 'ValueError',
        }


def test_from_dict():
    problem = middleware.from_dict({
        'type': 'test-problem',
        'title': 'Test Problem',
        'status': 500,
        'detail': 'a test problem occurred',
        'instance': 'testproblem',
    })

    assert problem == middleware.Problem(
        type='test-problem',
        title='Test Problem',
        status=500,
        detail='a test problem occurred',
        instance='testproblem',
    )


def test_from_dict_empty():
    problem = middleware.from_dict({})

    assert problem == middleware.Problem(
        type='about:blank',
        title='Internal Server Error',
        status=500,
    )


def test_from_dict_with_extras():
    problem = middleware.from_dict({
        'type': 'test-problem',
        'title': 'Test Problem',
        'status': 500,
        'key1': 'extra',
        'key2': {
            'foo': ['bar', 'baz']
        }
    })

    assert problem == middleware.Problem(
        type='test-problem',
        title='Test Problem',
        status=500,
        key1='extra',
        key2={'foo': ['bar', 'baz']}
    )


def test_from_http_exception():
    problem = middleware.from_http_exception(HTTPException(
        status_code=401,
        detail='test http error',
    ))

    assert problem == middleware.Problem(
        type='',
        title='',
        status=401,
        detail='test http error',
    )


def test_from_request_validation_error():
    problem = middleware.from_request_validation_error(RequestValidationError(
        errors=[
            ErrorWrapper(ValueError('foo'), 'here'),
            ErrorWrapper(ValueError('bar'), 'there'),
        ],
    ))

    assert problem == middleware.Problem(
        type='',
        title='Validation Error',
        status=400,
        detail='One or more user-provided parameters are invalid',
        errors=[
            {
                'loc': ('here',),
                'msg': 'foo',
                'type': 'value_error',
            },
            {
                'loc': ('there',),
                'msg': 'bar',
                'type': 'value_error',
            },
        ],
    )


def test_from_exception():
    problem = middleware.from_exception(ValueError('test error'))

    assert problem == middleware.Problem(
        type='',
        title='Unexpected Server Error',
        status=500,
        detail='test error',
        exc_type='ValueError',
    )


@pytest.mark.asyncio
async def test_get_exception_handler():
    handler = middleware.get_exception_handler()

    resp = await handler(
        request=Request(scope={
            'type': 'http',
            'app': FastAPI()},
        ),
        exc=ValueError('test error'),
    )

    assert isinstance(resp, middleware.ProblemResponse)
    assert resp.debug is False
    assert resp.body == b'{"exc_type":"ValueError","type":"about:blank","title":"Unexpected Server Error","status":500,"detail":"test error"}'  # noqa


@pytest.mark.asyncio
async def test_get_exception_handler_debug():
    handler = middleware.get_exception_handler(debug=True)

    resp = await handler(
        request=Request(scope={
            'type': 'http',
            'app': FastAPI(debug=True)
        }),
        exc=ValueError('test error'),
    )

    assert isinstance(resp, middleware.ProblemResponse)
    assert resp.debug is True
    assert resp.body == b'{\n  "exc_type": "ValueError",\n  "type": "about:blank",\n  "title": "Unexpected Server Error",\n  "status": 500,\n  "detail": "test error"\n}'  # noqa


@pytest.mark.asyncio
async def test_get_exception_handler_pre_hooks_ok():
    hook1 = AsyncMock()
    hook2 = MagicMock()
    hook3 = MagicMock()
    handler = middleware.get_exception_handler(pre_hooks=[hook1, hook2, hook3])

    resp = await handler(
        request=Request(scope={
            'type': 'http',
            'app': FastAPI()},
        ),
        exc=ValueError('test error'),
    )

    assert isinstance(resp, middleware.ProblemResponse)
    assert resp.debug is False
    assert resp.body == b'{"exc_type":"ValueError","type":"about:blank","title":"Unexpected Server Error","status":500,"detail":"test error"}'  # noqa

    hook1.assert_awaited_once()
    hook2.assert_called_once()
    hook3.assert_called_once()


@pytest.mark.asyncio
async def test_get_exception_handler_pre_hooks_bad_hook():
    # hook has too few arguments
    handler = middleware.get_exception_handler(pre_hooks=[lambda x: x])

    with pytest.raises(TypeError) as err:
        await handler(
            request=Request(scope={
                'type': 'http',
                'app': FastAPI()},
            ),
            exc=ValueError('test error'),
        )

    assert 'takes 1 positional argument but 2 were given' in str(err.value)


@pytest.mark.asyncio
async def test_get_exception_handler_pre_hooks_error():
    hook1 = AsyncMock()
    hook2 = MagicMock()
    hook3 = MagicMock(side_effect=ValueError('hook error'))

    handler = middleware.get_exception_handler(pre_hooks=[hook1, hook2, hook3])

    with pytest.raises(ValueError) as err:
        await handler(
            request=Request(scope={
                'type': 'http',
                'app': FastAPI()},
            ),
            exc=ValueError('test error'),
        )

    assert 'hook error' == str(err.value)

    hook1.assert_awaited_once()
    hook2.assert_called_once()
    hook3.assert_called_once()


@pytest.mark.asyncio
async def test_get_exception_handler_post_hooks_ok():
    hook1 = AsyncMock()
    hook2 = MagicMock()
    hook3 = MagicMock()
    handler = middleware.get_exception_handler(post_hooks=[hook1, hook2, hook3])

    resp = await handler(
        request=Request(scope={
            'type': 'http',
            'app': FastAPI()},
        ),
        exc=ValueError('test error'),
    )

    assert isinstance(resp, middleware.ProblemResponse)
    assert resp.debug is False
    assert resp.body == b'{"exc_type":"ValueError","type":"about:blank","title":"Unexpected Server Error","status":500,"detail":"test error"}'  # noqa

    hook1.assert_awaited_once()
    hook2.assert_called_once()
    hook3.assert_called_once()


@pytest.mark.asyncio
async def test_get_exception_handler_post_hooks_bad_book():
    # hook has too few arguments
    handler = middleware.get_exception_handler(post_hooks=[lambda x: x])

    with pytest.raises(TypeError) as err:
        await handler(
            request=Request(scope={
                'type': 'http',
                'app': FastAPI()},
            ),
            exc=ValueError('test error'),
        )

    assert 'takes 1 positional argument but 3 were given' in str(err.value)


@pytest.mark.asyncio
async def test_get_exception_handler_post_hooks_error():
    hook1 = AsyncMock()
    hook2 = MagicMock()
    hook3 = MagicMock(side_effect=ValueError('hook error'))

    handler = middleware.get_exception_handler(post_hooks=[hook1, hook2, hook3])

    with pytest.raises(ValueError) as err:
        await handler(
            request=Request(scope={
                'type': 'http',
                'app': FastAPI()},
            ),
            exc=ValueError('test error'),
        )

    assert 'hook error' == str(err.value)

    hook1.assert_awaited_once()
    hook2.assert_called_once()
    hook3.assert_called_once()


def test_register():
    app = FastAPI()
    assert len(app.exception_handlers) == 2  # default handlers
    assert len(app.user_middleware) == 0
    orig_handlers = app.exception_handlers.copy()

    middleware.register(app)

    assert len(app.exception_handlers) == 2
    assert len(app.user_middleware) == 1
    for key in app.exception_handlers:
        assert app.exception_handlers[key] != orig_handlers[key]
