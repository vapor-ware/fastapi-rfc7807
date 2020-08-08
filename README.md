# fastapi-rfc7807

[FastAPI](https://fastapi.tiangolo.com/) middleware which translates server-side exceptions
into [RFC-7807](https://tools.ietf.org/html/rfc7807) compliant problem detail error responses.

## Installation

`fastapi_rfc7807` requires Python 3.6+

```
pip install fastapi_rfc7807
```

## Usage

Below is a simple example which shows the bare minimum needed to configure a FastAPI application
with `fastapi_rfc7807`.

```python
from fastapi import FastAPI 
from fastapi_rfc7807 import middleware

app = FastAPI()
middleware.register(app)


@app.get('/error')
async def error():
    raise ValueError('something went wrong')

```

The resulting error returned from the server looks like:

```console
$ curl localhost:8000/error
{"exc_type":"ValueError","type":"about:blank","title":"Unexpected Server Error","status":500,"detail":"something went wrong"}
```

See the [examples](examples) directory for additional examples.
