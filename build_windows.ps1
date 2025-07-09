# PLTHook Windows Build Script
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

$rootDir = $PSScriptRoot
$buildDir = Join-Path $rootDir "build"
$outputDir = Join-Path $rootDir "output"

Write-Host "PLTHook Build Script" -ForegroundColor Green
Write-Host "===================" -ForegroundColor Green

function Clean-BuildDirectories {
    Write-Host "Cleaning build directories..." -ForegroundColor Yellow
    if (Test-Path $buildDir) {
        Remove-Item $buildDir -Recurse -Force
    }
    if (Test-Path $outputDir) {
        Remove-Item $outputDir -Recurse -Force
    }
    
    $testDir = Join-Path $rootDir "test"
    $toClean = @("*.dll", "*.exe", "*.lib", "*.exp", "*.obj", "*.so")
    foreach ($pattern in $toClean) {
        Get-ChildItem -Path $testDir -Filter $pattern -ErrorAction SilentlyContinue | Remove-Item -Force
    }
    
    Write-Host "Cleanup completed" -ForegroundColor Green
}

function Build-Windows {
    param([string]$Arch)
    
    Write-Host "Building Windows $Arch platform..." -ForegroundColor Yellow
    
    $winOutputDir = Join-Path $outputDir "windows\$Arch"
    New-Item -ItemType Directory -Path $winOutputDir -Force | Out-Null
    
    # Find Visual Studio
    $vsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vsWhere) {
        $vsPath = & $vsWhere -latest -property installationPath
        if ($vsPath) {
            $vcVarsPath = Join-Path $vsPath "VC\Auxiliary\Build\vcvarsall.bat"
            if (Test-Path $vcVarsPath) {
                Write-Host "Found Visual Studio: $vsPath" -ForegroundColor Green
                
                $vcArch = switch ($Arch) {
                    "x86" { "x86" }
                    "x64" { "x64" }
                    "arm64" { "arm64" }
                }
                
                $testDir = Join-Path $rootDir "test"
                Push-Location $testDir
                
                try {
                    $buildCmd = "`"$vcVarsPath`" $vcArch && nmake /f Makefile.win32 all"
                    Write-Host "Executing build command: $buildCmd" -ForegroundColor Cyan
                    
                    cmd /c $buildCmd
                    if ($LASTEXITCODE -ne 0) {
                        throw "Windows build failed"
                    }
                    
                    Copy-Item "libtest.dll" $winOutputDir -Force
                    Copy-Item "testprog.exe" $winOutputDir -Force
                    if (Test-Path "libtest.lib") {
                        Copy-Item "libtest.lib" $winOutputDir -Force
                    }
                    
                    Write-Host "Windows $Arch build completed" -ForegroundColor Green
                    Write-Host "Output directory: $winOutputDir" -ForegroundColor Green
                    
                } finally {
                    Pop-Location
                }
            }
        }
    } else {
        Write-Error "Visual Studio not found. Please install Visual Studio 2019 or later"
    }
}

function Run-WindowsTests {
    param([string]$Arch)
    
    $winOutputDir = Join-Path $outputDir "windows\$Arch"
    if (-not (Test-Path $winOutputDir)) {
        Write-Warning "Windows $Arch build artifacts not found, skipping tests"
        return
    }
    
    Write-Host "Running Windows $Arch tests..." -ForegroundColor Yellow
    
    Push-Location $winOutputDir
    try {
        Write-Host "Testing open mode..." -ForegroundColor Cyan
        .\testprog.exe open
        
        Write-Host "Testing open_by_handle mode..." -ForegroundColor Cyan
        .\testprog.exe open_by_handle
        
        Write-Host "Windows $Arch tests passed" -ForegroundColor Green
        
    } catch {
        Write-Error "Windows $Arch tests failed: $_"
    } finally {
        Pop-Location
    }
}

try {
    if ($Clean) {
        Clean-BuildDirectories
        return
    }
    
    New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    
    switch ($Platform) {
        "windows" {
            Build-Windows -Arch $Architecture
            Run-WindowsTests -Arch $Architecture
        }
        "all" {
            Build-Windows -Arch $Architecture
            Run-WindowsTests -Arch $Architecture
        }
    }
    
    Write-Host "`nBuild completed!" -ForegroundColor Green
    Write-Host "Output directory: $outputDir" -ForegroundColor Green
    
} catch {
    Write-Error "Build failed: $_"
    exit 1
}
