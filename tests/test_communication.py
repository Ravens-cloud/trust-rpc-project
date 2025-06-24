# tests/test_communication.py
import pytest
import pytest_asyncio
import asyncio
import os
import sys
from trust_sockets.rpc import RPCClient
from trust_sockets.protocol import HandshakeError

# 定义测试用的常量
HOST = "127.0.0.1"
VALID_TRUST_ID = "test-secret-id-12345"
INVALID_TRUST_ID = "wrong-id-67890"


@pytest_asyncio.fixture(scope="module")
async def server_address():
    """
    启动服务器子进程，使用动态端口，并返回 (host, port) 元组。
    scope="module" 确保所有测试共享同一个服务器实例，提高效率。
    """
    env = os.environ.copy()
    env["TRUST_ID"] = VALID_TRUST_ID

    cmd = [
        sys.executable, "-m", "trust_sockets.server",
        "--host", HOST,
        "--port", "0"  # 使用端口0，让OS分配可用端口
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    address = None
    try:
        # 轮询 stdout, 等待服务器打印出监听地址
        async for line_bytes in process.stdout:
            line = line_bytes.decode('utf-8').strip()
            if line.startswith("SERVING_ON::"):
                _, host, port_str = line.split("::")
                address = (host, int(port_str))
                break  # 成功获取地址，退出循环

        if address is None:
            pytest.fail("Server process did not print address.")

    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        pytest.fail("Server process did not start up in time.")

    yield address  # 将地址提供给测试用例

    # 清理
    if process.returncode is None:
        process.terminate()
        await process.wait()


@pytest.mark.asyncio
async def test_successful_connection_and_rpc(server_address):
    """测试 TRUST_ID 一致时的正常通信和 RPC 调用"""
    host, port = server_address
    os.environ["TRUST_ID"] = VALID_TRUST_ID

    client = RPCClient(host, port)

    await client.connect()
    result = await client._async_call("greet", "Tester")
    assert result == "Hello, Tester!"
    await client.close()

    sync_client = RPCClient(host, port)
    result_sync = sync_client.sync_call("greet", "SyncTester")
    assert result_sync == "Hello, SyncTester!"

    # 清理环境变量，避免影响其他测试
    del os.environ["TRUST_ID"]


@pytest.mark.asyncio
async def test_refused_connection_mismatched_id(server_address):
    """测试 TRUST_ID 不一致时，连接被拒绝"""
    host, port = server_address
    os.environ["TRUST_ID"] = INVALID_TRUST_ID

    client = RPCClient(host, port)

    with pytest.raises(HandshakeError, match="Server rejected connection"):
        await client.connect()

    del os.environ["TRUST_ID"]


@pytest.mark.asyncio
async def test_refused_connection_no_client_id(server_address):
    """测试客户端没有 TRUST_ID 时，连接被拒绝"""
    host, port = server_address
    if "TRUST_ID" in os.environ:
        del os.environ["TRUST_ID"]

    client = RPCClient(host, port)

    with pytest.raises(HandshakeError, match="Client TRUST_ID not set"):
        await client.connect()


@pytest.mark.asyncio
async def test_rpc_method_not_found(server_address):
    """测试调用不存在的 RPC 方法"""
    host, port = server_address
    os.environ["TRUST_ID"] = VALID_TRUST_ID
    client = RPCClient(host, port)

    await client.connect()

    with pytest.raises(RuntimeError, match="NameError: Method 'no_such_method' not found"):
        await client._async_call("no_such_method")

    await client.close()
    del os.environ["TRUST_ID"]


@pytest.mark.asyncio
async def test_rpc_param_error(server_address):
    """测试 RPC 方法参数错误"""
    host, port = server_address
    os.environ["TRUST_ID"] = VALID_TRUST_ID
    client = RPCClient(host, port)

    await client.connect()

    with pytest.raises(RuntimeError, match="TypeError: Name must be a string"):
        await client._async_call("greet", 12345)

    await client.close()
    del os.environ["TRUST_ID"]