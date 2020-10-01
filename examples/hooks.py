"""
A basic example application showcasing fastapi_rfc7807 with
simple hooks configured.

Run from the `examples` directory with:
    $ uvicorn hooks:app
"""

from fastapi import FastAPI, Request, Response

from fastapi_rfc7807.middleware import register


def print_error(request: Request, exc: Exception) -> None:
    print(exc)


def add_response_header(request: Request, response: Response, exc: Exception) -> None:
    response.headers['X-Custom-Header'] = 'foobar'


app = FastAPI()
register(
    app=app,
    pre_hooks=[print_error],
    post_hooks=[add_response_header],
)


@app.get('/error')
async def error():
    raise ValueError('something went wrong')


# Response:
#
# $ curl -i localhost:8000/error
# HTTP/1.1 200 OK
# date: Wed, 30 Sep 2020 20:43:32 GMT
# server: uvicorn
# content-length: 125
# content-type: application/problem+json
# x-custom-header: foobar
#
# {"exc_type":"ValueError","type":"about:blank","title":"Unexpected Server Error","status":500,"detail":"something went wrong"}

# In application logs, the error gets printed
#
# INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
# something went wrong
# ...
