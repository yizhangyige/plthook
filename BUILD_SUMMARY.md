# PLTHook 构建过程总结

本文档总结了 PLTHook 项目的构建过程和结果。

## 构建环境信息

- **日期**: 2025年7月7日
- **平台**: Windows 11
- **工具链**: Visual Studio 2022 Community (17.14.7)
- **编译器**: MSVC 14.44.35211.0

## 已完成的构建

### ✅ Windows x64 平台

**构建状态**: 成功  
**输出目录**: `output/windows/x64/`

**构建产物**:
- `libtest.dll` - 测试用共享库
- `libtest.lib` - 导入库 (MSVC)
- `testprog.exe` - 测试程序

**测试结果**:
- ✅ `open` 模式测试通过
- ✅ `open_by_handle` 模式测试通过
- ⚠️ `open_by_address` 不支持 (Windows 平台限制)

## 提供的构建工具

### 1. PowerShell 构建脚本 (`build_windows.ps1`)
- 专门针对 Windows 平台优化
- 自动检测 Visual Studio 安装
- 支持 x86, x64, ARM64 架构
- 集成测试执行

**使用方法**:
```powershell
# 构建 x64 版本
.\build_windows.ps1 -Platform windows -Architecture x64

# 清理构建目录
.\build_windows.ps1 -Clean
```

### 2. 跨平台构建脚本 (`build.sh`)
- 支持 Linux, macOS, Windows (WSL), Android
- 基于 Bash，具有良好的跨平台兼容性
- 支持交叉编译

**使用方法**:
```bash
# 自动检测平台并构建
./build.sh -p auto -r

# 构建 Android 版本
./build.sh -p android -a arm64 -n /path/to/ndk
```

### 3. CMake 构建系统 (`CMakeLists.txt`)
- 现代化的跨平台构建系统
- 支持多种生成器 (Visual Studio, Ninja, Make)
- 集成 CPack 打包功能

**使用方法**:
```bash
mkdir build && cd build
cmake .. -DBUILD_TESTS=ON
cmake --build . --config Release
ctest
```

### 4. Python 发布构建器 (`release_builder.py`)
- 自动化多平台构建
- 生成发布包
- 构建信息记录

**使用方法**:
```bash
python release_builder.py --platforms windows-x64 linux-x86_64 android-arm64 --all
```

## 构建配置和特性

### 项目配置 (`plthook.toml`)
统一管理所有平台的构建参数、编译选项、依赖项等配置。

### 核心源文件
- `plthook.h` - 公共头文件
- `plthook_win32.c` - Windows 实现 (IAT 钩取)
- `plthook_elf.c` - Linux/Android 实现 (PLT 钩取)
- `plthook_osx.c` - macOS 实现

### 测试程序
- `test/libtest.c` - 测试用共享库源码
- `test/testprog.c` - 测试程序源码
- `test/run_tests_windows.bat` - Windows 测试脚本
- `test/android/run_tests.sh` - Android 测试脚本

## Android 构建准备

### NDK 配置更新
已优化 Android 构建配置文件:

**`test/android/jni/Android.mk`**:
- 添加了 PLTHook 静态库目标
- 改进了模块依赖关系
- 添加了完整的编译标志

**`test/android/jni/Application.mk`**:
- 支持多架构构建 (arm64-v8a, armeabi-v7a, x86_64)
- 优化的编译选项

### Android 构建命令
```bash
# 设置 NDK 路径
export ANDROID_NDK_ROOT=/path/to/android-ndk

# 构建所有架构
cd test/android
$ANDROID_NDK_ROOT/ndk-build clean
$ANDROID_NDK_ROOT/ndk-build

# 或使用 CMake
mkdir build-android && cd build-android
cmake .. -DCMAKE_TOOLCHAIN_FILE=$ANDROID_NDK_ROOT/build/cmake/android.toolchain.cmake \
         -DANDROID_ABI=arm64-v8a \
         -DANDROID_PLATFORM=android-21
make
```

## 示例程序

### `examples/malloc_hook.c`
演示如何使用 PLTHook 拦截 `malloc` 函数调用:
- 记录内存分配大小和地址
- 调用原始函数完成实际分配
- 跨平台兼容性处理

**编译运行**:
```bash
cd examples
make malloc_hook
./malloc_hook
```

## 已知问题和限制

### Windows 平台
1. **open_by_address 不支持**: Windows 平台的 PLT/IAT 机制限制
2. **架构支持**: 需要对应的 Visual Studio 工具链
3. **权限要求**: 某些钩取操作可能需要管理员权限

### Android 平台
1. **权限限制**: 现代 Android 版本对动态链接的限制增强
2. **SELinux 策略**: 可能影响某些钩取操作
3. **API 级别兼容性**: 不同 Android 版本的行为差异

### 一般限制
1. **内置函数**: 编译器内联的函数无法钩取
2. **静态链接**: 静态链接的函数无法通过 PLT/IAT 钩取
3. **安全软件**: 防病毒软件可能阻止钩取行为

## 后续开发计划

### 待完成的构建
- [ ] Linux x86_64 构建
- [ ] Linux ARM64 构建  
- [ ] macOS Intel 构建
- [ ] macOS Apple Silicon 构建
- [ ] Android ARM64 构建
- [ ] Android ARMv7 构建

### 功能改进
- [ ] 更好的错误处理和诊断
- [ ] 性能优化和基准测试
- [ ] 更多示例和文档
- [ ] CI/CD 集成

### 工具改进
- [ ] GUI 构建工具
- [ ] 自动化测试套件
- [ ] 性能分析工具
- [ ] 调试辅助工具

## 技术要点

### PLT/IAT 钩取原理
1. **PLT (Procedure Linkage Table)**: Unix 系统使用的动态链接机制
2. **IAT (Import Address Table)**: Windows 系统使用的动态链接机制
3. **钩取实现**: 修改函数地址表中的指针指向钩子函数

### 跨平台兼容性
- **统一接口**: 通过 `plthook.h` 提供一致的 API
- **平台特定实现**: 针对不同系统的底层机制实现
- **编译时选择**: 根据目标平台自动选择相应的源文件

### 内存保护处理
- **页面保护**: 修改内存保护属性以允许写入
- **原子操作**: 确保函数地址替换的原子性
- **错误恢复**: 处理内存保护和权限错误

## 总结

PLTHook 项目现已具备完整的构建工具链和跨平台支持。Windows x64 平台的构建和测试已验证成功，为其他平台的构建奠定了良好基础。

项目提供了多种构建方式以适应不同的开发环境和需求，从简单的 Makefile 到现代化的 CMake，再到自动化的 Python 脚本，开发者可以根据具体情况选择最适合的构建方法。

文档和示例程序有助于新用户快速上手，而详细的配置文件和构建脚本则为高级用户提供了充分的定制空间。
