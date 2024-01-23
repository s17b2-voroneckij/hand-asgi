import starlette.requests
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route


async def homepage(request):
    return JSONResponse({'hello': 'world'})


async def echo(request: starlette.requests.Request):
    return PlainTextResponse((await request.body()).decode())

routes = [
    Route("/", endpoint=homepage),
    Route("/", methods=["POST"], endpoint=echo)
]

echo_app = Starlette(debug=True, routes=routes)
