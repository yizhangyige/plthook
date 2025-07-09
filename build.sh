#!/bin/bash

# PLTHook 跨平台构建脚本
# 支持 Linux, macOS, Windows (WSL), Android

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
OUTPUT_DIR="$SCRIPT_DIR/output"
PLATFORM=""
ARCHITECTURE="x86_64"
ANDROID_NDK_PATH=""
BUILD_TYPE="Release"
CLEAN=false
RUN_TESTS=false

# 帮助信息
show_help() {
    echo "PLTHook 构建脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -p, --platform PLATFORM    目标平台 (linux|macos|windows|android|auto)"
    echo "  -a, --arch ARCH            目标架构 (x86_64|arm64|armv7)"
    echo "  -n, --ndk-path PATH        Android NDK 路径"
    echo "  -t, --build-type TYPE      构建类型 (Debug|Release|RelWithDebInfo)"
    echo "  -c, --clean                清理构建目录"
    echo "  -r, --run-tests            运行测试"
    echo "  -h, --help                 显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -p linux -a x86_64 -r"
    echo "  $0 -p android -n /path/to/ndk -a arm64"
    echo "  $0 -p auto -c"
}

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检测平台
detect_platform() {
    case "$(uname -s)" in
        Linux*)
            if [ -n "$ANDROID_NDK_PATH" ]; then
                echo "android"
            else
                echo "linux"
            fi
            ;;
        Darwin*)
            echo "macos"
            ;;
        CYGWIN*|MINGW*|MSYS*)
            echo "windows"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

# 检测架构
detect_architecture() {
    case "$(uname -m)" in
        x86_64|amd64)
            echo "x86_64"
            ;;
        arm64|aarch64)
            echo "arm64"
            ;;
        armv7l)
            echo "armv7"
            ;;
        *)
            echo "x86_64"  # 默认
            ;;
    esac
}

# 清理函数
clean_build() {
    log_info "清理构建目录..."
    
    [ -d "$BUILD_DIR" ] && rm -rf "$BUILD_DIR"
    [ -d "$OUTPUT_DIR" ] && rm -rf "$OUTPUT_DIR"
    
    # 清理测试目录中的构建产物
    cd "$SCRIPT_DIR/test"
    rm -f *.so *.dll *.exe *.dylib testprog libtest.*
    
    # 清理 Android 构建产物
    if [ -d "$SCRIPT_DIR/test/android" ]; then
        cd "$SCRIPT_DIR/test/android"
        rm -rf libs obj
    fi
    
    log_success "清理完成"
}

# Linux 构建
build_linux() {
    log_info "构建 Linux $ARCHITECTURE 平台..."
    
    mkdir -p "$BUILD_DIR/linux-$ARCHITECTURE"
    cd "$BUILD_DIR/linux-$ARCHITECTURE"
    
    # 配置 CMake
    cmake "$SCRIPT_DIR" \
        -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
        -DBUILD_SHARED_LIBS=ON \
        -DBUILD_TESTS=ON \
        -DCMAKE_INSTALL_PREFIX="$OUTPUT_DIR/linux-$ARCHITECTURE"
    
    # 构建
    make -j$(nproc)
    
    # 安装
    make install
    
    log_success "Linux $ARCHITECTURE 构建完成"
}

# macOS 构建
build_macos() {
    log_info "构建 macOS $ARCHITECTURE 平台..."
    
    mkdir -p "$BUILD_DIR/macos-$ARCHITECTURE"
    cd "$BUILD_DIR/macos-$ARCHITECTURE"
    
    # 配置 CMake
    local cmake_args=(
        "$SCRIPT_DIR"
        -DCMAKE_BUILD_TYPE="$BUILD_TYPE"
        -DBUILD_SHARED_LIBS=ON
        -DBUILD_TESTS=ON
        -DCMAKE_INSTALL_PREFIX="$OUTPUT_DIR/macos-$ARCHITECTURE"
    )
    
    # 设置架构特定的配置
    if [ "$ARCHITECTURE" = "arm64" ]; then
        cmake_args+=(-DCMAKE_OSX_ARCHITECTURES=arm64)
    elif [ "$ARCHITECTURE" = "x86_64" ]; then
        cmake_args+=(-DCMAKE_OSX_ARCHITECTURES=x86_64)
    fi
    
    cmake "${cmake_args[@]}"
    
    # 构建
    make -j$(sysctl -n hw.ncpu)
    
    # 安装
    make install
    
    log_success "macOS $ARCHITECTURE 构建完成"
}

# Windows 构建 (使用 MinGW 或在 WSL 中)
build_windows() {
    log_info "构建 Windows $ARCHITECTURE 平台..."
    
    # 检查是否在 WSL 环境中
    if grep -qi microsoft /proc/version 2>/dev/null; then
        log_info "检测到 WSL 环境，使用交叉编译..."
        
        # 安装必要的工具
        if ! command -v x86_64-w64-mingw32-gcc &> /dev/null; then
            log_warning "未找到 MinGW，尝试安装..."
            sudo apt-get update
            sudo apt-get install -y gcc-mingw-w64-x86-64 g++-mingw-w64-x86-64
        fi
        
        mkdir -p "$BUILD_DIR/windows-$ARCHITECTURE"
        cd "$BUILD_DIR/windows-$ARCHITECTURE"
        
        # 使用 MinGW 交叉编译
        cmake "$SCRIPT_DIR" \
            -DCMAKE_SYSTEM_NAME=Windows \
            -DCMAKE_C_COMPILER=x86_64-w64-mingw32-gcc \
            -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
            -DBUILD_SHARED_LIBS=ON \
            -DBUILD_TESTS=ON \
            -DCMAKE_INSTALL_PREFIX="$OUTPUT_DIR/windows-$ARCHITECTURE"
        
        make -j$(nproc)
        make install
        
    else
        # 使用原生 Makefile
        log_info "使用原生 Windows 构建环境..."
        cd "$SCRIPT_DIR/test"
        
        if command -v cl &> /dev/null; then
            # 使用 MSVC
            nmake /f Makefile.win32 all
        elif command -v gcc &> /dev/null; then
            # 使用 MinGW
            make UNAME_S=MINGW32_NT
        else
            log_error "未找到支持的编译器 (cl 或 gcc)"
            exit 1
        fi
        
        # 复制构建产物
        mkdir -p "$OUTPUT_DIR/windows-$ARCHITECTURE/bin"
        cp *.dll *.exe "$OUTPUT_DIR/windows-$ARCHITECTURE/bin/" 2>/dev/null || true
    fi
    
    log_success "Windows $ARCHITECTURE 构建完成"
}

# Android 构建
build_android() {
    log_info "构建 Android $ARCHITECTURE 平台..."
    
    if [ -z "$ANDROID_NDK_PATH" ]; then
        log_error "请提供 Android NDK 路径 (-n 选项)"
        exit 1
    fi
    
    if [ ! -d "$ANDROID_NDK_PATH" ]; then
        log_error "Android NDK 路径不存在: $ANDROID_NDK_PATH"
        exit 1
    fi
    
    # 设置 Android 架构映射
    local android_abi
    case "$ARCHITECTURE" in
        arm64)
            android_abi="arm64-v8a"
            ;;
        armv7)
            android_abi="armeabi-v7a"
            ;;
        x86_64)
            android_abi="x86_64"
            ;;
        *)
            log_error "不支持的 Android 架构: $ARCHITECTURE"
            exit 1
            ;;
    esac
    
    mkdir -p "$BUILD_DIR/android-$ARCHITECTURE"
    cd "$BUILD_DIR/android-$ARCHITECTURE"
    
    # 使用 CMake + NDK
    cmake "$SCRIPT_DIR" \
        -DCMAKE_TOOLCHAIN_FILE="$ANDROID_NDK_PATH/build/cmake/android.toolchain.cmake" \
        -DANDROID_ABI="$android_abi" \
        -DANDROID_PLATFORM=android-21 \
        -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
        -DBUILD_SHARED_LIBS=ON \
        -DBUILD_TESTS=ON \
        -DBUILD_ANDROID=ON \
        -DCMAKE_INSTALL_PREFIX="$OUTPUT_DIR/android-$ARCHITECTURE"
    
    make -j$(nproc)
    make install
    
    log_success "Android $ARCHITECTURE 构建完成"
}

# 运行测试
run_tests() {
    log_info "运行测试..."
    
    local test_dir
    case "$PLATFORM" in
        linux)
            test_dir="$OUTPUT_DIR/linux-$ARCHITECTURE"
            ;;
        macos)
            test_dir="$OUTPUT_DIR/macos-$ARCHITECTURE"
            ;;
        windows)
            test_dir="$OUTPUT_DIR/windows-$ARCHITECTURE"
            ;;
        android)
            log_warning "Android 测试需要在设备上运行，跳过"
            return
            ;;
    esac
    
    if [ ! -d "$test_dir" ]; then
        log_warning "测试目录不存在，跳过测试: $test_dir"
        return
    fi
    
    cd "$test_dir"
    
    # 设置库路径
    if [ "$PLATFORM" = "linux" ]; then
        export LD_LIBRARY_PATH="$test_dir/lib:$LD_LIBRARY_PATH"
    elif [ "$PLATFORM" = "macos" ]; then
        export DYLD_LIBRARY_PATH="$test_dir/lib:$DYLD_LIBRARY_PATH"
    fi
    
    # 运行测试
    local testprog="$test_dir/bin/testprog"
    if [ "$PLATFORM" = "windows" ]; then
        testprog="$testprog.exe"
    fi
    
    if [ -x "$testprog" ]; then
        log_info "运行 open 测试..."
        "$testprog" open
        
        log_info "运行 open_by_handle 测试..."
        "$testprog" open_by_handle
        
        if [ "$PLATFORM" != "windows" ]; then
            log_info "运行 open_by_address 测试..."
            "$testprog" open_by_address
        fi
        
        log_success "所有测试通过"
    else
        log_warning "测试程序不存在: $testprog"
    fi
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--platform)
            PLATFORM="$2"
            shift 2
            ;;
        -a|--arch)
            ARCHITECTURE="$2"
            shift 2
            ;;
        -n|--ndk-path)
            ANDROID_NDK_PATH="$2"
            shift 2
            ;;
        -t|--build-type)
            BUILD_TYPE="$2"
            shift 2
            ;;
        -c|--clean)
            CLEAN=true
            shift
            ;;
        -r|--run-tests)
            RUN_TESTS=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 主逻辑
main() {
    log_info "PLTHook 构建脚本启动"
    
    # 清理
    if [ "$CLEAN" = true ]; then
        clean_build
        if [ -z "$PLATFORM" ]; then
            exit 0
        fi
    fi
    
    # 自动检测平台
    if [ "$PLATFORM" = "auto" ] || [ -z "$PLATFORM" ]; then
        PLATFORM=$(detect_platform)
        log_info "自动检测平台: $PLATFORM"
    fi
    
    # 自动检测架构
    if [ -z "$ARCHITECTURE" ]; then
        ARCHITECTURE=$(detect_architecture)
        log_info "自动检测架构: $ARCHITECTURE"
    fi
    
    # 创建输出目录
    mkdir -p "$OUTPUT_DIR"
    
    # 根据平台构建
    case "$PLATFORM" in
        linux)
            build_linux
            ;;
        macos)
            build_macos
            ;;
        windows)
            build_windows
            ;;
        android)
            build_android
            ;;
        *)
            log_error "不支持的平台: $PLATFORM"
            show_help
            exit 1
            ;;
    esac
    
    # 运行测试
    if [ "$RUN_TESTS" = true ]; then
        run_tests
    fi
    
    log_success "构建完成!"
    log_info "输出目录: $OUTPUT_DIR"
}

# 运行主逻辑
main "$@"
