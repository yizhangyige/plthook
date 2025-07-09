@echo off
setlocal

REM Windows 平台 PLTHook 测试脚本

echo PLTHook Windows 测试开始
echo ========================

REM 检查文件是否存在
if not exist "testprog.exe" (
    echo 错误: 测试程序不存在: testprog.exe
    exit /b 1
)

if not exist "libtest.dll" (
    echo 错误: 测试库不存在: libtest.dll
    exit /b 1
)

echo 系统信息:
echo   操作系统: %OS%
echo   处理器架构: %PROCESSOR_ARCHITECTURE%
echo   .NET Framework: 
powershell -command "(Get-ItemProperty 'HKLM:SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full\' -Name Release -ErrorAction SilentlyContinue).Release" 2>nul
echo.

REM 运行测试
echo 测试 1: open 模式
testprog.exe open
if %errorlevel% neq 0 (
    echo X open 测试失败
    exit /b 1
) else (
    echo √ open 测试通过
)

echo.
echo 测试 2: open_by_handle 模式
testprog.exe open_by_handle
if %errorlevel% neq 0 (
    echo X open_by_handle 测试失败
    exit /b 1
) else (
    echo √ open_by_handle 测试通过
)

echo.
echo 测试 3: 内存监控功能
if exist "memory_monitor_win.exe" (
    echo 运行内存监控测试 (10秒)...
    start /B memory_monitor_win.exe -t -r 10
    timeout /t 12 >nul
    echo √ 内存监控测试完成
) else (
    echo - 内存监控程序不存在，跳过测试
)

echo.
echo 注意: Windows 平台不支持 open_by_address 模式
echo.
echo ========================
echo 所有测试已完成

endlocal
