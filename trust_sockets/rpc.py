# trust_sockets/rpc.py
import json
import uuid
import asyncio
from .protocol import ENCODING, read_msg, send_msg
from .services import RPC_FUNCTIONS
import threading

# --- RPC Server-side Dispatcher ---

async def dispatch_rpc_call(request_data: bytes) -> bytes:
    """解析 RPC 请求，调用函数，并返回序列化的结果"""
    error = None
    result = None
    request_id = None

    try:
        payload = json.loads(request_data.decode(ENCODING))
        request_id = payload.get("id")
        method_name = payload["method"]
        params = payload.get("params", {})
        args = params.get("args", [])
        kwargs = params.get("kwargs", {})

        if method_name not in RPC_FUNCTIONS:
            raise NameError(f"Method '{method_name}' not found.")

        func = RPC_FUNCTIONS[method_name]

        # 支持同步和异步函数
        if asyncio.iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)

    except Exception as e:
        error = f"{type(e).__name__}: {e}"

    response = {"id": request_id, "result": result, "error": error}
    return json.dumps(response).encode(ENCODING)


# --- RPC Client-side ---

class RPCClient:
    """RPC 客户端，封装了连接、握手和远程调用逻辑"""
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self._is_connected = False
        self.pending_futures: dict[str, asyncio.Future] = {}
        self._listen_task: asyncio.Task | None = None  # 用于保存监听响应的任务引用

    async def connect(self):
        """建立连接并执行握手。如果已连接则直接返回；连接成功后，启动后台监听任务。"""
        if self._is_connected:
            return

        from .protocol import perform_client_handshake  # 避免循环导入
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        await perform_client_handshake(self.reader, self.writer)
        self._is_connected = True

        # 创建并保存监听任务
        self._listen_task = asyncio.create_task(self._listen_for_responses())

    async def close(self):
        """关闭连接：先关闭 writer，再取消监听任务，清理 pending futures。"""
        if self._is_connected and self.writer:
            # 关闭底层连接
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
            self._is_connected = False

            # 取消后台监听任务
            if self._listen_task:
                self._listen_task.cancel()
                try:
                    await self._listen_task
                except asyncio.CancelledError:
                    pass
                self._listen_task = None

            # 取消并清理所有尚未完成的 futures
            for fut in self.pending_futures.values():
                if not fut.done():
                    fut.cancel()
            self.pending_futures.clear()

    async def _listen_for_responses(self):
        """
        后台任务：持续读取服务端响应并完成对应 future。
        退出时要对 CancelledError 友好处理，或在异常时通知所有 pending futures。
        """
        try:
            while self._is_connected:
                data = await read_msg(self.reader)
                if data is None:
                    break  # 对端关闭连接
                try:
                    response = json.loads(data.decode(ENCODING))
                except Exception as e:
                    # 无法解析则通知所有 pending futures 错误，随后退出
                    for fut in self.pending_futures.values():
                        if not fut.done():
                            fut.set_exception(e)
                    self.pending_futures.clear()
                    break

                request_id = response.get("id")
                if request_id in self.pending_futures:
                    future = self.pending_futures.pop(request_id)
                    if response.get("error"):
                        future.set_exception(RuntimeError(response["error"]))
                    else:
                        future.set_result(response.get("result"))
                # 若收到非预期响应 ID，可忽略或记录日志
        except asyncio.CancelledError:
            # 被取消时，直接退出
            pass
        except Exception as e:
            # 其它异常发生时，通知所有 pending futures，然后退出
            for fut in self.pending_futures.values():
                if not fut.done():
                    fut.set_exception(e)
            self.pending_futures.clear()

    async def _async_call(self, method: str, *args, **kwargs):
        """异步 RPC 调用"""
        if not self._is_connected:
            await self.connect()

        request_id = str(uuid.uuid4())
        request = {
            "type": "rpc",
            "id": request_id,
            "method": method,
            "params": {"args": args, "kwargs": kwargs}
        }

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.pending_futures[request_id] = future

        await send_msg(self.writer, json.dumps(request).encode(ENCODING))
        return await future

    async def _sync_wrapper(self, method: str, *args, **kwargs):
        """
        用于同步调用的异步包装器：connect、调用、close
        """
        await self.connect()
        try:
            result = await self._async_call(method, *args, **kwargs)
        finally:
            # 确保无论是否抛异常，都关闭连接
            await self.close()
        return result

    def sync_call(self, method: str, *args, **kwargs):
        """
        同步 RPC 调用：
        - 如果当前没有运行中的事件循环，直接用 asyncio.run；
        - 如果已有运行的事件循环，在线程中新建事件循环执行异步包装器，避免重复调用 asyncio.run。
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is None or not loop.is_running():
            # 没有正在运行的事件循环，直接用 asyncio.run
            return asyncio.run(self._sync_wrapper(method, *args, **kwargs))
        else:
            # 当前已有事件循环在运行，使用线程来执行新的事件循环
            result_container: dict[str, object] = {}
            def target():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    res = new_loop.run_until_complete(self._sync_wrapper(method, *args, **kwargs))
                    result_container['result'] = res
                except Exception as e:
                    result_container['exception'] = e
                finally:
                    # 关闭事件循环
                    new_loop.close()

            t = threading.Thread(target=target)
            t.start()
            t.join()
            if 'exception' in result_container:
                raise result_container['exception']
            return result_container.get('result')
