# Android 设备测试部署脚本
param(
    [Parameter()]
    [ValidateSet("arm64-v8a", "armeabi-v7a", "x86_64", "auto")]
    [string]$Architecture = "auto",
    
    [Parameter()]
    [switch]$Deploy,
    
    [Parameter()]
    [switch]$Test,
    
    [Parameter()]
    [switch]$All
)

$ErrorActionPreference = "Stop"

Write-Host "Android 设备测试部署脚本" -ForegroundColor Green
Write-Host "========================" -ForegroundColor Green

$rootDir = $PSScriptRoot
$outputDir = Join-Path $rootDir "output\android"
$androidTestDir = Join-Path $rootDir "test\android"

# 检查 ADB
$adbPath = "adb"
try {
    $null = & $adbPath version
} catch {
    Write-Host "错误: ADB 未找到或不在 PATH 中" -ForegroundColor Red
    Write-Host "请确保 Android SDK 已安装并且 ADB 在 PATH 中" -ForegroundColor Red
    exit 1
}

# 检查设备连接
Write-Host "检查 Android 设备连接..." -ForegroundColor Yellow
$devices = & $adbPath devices
if ($devices -match "device$") {
    Write-Host "✓ 检测到 Android 设备" -ForegroundColor Green
} else {
    Write-Host "错误: 未检测到 Android 设备" -ForegroundColor Red
    Write-Host "请确保设备已连接并启用 USB 调试" -ForegroundColor Red
    exit 1
}

# 自动检测设备架构
if ($Architecture -eq "auto") {
    Write-Host "自动检测设备架构..." -ForegroundColor Yellow
    $deviceAbi = & $adbPath shell getprop ro.product.cpu.abi
    $deviceAbi = $deviceAbi.Trim()
    
    if ($deviceAbi -match "arm64-v8a") {
        $Architecture = "arm64-v8a"
    } elseif ($deviceAbi -match "armeabi-v7a") {
        $Architecture = "armeabi-v7a"
    } elseif ($deviceAbi -match "x86_64") {
        $Architecture = "x86_64"
    } else {
        Write-Host "警告: 未识别的设备架构: $deviceAbi，使用 arm64-v8a" -ForegroundColor Yellow
        $Architecture = "arm64-v8a"
    }
}

Write-Host "使用架构: $Architecture" -ForegroundColor Yellow

$sourceDir = Join-Path $outputDir $Architecture
if (-not (Test-Path $sourceDir)) {
    Write-Host "错误: 构建输出目录不存在: $sourceDir" -ForegroundColor Red
    Write-Host "请先运行 .\build_android.ps1 构建 Android 版本" -ForegroundColor Red
    exit 1
}

# 设备信息
Write-Host ""
Write-Host "设备信息:" -ForegroundColor Cyan
$deviceModel = & $adbPath shell getprop ro.product.model
$androidVersion = & $adbPath shell getprop ro.build.version.release
$apiLevel = & $adbPath shell getprop ro.build.version.sdk
Write-Host "  设备型号: $($deviceModel.Trim())" -ForegroundColor Gray
Write-Host "  Android 版本: $($androidVersion.Trim())" -ForegroundColor Gray
Write-Host "  API 级别: $($apiLevel.Trim())" -ForegroundColor Gray
Write-Host "  架构: $($deviceAbi.Trim())" -ForegroundColor Gray

if ($All -or $Deploy) {
    Write-Host ""
    Write-Host "部署文件到设备..." -ForegroundColor Cyan
    
    # 创建目录
    & $adbPath shell mkdir -p /data/local/tmp/plthook
    
    # 推送构建文件
    Write-Host "推送构建文件..." -ForegroundColor Yellow
    $sourceFiles = Get-ChildItem "$sourceDir\*" -File
    foreach ($file in $sourceFiles) {
        Write-Host "  推送: $($file.Name)" -ForegroundColor Gray
        & $adbPath push $file.FullName /data/local/tmp/plthook/
    }
    
    # 推送测试脚本
    Write-Host "推送测试脚本..." -ForegroundColor Yellow
    & $adbPath push "$androidTestDir\run_tests.sh" /data/local/tmp/plthook/
    
    # 设置执行权限
    Write-Host "设置执行权限..." -ForegroundColor Yellow
    & $adbPath shell chmod +x /data/local/tmp/plthook/testprog
    & $adbPath shell chmod +x /data/local/tmp/plthook/memory_monitor
    & $adbPath shell chmod +x /data/local/tmp/plthook/android_simple_test
    & $adbPath shell chmod +x /data/local/tmp/plthook/multithread_memory_test
    & $adbPath shell chmod +x /data/local/tmp/plthook/multithread_memory_test_cpp
    & $adbPath shell chmod +x /data/local/tmp/plthook/memory_stress_test
    & $adbPath shell chmod +x /data/local/tmp/plthook/advanced_memory_test
    & $adbPath shell chmod +x /data/local/tmp/plthook/run_tests.sh
    
    # 验证文件部署
    Write-Host "验证文件部署..." -ForegroundColor Yellow
    & $adbPath shell ls -la /data/local/tmp/plthook/
    
    Write-Host "✓ 文件部署完成" -ForegroundColor Green
}

if ($All -or $Test) {
    Write-Host ""
    Write-Host "运行 Android 测试..." -ForegroundColor Cyan
    
    # 设置环境并运行测试
    $testCommand = @"
cd /data/local/tmp/plthook && 
export LD_LIBRARY_PATH=/data/local/tmp/plthook:`$LD_LIBRARY_PATH && 
./run_tests.sh
"@
    
    Write-Host "执行测试命令..." -ForegroundColor Yellow
    & $adbPath shell $testCommand
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Android 测试完成" -ForegroundColor Green
    } else {
        Write-Host "✗ Android 测试失败" -ForegroundColor Red
    }
}

if (-not $Deploy -and -not $Test -and -not $All) {
    Write-Host ""
    Write-Host "使用方法:" -ForegroundColor Yellow
    Write-Host "  .\test_android.ps1 -Deploy     # 部署文件到设备" -ForegroundColor Gray
    Write-Host "  .\test_android.ps1 -Test       # 运行测试" -ForegroundColor Gray
    Write-Host "  .\test_android.ps1 -All        # 部署并测试" -ForegroundColor Gray
    Write-Host "  .\test_android.ps1 -All -Architecture arm64-v8a  # 指定架构" -ForegroundColor Gray
    Write-Host ""
    Write-Host "手动操作命令:" -ForegroundColor Yellow
    Write-Host "  adb push output/android/$Architecture/* /data/local/tmp/plthook/" -ForegroundColor Gray
    Write-Host "  adb shell 'cd /data/local/tmp/plthook && ./run_tests.sh'" -ForegroundColor Gray
}
