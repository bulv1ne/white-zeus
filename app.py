import argparse
import asyncio
import logging
from urllib.parse import urlparse

URL = "https://example.com"
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
    replace_host = f"{hostname}:{u.port}" if u.port else hostname

    remote_reader, remote_writer = await asyncio.open_connection(
        hostname, port, ssl=ssl
    )

    await asyncio.gather(
        read_head(reader, remote_writer, replace_host=replace_host),
        send_file(remote_reader, writer),
    )

    if not writer.is_closing():
        if writer.can_write_eof():
            writer.write_eof()
        writer.close()

    if not remote_writer.is_closing():
        if remote_writer.can_write_eof():
            remote_writer.write_eof()
        remote_writer.close()

    await asyncio.gather(writer.wait_closed(), writer.wait_closed())


async def read_head(reader, writer, replace_host=None):
    pipeline = Pipeline(reader, writer)
    try:
        while not reader.at_eof():
            await pipeline.pipe_until(b"Host: ")
            if replace_host:
                # Empty the line
                host = await pipeline.read_until(b"\r\n")
                if host:
                    writer.write(f"{replace_host}\r\n".encode())
                    await writer.drain()
    except ConnectionResetError:
        print("Connection Reset Error")


class Pipeline:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.chunk = b""

    async def pipe_until(self, until):
        while not self.reader.at_eof():
            try:
                pos = self.chunk.index(until)
            except ValueError:
                # Drain chunk if possible until "until" is partially found
                data_stream, self.chunk = partial_find(self.chunk, until)
                if data_stream:
                    self.writer.write(data_stream)
                    await self.writer.drain()

                data = await self.reader.read(BUFFER_SIZE)
                self.chunk += data
            else:
                pos += len(until)
                self.writer.write(self.chunk[:pos])
                await self.writer.drain()
                self.chunk = self.chunk[pos:]
                return

    async def read_until(self, until):
        while not self.reader.at_eof():
            try:
                pos = self.chunk.index(until)
            except ValueError:
                data = await self.reader.read(BUFFER_SIZE)
                self.chunk += data
            else:
                pos += len(until)
                line = self.chunk[:pos]
                self.chunk = self.chunk[pos:]
                return line


async def send_file(reader, writer):
    try:
        while not reader.at_eof() and not writer.is_closing():
            data = await reader.read(BUFFER_SIZE)
            writer.write(data)
            await writer.drain()
    except ConnectionResetError:
        print("Connection Reset Error")


def partial_find(chunk, until):
    """Finds `until` in chunk and splits after `until`.
    If until is partially found at the end of the chunk,
    it will split right before the partially found string

    This function is used to consume as much of chunk as possible while
    still able to append to chunk
    """
    try:
        pos = chunk.index(until)
    except ValueError:
        pass
    else:
        pos += len(until)
        return chunk[:pos], chunk[pos:]

    chunk_len = len(chunk)
    until_len = len(until)
    chunk_range = range(max(0, chunk_len - until_len), chunk_len)
    until_range = range(min(until_len, chunk_len), 0, -1)

    for chunk_pos, until_pos in zip(chunk_range, until_range):
        if chunk[chunk_pos:] == until[:until_pos]:
            return chunk[:chunk_pos], chunk[chunk_pos:]
    return chunk, b""


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
