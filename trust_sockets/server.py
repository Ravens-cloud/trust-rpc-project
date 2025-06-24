# trust_sockets/server.py

import os

if "PYTEST_CURRENT_TEST" not in os.environ:
    if not os.environ.get("TRUST_ID"):
        try:
            with open('.env') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, val = line.strip().split('=', 1)
                        os.environ.setdefault(key, val)
        except FileNotFoundError:
            pass

print(f"[DEBUG][server] TRUST_ID = {os.getenv('TRUST_ID')}")

import asyncio
import argparse
from .protocol import perform_server_handshake, HandshakeError, read_msg, send_msg, ConnectionClosedError
from .rpc import dispatch_rpc_call


async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info('peername')
    print(f"Server: Accepted connection from {addr}")

    try:
        await perform_server_handshake(reader, writer)
        print(f"Server: Connection from {addr} is now trusted. Waiting for RPC calls.")
        while not reader.at_eof():
            request_data = await read_msg(reader)
            if request_data is None:
                break

            response_data = await dispatch_rpc_call(request_data)
            await send_msg(writer, response_data)

    except HandshakeError as e:
        print(f"Server: Handshake with {addr} failed: {e}")
    except ConnectionClosedError:
        print(f"Server: Client {addr} closed connection unexpectedly.")
    except asyncio.IncompleteReadError:
        print(f"Server: Client {addr} disconnected abruptly.")
    except Exception as e:
        print(f"Server: An error occurred with {addr}: {e}")
    finally:
        print(f"Server: Closing connection with {addr}")
        writer.close()
        await writer.wait_closed()


async def main():
    # --- 恢复：使用 argparse 解析命令行参数 ---
    parser = argparse.ArgumentParser(description="Async Trusted RPC Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8888, help="Port to listen on (0 for dynamic port)")
    args = parser.parse_args()

    print(f"[SERVER START] TRUST_ID = {os.getenv('TRUST_ID')}")
    server = await asyncio.start_server(handle_connection, args.host, args.port)

    if not server.sockets:
        print("Server failed to start.")
        return

    actual_addr = server.sockets[0].getsockname()

    print(f"SERVING_ON::{actual_addr[0]}::{actual_addr[1]}", flush=True)
    print(f'Serving on {actual_addr}...')

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer is shutting down.")