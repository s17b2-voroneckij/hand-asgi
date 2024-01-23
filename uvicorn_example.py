import starlette.requests
import uvicorn
from starlette.responses import PlainTextResponse


app = PlainTextResponse("hello, world")

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


async def homepage(request):
    return JSONResponse({'hello': 'world'})


async def echo(request: starlette.requests.Request):
    return PlainTextResponse((await request.body()).decode())

routes = [
    Route("/", endpoint=homepage),
    Route("/", methods=["POST"], endpoint=echo)
]

app = Starlette(debug=True, routes=routes)


async def my_app(scope, receive, send):
    async def receive_wrapper(*args, **kwargs):
        print("receive called with args: ", args, kwargs)
        ret = await receive(*args, **kwargs)
        print("receive result", ret)
        return ret

    async def send_wrapper(*args, **kwargs):
        print("send called with args: ", args, kwargs)
        await send(*args, **kwargs)

    print("my app called with scope", scope)
    await app(scope, receive_wrapper, send_wrapper)


if __name__ == "__main__":
    uvicorn.run(my_app, host="0.0.0.0", port=8080)
