import argparse
import asyncio
import logging
from urllib.parse import urlparse

from .utils import close_writer

URL = "http://127.0.0.1:8080"
BUFFER_SIZE = 1024


async def main():
    parser = argparse.ArgumentParser(description="White Zeus server")
    parser.add_argument("--host", default="127.0.0.1", help="Default: 127.0.0.1")
    parser.add_argument("--port", "-p", default=8080, type=int, help="Default: 8080")
    args = parser.parse_args()

    server = await asyncio.start_server(proxy, args.host, args.port)

    addr = server.sockets[0].getsockname()
    print(f"Serving on {addr}")

    async with server:
        await server.serve_forever()


async def proxy(reader, writer):
    u = urlparse(URL)
    hostname = u.hostname
    port = u.port or (443 if u.scheme == "https" else 80)
    ssl = u.scheme == "https"
    # replace_host = f"{hostname}:{u.port}" if u.port else hostname

    reader_pipeline = Pipeline(reader)
    pre_host, host = await read_host(reader_pipeline)

    if not host:
        await close_writer(writer)
        return

    remote_reader, remote_writer = await asyncio.open_connection(
        hostname, port, ssl=ssl
    )

    print(host.decode())
    remote_writer.write(b"".join([pre_host, host, b"\r\n"]))
    await remote_writer.drain()

    await asyncio.gather(
        reader_pipeline.send_file(remote_writer),
        Pipeline(remote_reader).send_file(writer),
    )


async def read_host(pipeline_reader, replace_host=None):
    try:
        buffer = await pipeline_reader.read_until(b"Host: ")
        host = await pipeline_reader.read_until(b"\r\n")
        if host:
            host = host[:-2]
        return buffer, host
    except ConnectionResetError:
        print("Connection Reset Error")


class Pipeline:
    def __init__(self, reader):
        self.reader = reader
        self.chunk = b""

    async def read_until(self, until):
        while not self.reader.at_eof():
            try:
                pos = self.chunk.index(until)
            except ValueError:
                try:
                    data = await asyncio.wait_for(
                        self.reader.read(BUFFER_SIZE), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                self.chunk += data
            else:
                pos += len(until)
                line = self.chunk[:pos]
                self.chunk = self.chunk[pos:]
                return line
        return b""

    async def send_file(self, writer):
        try:
            if self.chunk and not writer.is_closing():
                writer.write(self.chunk)
                await writer.drain()
            while not self.reader.at_eof() and not writer.is_closing():
                try:
                    data = await asyncio.wait_for(
                        self.reader.read(BUFFER_SIZE), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    pass
                else:
                    writer.write(data)
                    await writer.drain()
        except ConnectionResetError:
            print("Connection Reset Error")
        finally:
            await close_writer(writer)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
