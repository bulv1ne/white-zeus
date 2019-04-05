async def close_writer(writer):
    if not writer.is_closing():
        if writer.can_write_eof():
            writer.write_eof()
        writer.close()
    await writer.wait_closed()


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
