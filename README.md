# 可信 Socket 通信与 RPC 系统

本项目基于 Python `asyncio` 实现了一个安全的 C/S (客户端/服务端) 通信系统，并在此基础上构建了一个轻量级的 RPC 框架。以下 README 提供更全面的说明、运行示例（文本或示意截图占位）、环境要求和操作步骤。

---

## 项目简介

* **可信通信**：通过共享的环境变量 `TRUST_ID` 进行质询-响应握手，保证双方通信安全。
* **异步 I/O**：使用 Python 标准库 `asyncio` 构建，支持高并发处理。
* **轻量级 RPC**：允许客户端像调用本地函数一样调用服务端提供的函数，支持同步与异步调用。
* **无第三方运行时依赖**：核心功能仅依赖 Python 标准库，易于部署。
* **模块化设计**：将握手、消息分包、RPC 分发、服务实现等逻辑分文件组织，便于扩展与维护。
* **完备测试**：使用 `pytest` 和 `pytest-asyncio` 进行单元与集成测试，覆盖正常与异常场景。
- **环境管理**：通过 `.env` 自动加载 `TRUST_ID`，在未设置环境变量时生效；测试时可通过 subprocess env 传入。

## 特性

1. **握手认证**：客户端连接后，服务端发起随机质询，客户端基于 `TRUST_ID` 计算响应并回传，服务端校验通过后建立可信连接。
2. **消息分包**：自定义消息帧，4 字节长度前缀 + 消息体，确保完整读写。
3. **RPC 调用**：支持同步和异步调用模式。请求格式为 JSON，包含唯一请求 ID、方法名、参数；响应包含对应 ID、结果或错误信息。
4. **同步客户端接口**：封装异步逻辑，通过 `asyncio.run` 提供阻塞式调用，方便常规脚本中使用。
5. **异步客户端接口**：在已有 `asyncio` 环境中，可发起并发 RPC 调用。
6. **服务端可扩展服务**：在 `services.py` 中注册函数，即可通过 RPC 暴露给客户端。
7. **日志与调试**：在关键阶段打印日志（握手、调用、异常），便于调试与监控。
8. **测试覆盖**：包括成功连接、握手失败、RPC 方法不存在、参数错误、客户端缺少 `TRUST_ID` 等场景。

## 环境要求

* **操作系统**：Windows、Linux、macOS 均可（需 Python 环境）。
* **Python 版本**：Python >= 3.8，推荐 3.9 或更高。
* **运行依赖**：

  * 无额外运行时依赖，仅使用 Python 标准库（`asyncio`, `struct`, `hashlib`, `json`, `os`, `secrets`, `uuid` 等）。
* **开发/测试依赖**（可选，仅在开发环境使用）：

  * `pytest` (>=6.0)
  * `pytest-asyncio`

可创建或激活虚拟环境：

```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install --upgrade pip
pip install pytest pytest-asyncio
```

## 目录结构

```text
trust-rpc-project/
├── .gitignore
├── .env
├── README.md                   # 本文档
├── trust_sockets/
│   ├── __init__.py
│   ├── protocol.py            # 握手协议、消息分包逻辑
│   ├── server.py              # 服务端入口与连接处理
│   ├── client.py              # 客户端示例：RPC 演示或简单聊天
│   ├── rpc.py                 # RPC 调度与客户端封装
│   └── services.py            # 服务端提供的远程函数注册
└── tests/
    ├── __init__.py
    └── test_communication.py  # 核心通信与 RPC 测试用例
```

## 配置环境变量

在运行前，需要在.env文件中设置环境变量 `TRUST_ID`。客户端和服务端必须使用相同的值：

* **Linux/macOS**:

  ```bash
  export TRUST_ID="my-super-secret-key"
  ```
* **Windows PowerShell**:

  ```powershell
  $Env:TRUST_ID = "my-super-secret-key"
  ```
* **Windows cmd:**

  ```cmd
  set TRUST_ID=my-super-secret-key
  ```

请确保在同一终端或会话中启动服务端/客户端时均已设置该变量。

## Windows运行指南

以下示例假设 `trust-rpc-project` 是当前工作目录。

### 1. 启动服务端

```bash
# 进入项目根目录
cd trust-rpc-project

# 启动服务器
python -m trust_sockets.server
```

* 默认监听 `127.0.0.1:8888`。
* 启动后，输出示例：

  ```text
  Serving on ('127.0.0.1', 8888)...
  ```

> **注意**：如需修改监听地址或端口，可在 `server.py` 中调整 `host` 和 `port` 变量，或扩展命令行参数支持。

### 2. 运行客户端示例

在另一个终端，确保设置相同 `TRUST_ID`：

```bash
cd trust-rpc-project

python -m trust_sockets.client
```

客户端默认运行 RPC 演示 (`rpc_demo_main`)：

* **异步 RPC 调用演示**：并发调用 `greet` 与 `long_running_task`，显示返回结果。
* **同步 RPC 调用演示**：阻塞方式调用 `greet`，并测试参数错误场景。

输出示例（文本示意）：

```
PS D:\trust-rpc-project> python -m trust_sockets.client
[DEBUG][client] TRUST_ID = my-super-secret-key
[DEBUG][client pid=49440] perform_client_handshake: TRUST_ID='my-super-secret-key'
Client: Received challenge.
Client: Sent response.
Client: Handshake successful.
Async 'greet' result: Hello, Alice!
Async 'long_running_task' result: Task completed after 2 seconds.
Async error test successful: NameError: Method 'non_existent_function' not found.

--- Testing Sync RPC Call ---
[DEBUG][client pid=49440] perform_client_handshake: TRUST_ID='my-super-secret-key'
Client: Received challenge.
Client: Sent response.
Client: Handshake successful.
Sync 'greet' result: Hello, Bob!
[DEBUG][client pid=49440] perform_client_handshake: TRUST_ID='my-super-secret-key'
Client: Received challenge.
Client: Sent response.
Client: Handshake successful.
Sync error test successful: TypeError: Name must be a string
--- Sync Test Finished ---
```

> **截图示例占位**
>
> ```markdown
> ![异步 RPC 调用示例](assets/async_rpc_demo.png)
> ![同步 RPC 调用示例](assets/sync_rpc_demo.png)
> ```

### 3. 运行简单聊天示例（可选）

若想测试未经 RPC 封装的基础握手与消息收发，可在 `client.py` 中调用 `simple_chat_main()`：

```bash
# 修改 client.py 的 __main__ 或新建脚本：
# asyncio.run(simple_chat_main())
python -m trust_sockets.client
```

* 客户端在握手成功后，可输入消息并接收服务端回显（需在服务端对应逻辑中实现回显）。

### 4. 运行测试用例

项目使用 `pytest` 与 `pytest-asyncio` 编写测试。确保开发/测试环境已安装依赖。

```bash
cd trust-rpc-project

pytest -v
```

测试内容包括：

* 正常连接与 RPC 调用成功。
* 不同或缺失 `TRUST_ID` 导致握手失败。
* RPC 方法不存在或参数类型错误导致 RPC 调用失败。

输出示例（文本示意）：

```
PS D:\trust-rpc-project> pytest -v
=============================================================================== test session starts ===============================================================================
platform win32 -- Python 3.12.8, pytest-8.4.1, pluggy-1.6.0 -- C:\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: D:\trust-rpc-project
rootdir: D:\trust-rpc-project
plugins: anyio-4.9.0, asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 5 items                                                                                                                                                                   

tests/test_communication.py::test_successful_connection_and_rpc PASSED                                                                                                       [ 20%] 
tests/test_communication.py::test_refused_connection_mismatched_id PASSED                                                                                                    [ 40%] 
tests/test_communication.py::test_refused_connection_no_client_id PASSED                                                                                                     [ 60%] 
tests/test_communication.py::test_rpc_method_not_found PASSED                                                                                                                [ 80%] 
tests/test_communication.py::test_rpc_param_error PASSED                                                                                                                     [100%] 

================================================================================ 5 passed in 0.17s ================================================================================ 
```

> **截图示例占位**：可将 pytest 输出结果截图并关联：
>
> ```markdown
> ![测试通过示例](
> /pytest_success.png)
> ```

## 日志与调试

* 在关键函数（握手、RPC 调用分发等）均有打印，可根据需要调整或替换为更完善的日志框架（如 `logging` 模块）。
* 若遇到连接问题，可在客户端或服务端捕获异常并打印堆栈，或添加更多日志。

## 扩展与定制

* **修改端口/地址**：在 `server.py` 与客户端配置中调整或添加命令行参数解析。
* **新增服务**：在 `trust_sockets/services.py` 中注册新函数即可，支持同步或异步函数。
* **更复杂的认证**：可替换为公钥加密、TLS 等更安全的方案。
* **序列化替换**：若需要传输更复杂对象，可在 RPC 中使用 `pickle`、`msgpack` 等，但需注意安全性。
* **日志系统**：集成 `logging`、日志文件、不同级别日志等。
* **监控与运维**：集成 Prometheus、健康检查接口等。


## 常见问题

* **握手失败**：确认客户端/服务端 `TRUST_ID` 完全一致；注意环境变量作用域。
* **端口被占用**：若 `8888` 被占用，可修改监听端口或查看占用进程并释放。
* **测试失败**：确保测试环境中的 `TRUST_ID` 设置正确；如测试使用硬编码端口，可与实际运行端口保持一致。
* **兼容性**：在较旧 Python 版本 (<3.8) 可能缺少某些 `asyncio` 功能，建议使用 Python 3.9+。

## 联系与反馈

如有问题或建议，可在项目仓库中提交 Issue，或联系开发者。

---

