# trust_sockets/protocol.py
import asyncio
import struct
import hashlib
import os
import secrets
from typing import Optional

# 消息头部，包含4字节的长度信息
HEADER_FORMAT = "!I"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
ENCODING = 'utf-8'


# 自定义异常
class HandshakeError(Exception):
    pass


class ConnectionClosedError(Exception):
    pass


async def read_msg(reader: asyncio.StreamReader) -> Optional[bytes]:
    """从流中读取一个完整的消息（处理消息分包）"""
    header = await reader.readexactly(HEADER_SIZE)
    if not header:
        return None

    msg_len = struct.unpack(HEADER_FORMAT, header)[0]

    if msg_len == 0:
        return b''

    data = await reader.readexactly(msg_len)
    return data


async def send_msg(writer: asyncio.StreamWriter, data: bytes):
    """向流中写入一个完整的消息（添加长度头部）"""
    header = struct.pack(HEADER_FORMAT, len(data))
    writer.write(header + data)
    await writer.drain()


async def perform_server_handshake(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    trust_id = os.environ.get("TRUST_ID")
    print(f"[DEBUG][server pid={os.getpid()}] perform_server_handshake: TRUST_ID='{trust_id}'")
    if not trust_id:
        raise HandshakeError("Server TRUST_ID not set.")

    # 生成并发送 challenge
    challenge = secrets.token_hex(16).encode(ENCODING)
    await send_msg(writer, challenge)
    print("Server: Sent challenge.")
    # 接收 response
    response_from_client = await read_msg(reader)
    if response_from_client is None:
        raise ConnectionClosedError("Client closed connection during handshake.")
    print("Server: Received response.")
    # 计算期望 response
    hasher = hashlib.sha256()
    hasher.update(challenge)
    hasher.update(trust_id.encode(ENCODING))
    expected_response = hasher.digest()
    if expected_response != response_from_client:
        await send_msg(writer, b"FAIL")
        raise HandshakeError("TRUST_ID mismatch. Handshake failed.")
    await send_msg(writer, b"OK")
    print("Server: Handshake successful.")

async def perform_client_handshake(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    # 调试：打印实际读取到的 TRUST_ID
    import os, sys
    trust_id = os.environ.get("TRUST_ID")
    print(f"[DEBUG][client pid={os.getpid()}] perform_client_handshake: TRUST_ID='{trust_id}'")
    if not trust_id:
        raise HandshakeError("Client TRUST_ID not set.")
    # 接收 challenge
    challenge = await read_msg(reader)
    if challenge is None:
        raise ConnectionClosedError("Server closed connection during handshake.")
    print("Client: Received challenge.")
    # 计算并发送 response
    hasher = hashlib.sha256()
    hasher.update(challenge)
    hasher.update(trust_id.encode(ENCODING))
    response_to_server = hasher.digest()
    await send_msg(writer, response_to_server)
    print("Client: Sent response.")
    # 接收结果
    result = await read_msg(reader)
    if result != b"OK":
        raise HandshakeError("Server rejected connection. TRUST_ID might be incorrect.")
    print("Client: Handshake successful.")