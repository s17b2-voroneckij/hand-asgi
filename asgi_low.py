import asyncio

import h11


class Protocol(asyncio.Protocol):
    def __init__(self, app, host, port):
        self.app = app
        self.host = host
        self.port = port
        self.tasks = []

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(peername))
        self.transport = transport
        self.queue = asyncio.Queue()
        self.connection = h11.Connection(our_role=h11.SERVER)
        self.task = None

        async def receive():
            return await self.queue.get()

        async def send(event):
            if event['type'] == "http.response.start":
                status_code = event["status"]
                headers = event["headers"]
                response = h11.Response(headers=headers, status_code=status_code)
                data = self.connection.send(response)
                self.transport.write(data)
            elif event["type"] == "http.response.body":
                body = event["body"]
                self.transport.write(body)
                self.transport.close()
            else:
                print("unknown event", event)

        self.receive = receive
        self.send = send

    def data_received(self, data: bytes):
        connection = self.connection
        connection.receive_data(data)
        next_event = connection.next_event()
        if isinstance(next_event, h11.Request):
            if b'?' in next_event.target:
                path, query = next_event.target.split(b'?')
            else:
                path = next_event.target
                query = b""
            scope = {
                'type': 'http',
                'asgi': {'version': '3.0', 'spec_version': '2.3'},
                'http_version': next_event.http_version.decode(),
                'server': (self.host, self.port),
                'scheme': 'http',
                'method': next_event.method.decode(),
                'path': path.decode(),
                'query_string': query,
                'headers': next_event.headers,
                'state': {}
            }
            self.task = asyncio.create_task(self.app(scope, self.receive, self.send))
        elif isinstance(next_event, h11.Data):
            self.tasks.append(asyncio.create_task(self.queue.put({'type': 'http.request', 'body': next_event.data, 'more_body': False})))
        else:
            print("unclear event", type(next_event))


async def main(app, host, port):
    # Get a reference to the event loop as we plan to use
    # low-level APIs.
    loop = asyncio.get_running_loop()
    startup_task = None

    async def startup():
        receive_count = 0
        fut = asyncio.Future()
        async def receive():
            nonlocal receive_count
            receive_count += 1
            if receive_count == 1:
                fut.set_result(True)
                return {'type': 'lifespan.startup'}
            else:
                await asyncio.sleep(1000000000)

        async def send(event):
            pass

        scope = {'type': 'lifespan', 'asgi': {'version': '3.0', 'spec_version': '2.0'}}

        try:
            nonlocal startup_task
            startup_task = asyncio.create_task(app(scope, receive, send))
            await fut
        except:
            print("app doesn`t support startup")

    await startup()

    server = await loop.create_server(
        lambda: Protocol(app, host, port),
        host, port)

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    from apps import echo_app

    asyncio.run(main(echo_app, "0.0.0.0", 8080))