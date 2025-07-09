@echo off
setlocal

REM Windows Memory Monitor Build Script for PLTHook

echo Memory Monitor Build Script for Windows
echo ========================================

@echo off
setlocal

REM Windows Memory Monitor Build Script for PLTHook

echo Memory Monitor Build Script for Windows
echo ========================================

REM First check if compiler is already in PATH
where cl >nul 2>&1
if %errorlevel% neq 0 (
    echo Visual Studio compiler not found in PATH, searching for installation...
    
    REM 查找 Visual Studio 安装路径
    set VSWHERE_PATH="%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
    if not exist %VSWHERE_PATH% set VSWHERE_PATH="%ProgramFiles%\Microsoft Visual Studio\Installer\vswhere.exe"

    if exist %VSWHERE_PATH% (
        for /f "usebackq tokens=*" %%i in (`%VSWHERE_PATH% -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do (
            set VSINSTALLDIR=%%i
        )
    )

    if defined VSINSTALLDIR (
        echo Found Visual Studio: %VSINSTALLDIR%
        call "%VSINSTALLDIR%\VC\Auxiliary\Build\vcvarsall.bat" x64
    ) else (
        echo Error: Visual Studio not found
        echo Please install Visual Studio with C++ tools or run from Developer Command Prompt
        exit /b 1
    )
)

REM Verify compiler is now available
where cl >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Visual Studio compiler still not found after setup
    exit /b 1
)

REM Build memory monitor
echo Building memory monitor...
cl /nologo /O2 /I.. memory_monitor.c ..\plthook_win32.c /Fememory_monitor.exe dbghelp.lib psapi.lib kernel32.lib

if %errorlevel% neq 0 (
    echo Build failed!
    exit /b 1
)

echo Build successful!

REM Copy to output directory if it exists
if exist "..\output\windows\x64" (
    copy memory_monitor.exe ..\output\windows\x64\
    echo Copied to output directory
)

echo.
echo Usage Examples:
echo   memory_monitor.exe -h                    Show help
echo   memory_monitor.exe -t -r 30              Run test for 30 seconds
echo   memory_monitor.exe -i 10 -d              Monitor every 10 seconds with detailed logs
echo   memory_monitor.exe                       Continuous monitoring every 5 seconds

endlocal
