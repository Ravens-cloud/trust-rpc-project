# trust_sockets/services.py
"""
服务端可供远程调用的函数
"""
import asyncio

def greet(name: str) -> str:
    """一个简单的同步问候函数"""
    if not isinstance(name, str):
        raise TypeError("Name must be a string")
    return f"Hello, {name}!"

async def long_running_task(seconds: int) -> str:
    """一个模拟耗时的异步函数"""
    print(f"Service: Starting long task for {seconds} seconds...")
    await asyncio.sleep(seconds)
    result = f"Task completed after {seconds} seconds."
    print(f"Service: {result}")
    return result

# 注册可用的 RPC 函数
RPC_FUNCTIONS = {
    "greet": greet,
    "long_running_task": long_running_task,
}