import asyncio

async def f():
    await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(f())