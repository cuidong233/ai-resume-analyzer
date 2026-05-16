import uvicorn

from app.main import app


def handler(environ, start_response):
    from a2wsgi import ASGIMiddleware

    return ASGIMiddleware(app)(environ, start_response)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
