@echo off
REM ========== 配置 ==========
set ROOT_DIR=trust-rpc-project

REM ========== 创建根目录 ==========
if not exist "%ROOT_DIR%" (
    mkdir "%ROOT_DIR%"
) else (
    echo 目录 "%ROOT_DIR%" 已存在
)
cd "%ROOT_DIR%"

REM ========== 创建根文件 ==========
REM .gitignore（空文件）
if not exist ".gitignore" (
    type nul > ".gitignore"
) else (
    echo 文件 .gitignore 已存在
)

REM README.md，添加项目标题作为初始内容
if not exist "README.md" (
    (echo # %ROOT_DIR%) > "README.md"
) else (
    echo 文件 README.md 已存在
)

REM ========== 创建 trust_sockets 目录及文件 ==========
if not exist "trust_sockets" (
    mkdir "trust_sockets"
) else (
    echo 目录 trust_sockets 已存在
)

REM 在 trust_sockets 下创建文件
for %%F in (__init__.py client.py server.py protocol.py rpc.py services.py) do (
    if not exist "trust_sockets\%%F" (
        type nul > "trust_sockets\%%F"
    ) else (
        echo 文件 trust_sockets\%%F 已存在
    )
)

REM ========== 创建 tests 目录及文件 ==========
if not exist "tests" (
    mkdir "tests"
) else (
    echo 目录 tests 已存在
)

for %%F in (__init__.py test_communication.py) do (
    if not exist "tests\%%F" (
        type nul > "tests\%%F"
    ) else (
        echo 文件 tests\%%F 已存在
    )
)

echo 目录结构创建完成！
pause
