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

    pre_host, host, post_host = await read_host(reader)

    if not host:
        await close_writer(writer)
        return

    remote_reader, remote_writer = await asyncio.open_connection(
        hostname, port, ssl=ssl
    )

    print(host.decode())
    remote_writer.write(b"".join([pre_host, replace_host.encode(), b"\r\n", post_host]))
    await remote_writer.drain()

    await asyncio.gather(
        send_file(reader, remote_writer), send_file(remote_reader, writer)
    )


async def close_writer(writer):
    if not writer.is_closing():
        if writer.can_write_eof():
            writer.write_eof()
        writer.close()
    await writer.wait_closed()


async def read_head(reader, writer, replace_host=None):
    pipeline = Pipeline(reader, writer)
    try:
        while not reader.at_eof():
            await pipeline.pipe_until(b"Host: ")
            host = await pipeline.read_until(b"\r\n")
            # host is None when reader is at_eof
            if host:
                # print(host[:-2])
                if replace_host:
                    host = f"{replace_host}\r\n".encode()
                writer.write(host)
                await writer.drain()
    except ConnectionResetError:
        print("Connection Reset Error")
    finally:
        await close_writer(writer)


async def read_host(reader, replace_host=None):
    pipeline = Pipeline(reader, None)
    try:
        if not reader.at_eof():
            buffer = await pipeline.read_until(b"Host: ")
            host = await pipeline.read_until(b"\r\n")
            if host:
                host = host[:-2]
            return buffer, host, pipeline.chunk
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
            try:
                data = await asyncio.wait_for(reader.read(BUFFER_SIZE), timeout=1.0)
            except asyncio.TimeoutError:
                pass
            else:
                writer.write(data)
                await writer.drain()
    except ConnectionResetError:
        print("Connection Reset Error")
    finally:
        await close_writer(writer)


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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
