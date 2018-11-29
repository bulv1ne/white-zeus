import argparse
import asyncio
from datetime import datetime
from itertools import repeat

import aiohttp

stats = []


async def fetch(session, url):
    now = datetime.now()
    try:
        async with session.get(url) as response:
            return await response.text()
    finally:
        stats.append(datetime.now() - now)


async def main():
    parser = argparse.ArgumentParser(description="Simple http benchmark")
    parser.add_argument("url")
    parser.add_argument(
        "--number", "-n", type=int, default=100, help="Number of requests"
    )
    parser.add_argument("--concurrency", "-c", type=int, default=10, help="Concurrency")

    args = parser.parse_args()

    pending = set()
    fetch_iter = repeat(lambda: fetch(session, args.url), args.number)

    start = datetime.now()
    async with aiohttp.ClientSession() as session:
        while True:
            for f, _ in zip(fetch_iter, range(args.concurrency - len(pending))):
                pending.add(f())

            if not pending:
                break
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
    diff = (datetime.now() - start) / args.number
    reqps = 1 / diff.total_seconds()
    print(f"Requests per second: {reqps}")

    # for s in sorted(stats):
    # print(s)


if __name__ == "__main__":
    asyncio.run(main())
