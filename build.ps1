# PLTHook 构建脚本 - Windows 平台
# 支持构建 Windows 和 Android 平台的共享库和测试程序

param(
    [Parameter()]
    [ValidateSet("windows", "android", "all")]
    [string]$Platform = "windows",
    
    [Parameter()]
    [ValidateSet("x86", "x64", "arm64")]
    [string]$Architecture = "x64",
    
    [Parameter()]
    [string]$AndroidNdkPath = "",
    
    [Parameter()]
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

# 工作目录
$rootDir = $PSScriptRoot
$buildDir = Join-Path $rootDir "build"
$outputDir = Join-Path $rootDir "output"

Write-Host "PLTHook 构建脚本" -ForegroundColor Green
Write-Host "================" -ForegroundColor Green

# 清理函数
function Clean-BuildDirectories {
    Write-Host "清理构建目录..." -ForegroundColor Yellow
    if (Test-Path $buildDir) {
        Remove-Item $buildDir -Recurse -Force
    }
    if (Test-Path $outputDir) {
        Remove-Item $outputDir -Recurse -Force
    }
    
    # 清理 test 目录中的构建产物
    $testDir = Join-Path $rootDir "test"
    $toClean = @("*.dll", "*.exe", "*.lib", "*.exp", "*.obj", "*.so")
    foreach ($pattern in $toClean) {
        Get-ChildItem -Path $testDir -Filter $pattern -ErrorAction SilentlyContinue | Remove-Item -Force
    }
    
    Write-Host "清理完成" -ForegroundColor Green
}

# Windows 构建函数
function Build-Windows {
    param([string]$Arch)
    
    Write-Host "开始构建 Windows $Arch 平台..." -ForegroundColor Yellow
    
    # 创建输出目录
    $winOutputDir = Join-Path $outputDir "windows\$Arch"
    New-Item -ItemType Directory -Path $winOutputDir -Force | Out-Null
    
    # 检查 Visual Studio 环境
    $vsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vsWhere) {
        $vsPath = & $vsWhere -latest -property installationPath
        if ($vsPath) {
            $vcVarsPath = Join-Path $vsPath "VC\Auxiliary\Build\vcvarsall.bat"
            if (Test-Path $vcVarsPath) {
                Write-Host "找到 Visual Studio: $vsPath" -ForegroundColor Green
                
                # 设置架构参数
                $vcArch = switch ($Arch) {
                    "x86" { "x86" }
                    "x64" { "x64" }
                    "arm64" { "arm64" }
                }
                
                # 构建共享库和测试程序
                $testDir = Join-Path $rootDir "test"
                Push-Location $testDir
                
                try {
                    # 使用 vcvarsall.bat 设置环境变量并构建
                    $buildCmd = "`"$vcVarsPath`" $vcArch && nmake /f Makefile.win32 all"
                    Write-Host "执行构建命令: $buildCmd" -ForegroundColor Cyan
                    
                    cmd /c $buildCmd
                    if ($LASTEXITCODE -ne 0) {
                        throw "Windows 构建失败"
                    }
                    
                    # 复制构建产物
                    Copy-Item "libtest.dll" $winOutputDir -Force
                    Copy-Item "testprog.exe" $winOutputDir -Force
                    if (Test-Path "libtest.lib") {
                        Copy-Item "libtest.lib" $winOutputDir -Force
                    }
                    
                    Write-Host "Windows $Arch 构建完成" -ForegroundColor Green
                    Write-Host "输出目录: $winOutputDir" -ForegroundColor Green
                    
                } finally {
                    Pop-Location
                }
            }
        }
    } else {
        Write-Error "未找到 Visual Studio，请确保已安装 Visual Studio 2019 或更高版本"
    }
}

# Android 构建函数
function Build-Android {
    param([string]$NdkPath)
    
    Write-Host "开始构建 Android 平台..." -ForegroundColor Yellow
    
    if (-not $NdkPath -or -not (Test-Path $NdkPath)) {
        Write-Error "请提供有效的 Android NDK 路径"
        return
    }
    
    # 创建输出目录
    $androidOutputDir = Join-Path $outputDir "android"
    New-Item -ItemType Directory -Path $androidOutputDir -Force | Out-Null
    
    # 设置 NDK 环境变量
    $env:ANDROID_NDK_ROOT = $NdkPath
    $ndkBuild = Join-Path $NdkPath "ndk-build.cmd"
    
    if (-not (Test-Path $ndkBuild)) {
        $ndkBuild = Join-Path $NdkPath "ndk-build"  # Linux/Mac 版本
    }
    
    if (-not (Test-Path $ndkBuild)) {
        Write-Error "未找到 ndk-build，请检查 NDK 路径"
        return
    }
    
    $androidProjectDir = Join-Path $rootDir "test\android"
    Push-Location $androidProjectDir
    
    try {
        Write-Host "执行 ndk-build..." -ForegroundColor Cyan
        & $ndkBuild clean
        & $ndkBuild
        
        if ($LASTEXITCODE -ne 0) {
            throw "Android 构建失败"
        }
        
        # 复制构建产物
        $libsDir = Join-Path $androidProjectDir "libs"
        if (Test-Path $libsDir) {
            Copy-Item $libsDir $androidOutputDir -Recurse -Force
        }
        
        $objDir = Join-Path $androidProjectDir "obj"
        if (Test-Path $objDir) {
            Copy-Item $objDir $androidOutputDir -Recurse -Force
        }
        
        Write-Host "Android 构建完成" -ForegroundColor Green
        Write-Host "输出目录: $androidOutputDir" -ForegroundColor Green
        
    } finally {
        Pop-Location
    }
}

# 运行测试函数
function Run-WindowsTests {
    param([string]$Arch)
    
    $winOutputDir = Join-Path $outputDir "windows\$Arch"
    if (-not (Test-Path $winOutputDir)) {
        Write-Warning "Windows $Arch 构建产物不存在，跳过测试"
        return
    }
    
    Write-Host "运行 Windows $Arch 测试..." -ForegroundColor Yellow
    
    Push-Location $winOutputDir
    try {
        Write-Host "测试 open 模式..." -ForegroundColor Cyan
        .\testprog.exe open
        
        Write-Host "测试 open_by_handle 模式..." -ForegroundColor Cyan
        .\testprog.exe open_by_handle
        
        Write-Host "Windows $Arch 测试通过" -ForegroundColor Green
        
    } catch {
        Write-Error "Windows $Arch 测试失败: $_"
    } finally {
        Pop-Location
    }
}

# 主构建逻辑
try {
    if ($Clean) {
        Clean-BuildDirectories
        return
    }
    
    # 创建构建和输出目录
    New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    
    switch ($Platform) {
        "windows" {
            Build-Windows -Arch $Architecture
            Run-WindowsTests -Arch $Architecture
        }
        "android" {
            if (-not $AndroidNdkPath) {
                $AndroidNdkPath = Read-Host "请输入 Android NDK 路径"
            }
            Build-Android -NdkPath $AndroidNdkPath
        }
        "all" {
            Build-Windows -Arch $Architecture
            Run-WindowsTests -Arch $Architecture
            
            if (-not $AndroidNdkPath) {
                $AndroidNdkPath = Read-Host "请输入 Android NDK 路径"
            }
            Build-Android -NdkPath $AndroidNdkPath
        }
    }
    
    Write-Host "`n构建完成!" -ForegroundColor Green
    Write-Host "输出目录: $outputDir" -ForegroundColor Green
    
} catch {
    Write-Error "构建失败: $_"
    exit 1
}
