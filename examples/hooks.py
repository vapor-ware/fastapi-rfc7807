"""
A basic example application showcasing fastapi_rfc7807 with
simple hooks configured.

Run from the `examples` directory with:
    $ uvicorn hooks:app
"""

from fastapi import FastAPI

from fastapi_rfc7807.middleware import register


def print_error(request, exc):
    print(exc)


app = FastAPI()
register(app, hooks=[print_error])


@app.get('/error')
async def error():
    raise ValueError('something went wrong')


# Response:
#
# $ curl localhost:8000/error
# {"exc_type":"ValueError","type":"about:blank","title":"Unexpected Server Error","status":500,"detail":"something went wrong"}

# In application logs, the error gets printed
#
# INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
# something went wrong
# ...
