import asyncio
import h11

from apps import echo_app


async def main(run_app, host: str, port: int) -> None:
    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        # read all the request
        # data = await reader.readuntil(b"\r\n\r\n")
        lines = []
        line = b""
        while line.strip() or not lines:
            line = await reader.readline()
            lines.append(line)
        data = b"".join(lines)
        connection = h11.Connection(our_role=h11.SERVER)
        connection.receive_data(data)
        request: h11.Request = connection.next_event()
        body_size = 0
        for header in request.headers:
            if header[0].decode().lower() == "content-length":
                body_size = int(header[1].decode())
        if b'?' in request.target:
            path, query = request.target.split(b'?')
        else:
            path = request.target
            query = b""
        scope = {
            'type': 'http',
            'asgi': {'version': '3.0', 'spec_version': '2.3'},
            'http_version': request.http_version.decode(),
            'server': (host, port),
            'scheme': 'http',
            'method': request.method.decode(),
            'path': path.decode(),
            'query_string': query,
            'headers': request.headers,
            'state': {}
        }
        status_code = None
        headers = None
        body = b""

        async def receive():
            connection.receive_data(await reader.read(body_size + 10))
            next = connection.next_event()
            if isinstance(next, h11.Data):
                return {'type': 'http.request', 'body': next.data, 'more_body': False}
            else:
                return {'type': 'http.request', 'body': b"", 'more_body': False}

        async def send(event):
            nonlocal status_code, headers, body
            if event['type'] == "http.response.start":
                status_code = event["status"]
                headers = event["headers"]
            elif event["type"] == "http.response.body":
                body = event["body"]
            else:
                print("unknown event", event)

        await run_app(scope, receive, send)
        response = h11.Response(headers=headers, status_code=status_code)
        data = connection.send(response)
        print(f"Send: {data}")
        writer.write(data)
        writer.write(body)
        await writer.drain()

        writer.close()
        await writer.wait_closed()

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
            task = asyncio.create_task(run_app(scope, receive, send))
            await fut
        except:
            print("app doesn`t support startup")

    await startup()

    server = await asyncio.start_server(
        handle, host, port)

    addresses = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addresses}')

    async with server:
        await server.serve_forever()


def run(app, host, port):
    asyncio.run(main(app, host, port))


if __name__ == '__main__':
    run(echo_app, '0.0.0.0', 8080)
