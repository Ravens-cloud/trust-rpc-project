# trust_sockets/client.py
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

print(f"[DEBUG][client] TRUST_ID = {os.getenv('TRUST_ID')}")

import asyncio
from .protocol import perform_client_handshake, HandshakeError, send_msg, read_msg
from .rpc import RPCClient


async def simple_chat_main():
    """基础题目：演示一个简单的可信聊天客户端"""
    host = '127.0.0.1'
    port = 8888

    try:
        reader, writer = await asyncio.open_connection(host, port)

        # 执行握手
        await perform_client_handshake(reader, writer)
        print("Client: Connection trusted. You can now send messages.")

        # 消息循环
        while True:
            message = await asyncio.to_thread(input, "Enter message to send (or 'exit'): ")
            if message == 'exit':
                break

            await send_msg(writer, message.encode())

            response = await read_msg(reader)
            if response is None:
                print("Server closed connection.")
                break
            print(f"Client: Received echo: {response.decode()}")

        writer.close()
        await writer.wait_closed()

    except HandshakeError as e:
        print(f"Client: Could not connect. Reason: {e}")
    except ConnectionRefusedError:
        print("Client: Connection refused. Is the server running?")
    except Exception as e:
        print(f"Client: An error occurred: {e}")


async def rpc_demo_main():
    client = RPCClient('127.0.0.1', 8888)
    try:
        # 异步调用示例
        await client.connect()
        task1 = client._async_call("greet", "Alice")
        task2 = client._async_call("long_running_task", 2)
        results = await asyncio.gather(task1, task2)
        print(f"Async 'greet' result: {results[0]}")
        print(f"Async 'long_running_task' result: {results[1]}")
        try:
            await client._async_call("non_existent_function")
        except Exception as e:
            print(f"Async error test successful: {e}")
        await client.close()

        # 同步调用示例
        print("\n--- Testing Sync RPC Call ---")
        sync_client = RPCClient('127.0.0.1', 8888)
        result = sync_client.sync_call("greet", "Bob")
        print(f"Sync 'greet' result: {result}")
        try:
            sync_client.sync_call("greet", 123)
        except Exception as e:
            print(f"Sync error test successful: {e}")
        print("--- Sync Test Finished ---\n")

    except HandshakeError as e:
        print(f"Client: Could not connect. Reason: {e}")
    except Exception as e:
        print(f"Client: An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(rpc_demo_main())