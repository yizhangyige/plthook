# Android PLTHook 构建脚本
param(
    [Parameter()]
    [string]$AndroidNdkPath = "C:\Users\dong\tools\android-ndk\android-ndk-r27",
    
    [Parameter()]
    [ValidateSet("arm64-v8a", "armeabi-v7a", "x86_64", "x86", "all")]
    [string]$Architecture = "all",
    
    [Parameter()]
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

Write-Host "Android PLTHook Build Script" -ForegroundColor Green
Write-Host "============================" -ForegroundColor Green

$rootDir = $PSScriptRoot
$androidDir = Join-Path $rootDir "test\android"
$outputDir = Join-Path $rootDir "output\android"

# 检查 NDK 路径
if (-not (Test-Path $AndroidNdkPath)) {
    Write-Host "错误: Android NDK 路径不存在: $AndroidNdkPath" -ForegroundColor Red
    exit 1
}

$ndkBuildExe = Join-Path $AndroidNdkPath "ndk-build.cmd"
if (-not (Test-Path $ndkBuildExe)) {
    $ndkBuildExe = Join-Path $AndroidNdkPath "ndk-build.exe"
}
if (-not (Test-Path $ndkBuildExe)) {
    Write-Host "错误: 未找到 ndk-build 工具: $ndkBuildExe" -ForegroundColor Red
    exit 1
}

Write-Host "使用 Android NDK: $AndroidNdkPath" -ForegroundColor Yellow
Write-Host "NDK Build 工具: $ndkBuildExe" -ForegroundColor Yellow

# 创建输出目录
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

# 清理构建
if ($Clean) {
    Write-Host "清理 Android 构建..." -ForegroundColor Yellow
    $cleanCmd = "$ndkBuildExe -C `"$androidDir`" clean"
    Write-Host "执行: $cleanCmd" -ForegroundColor Gray
    Invoke-Expression $cleanCmd
}

# 设置架构
$abiList = @()
if ($Architecture -eq "all") {
    $abiList = @("arm64-v8a", "armeabi-v7a", "x86_64")
} else {
    $abiList = @($Architecture)
}

Write-Host "构建目标架构: $($abiList -join ', ')" -ForegroundColor Yellow

# 构建每个架构
foreach ($abi in $abiList) {
    Write-Host ""
    Write-Host "构建 $abi 架构..." -ForegroundColor Cyan
    
    # 修改 Application.mk 以指定单一架构
    $appMkPath = Join-Path $androidDir "jni\Application.mk"
    $appMkContent = @"
APP_PLATFORM := android-21
APP_ABI := $abi
APP_STL := c++_shared
APP_CPPFLAGS := -frtti -fexceptions -std=c++11 -D__ANDROID_API__=21
APP_OPTIM := release
"@
    Set-Content -Path $appMkPath -Value $appMkContent -Encoding UTF8
    
    # 执行构建
    $buildCmd = "$ndkBuildExe -C `"$androidDir`" -j4"
    Write-Host "执行: $buildCmd" -ForegroundColor Gray
    
    try {
        Invoke-Expression $buildCmd
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ $abi 架构构建成功" -ForegroundColor Green
            
            # 复制构建结果到输出目录
            $abiOutputDir = Join-Path $outputDir $abi
            if (-not (Test-Path $abiOutputDir)) {
                New-Item -ItemType Directory -Path $abiOutputDir -Force | Out-Null
            }
            
            $libsPath = Join-Path $androidDir "libs\$abi"
            if (Test-Path $libsPath) {
                Copy-Item "$libsPath\*" $abiOutputDir -Force
                Write-Host "复制文件到: $abiOutputDir" -ForegroundColor Green
            }
        } else {
            Write-Host "✗ $abi 架构构建失败" -ForegroundColor Red
        }
    } catch {
        Write-Host "✗ $abi 架构构建异常: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 恢复原始 Application.mk
$appMkPath = Join-Path $androidDir "jni\Application.mk"
$originalAppMkContent = @"
APP_PLATFORM := android-21
APP_ABI := arm64-v8a
APP_STL := c++_shared
APP_CPPFLAGS := -frtti -fexceptions -std=c++11 -D__ANDROID_API__=21
APP_OPTIM := release
"@
Set-Content -Path $appMkPath -Value $originalAppMkContent -Encoding UTF8

Write-Host ""
Write-Host "Android 构建完成!" -ForegroundColor Green
Write-Host "输出目录: $outputDir" -ForegroundColor Green

# 显示构建结果
Write-Host ""
Write-Host "构建结果:" -ForegroundColor Yellow
Get-ChildItem $outputDir -Recurse | ForEach-Object {
    if ($_.PSIsContainer) {
        Write-Host "  📁 $($_.Name)/" -ForegroundColor Cyan
    } else {
        $size = [math]::Round($_.Length / 1KB, 2)
        Write-Host "    📄 $($_.Name) ($size KB)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "使用说明:" -ForegroundColor Yellow
Write-Host "1. 将对应架构的文件推送到 Android 设备:" -ForegroundColor Gray
Write-Host "   adb push output/android/arm64-v8a/* /data/local/tmp/" -ForegroundColor Gray
Write-Host "2. 在设备上运行测试:" -ForegroundColor Gray
Write-Host "   adb shell 'cd /data/local/tmp && ./run_tests.sh'" -ForegroundColor Gray
