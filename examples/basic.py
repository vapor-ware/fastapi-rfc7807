"""
A basic example application showcasing fastapi_rfc7807

Run from the `examples` directory with:
    $ uvicorn basic:app
"""

from fastapi import FastAPI

from fastapi_rfc7807.middleware import register


app = FastAPI()
register(app)


@app.get('/')
async def root():
    return {'message': 'Hello World'}


@app.get('/error')
async def error():
    raise ValueError('something went wrong')


# Response:
#
# $ curl localhost:8000/error
# {"exc_type":"ValueError","type":"about:blank","title":"Unexpected Server Error","status":500,"detail":"something went wrong"}
