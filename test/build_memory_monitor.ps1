# Windows Memory Monitor Build Script for PLTHook
param(
    [Parameter()]
    [ValidateSet("x86", "x64", "arm64")]
    [string]$Architecture = "x64",
    
    [Parameter()]
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

Write-Host "Memory Monitor Build Script for Windows" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green

# 查找 Visual Studio 安装
$vsInstallPath = $null
$vswherePath = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswherePath)) {
    $vswherePath = "${env:ProgramFiles}\Microsoft Visual Studio\Installer\vswhere.exe"
}

if (Test-Path $vswherePath) {
    $vsInstallPath = & $vswherePath -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if ($vsInstallPath) {
        Write-Host "Found Visual Studio: $vsInstallPath" -ForegroundColor Yellow
        $vcvarsPath = Join-Path $vsInstallPath "VC\Auxiliary\Build\vcvarsall.bat"
        
        if (Test-Path $vcvarsPath) {
            Write-Host "Setting up Visual Studio environment..." -ForegroundColor Yellow
            
            # 构建编译命令
            $buildCmd = "`"$vcvarsPath`" $Architecture && cl /nologo /O2 /I.. memory_monitor_win.c ..\plthook_win32.c /Fememory_monitor_win.exe dbghelp.lib psapi.lib kernel32.lib"
            
            # 执行构建
            Write-Host "Building memory monitor..." -ForegroundColor Yellow
            $result = cmd /c $buildCmd
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "Build successful!" -ForegroundColor Green
                
                # 复制到输出目录
                $outputDir = "..\output\windows\$Architecture"
                if (Test-Path $outputDir) {
                    Copy-Item "memory_monitor_win.exe" $outputDir -Force
                    Write-Host "Copied to output directory: $outputDir" -ForegroundColor Green
                }
                
                # 显示使用示例
                Write-Host ""
                Write-Host "Usage Examples:" -ForegroundColor Cyan
                Write-Host "  .\memory_monitor_win.exe -h                    Show help" -ForegroundColor Gray
                Write-Host "  .\memory_monitor_win.exe -t -r 30              Run test for 30 seconds" -ForegroundColor Gray
                Write-Host "  .\memory_monitor_win.exe -i 10 -d              Monitor every 10 seconds with detailed logs" -ForegroundColor Gray
                Write-Host "  .\memory_monitor_win.exe                       Continuous monitoring every 5 seconds" -ForegroundColor Gray
                
            } else {
                Write-Host "Build failed!" -ForegroundColor Red
                Write-Host $result
                exit 1
            }
        } else {
            Write-Host "Error: vcvarsall.bat not found in Visual Studio installation" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Error: No Visual Studio installation found with C++ tools" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Error: vswhere.exe not found. Please install Visual Studio with C++ tools" -ForegroundColor Red
    exit 1
}
