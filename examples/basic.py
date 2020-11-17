"""
A basic example application showcasing fastapi_rfc7807

Run from the `examples` directory with:
    $ uvicorn basic:app
"""

from fastapi import FastAPI

from fastapi_rfc7807.middleware import register, Problem


app = FastAPI()
register(app)


class AuthenticationError(Problem):
    """An example of how to create a custom subclass of the Problem error.

    This class also defines additional headers which should be sent with
    the error response.
    """

    headers = {
        'WWW-Authenticate': 'Bearer',
    }

    def __init__(self, msg: str) -> None:
        super(AuthenticationError, self).__init__(
            status=401,
            detail=msg,
        )


@app.get('/')
async def root():
    return {'message': 'Hello World'}


@app.get('/auth')
async def custom():
    raise AuthenticationError('user is unauthenticated')


@app.get('/error')
async def error():
    raise ValueError('something went wrong')


# Response:
#
# $ curl localhost:8000/error
# {"exc_type":"ValueError","type":"about:blank","title":"Unexpected Server Error","status":500,"detail":"something went wrong"}
