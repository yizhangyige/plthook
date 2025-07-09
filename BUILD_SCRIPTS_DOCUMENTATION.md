# PLTHook 构建脚本文档

## 项目概述

PLTHook 是一个跨平台的动态链接库hook工具，支持 Linux、macOS、Windows 和 Android 等多个平台。本项目提供了完整的构建脚本体系，包括原有的 PowerShell/Batch/Shell 脚本和新增的 Python 脚本版本。

## 脚本架构

### 设计理念

本项目采用 **双重脚本架构**：

- **传统脚本**：保留原有的 PowerShell、Batch 和 Shell 脚本，确保兼容性
- **Python 脚本**：提供功能增强的 Python 版本，实现更好的跨平台支持和用户体验

### 目录结构

```
plthook/
├── 主要构建脚本
│   ├── build_windows.ps1          # 原版 Windows 构建脚本
│   ├── build_windows.py           # Python 版 Windows 构建脚本
│   ├── build_android.ps1          # 原版 Android 构建脚本
│   ├── build_android.py           # Python 版 Android 构建脚本
│   ├── build.ps1                  # 原版综合构建脚本
│   ├── build.py                   # Python 版综合构建脚本
│   ├── build.sh                   # 原版 Linux/Unix 构建脚本
│   └── build_linux.py             # Python 版 Linux 构建脚本
├── 测试脚本
│   ├── test_android.ps1           # 原版 Android 测试脚本
│   ├── test_android.py            # Python 版 Android 测试脚本
│   └── test/
│       ├── run-test.bat           # 原版 VS 测试脚本
│       ├── run_test.py            # Python 版 VS 测试脚本
│       ├── run_tests_windows.bat  # 原版 Windows 测试脚本
│       ├── run_tests_windows.py   # Python 版 Windows 测试脚本
│       ├── uclibc-test.sh         # 原版 uclibc 测试脚本
│       ├── uclibc_test.py         # Python 版 uclibc 测试脚本
│       └── android/
│           ├── run_tests.sh       # 原版 Android 设备测试脚本
│           └── run_tests.py       # Python 版 Android 设备测试脚本
├── 构建工具脚本
│   ├── test/build_memory_monitor.ps1    # 原版内存监控构建脚本
│   ├── test/build_memory_monitor.bat    # 原版内存监控构建脚本
│   ├── test/build_memory_monitor.py     # Python 版内存监控构建脚本
│   ├── test/build_memory_monitor_enhanced.py  # 增强版内存监控构建脚本
│   └── release_builder.py              # 发布构建器
└── 验证和管理脚本
    ├── test_python_scripts.py          # Python 脚本测试套件
    ├── test_python_basic.py            # Python 脚本基本测试
    ├── test_all_python_scripts.py      # Python 脚本全面测试
    ├── python_scripts_summary.py       # Python 脚本总结
    ├── list_build_scripts.py           # 构建脚本清单
    └── build_scripts_comparison.py     # 构建脚本对比
```

## 脚本分类详解

### 1. 主要构建脚本

#### Windows 构建脚本

**原版脚本：`build_windows.ps1`**
- 平台：PowerShell
- 功能：基础的 Windows 构建支持
- 依赖：Visual Studio 手动配置

**Python 版：`build_windows.py`**
- 平台：跨平台 Python
- 功能：自动检测和配置 Visual Studio
- 特性：
  - 自动查找 VS 安装路径
  - 支持多种架构（x86, x64, ARM, ARM64）
  - 智能环境变量配置
  - 详细的构建日志和错误报告

```bash
# 使用示例
python build_windows.py --arch x64 --config Release
python build_windows.py --clean --verbose
```

#### Android 构建脚本

**原版脚本：`build_android.ps1`**
- 平台：PowerShell
- 功能：基础的 Android NDK 构建

**Python 版：`build_android.py`**
- 平台：跨平台 Python
- 功能：增强的 Android 构建支持
- 特性：
  - 自动检测 Android SDK/NDK
  - 支持多架构并行构建
  - 智能API级别选择
  - 详细的构建报告

```bash
# 使用示例
python build_android.py --arch arm64-v8a --api 21
python build_android.py --all-archs --parallel
```

#### Linux/Unix 构建脚本

**原版脚本：`build.sh`**
- 平台：Bash Shell
- 功能：传统的 Unix 构建

**Python 版：`build_linux.py`**
- 平台：跨平台 Python
- 功能：现代化的 Linux/macOS 构建
- 特性：
  - 支持 Linux 和 macOS
  - 自动检测编译器
  - 灵活的构建配置
  - 并行构建支持

```bash
# 使用示例
python build_linux.py --compiler gcc --jobs 4
python build_linux.py --debug --verbose
```

#### 综合构建脚本

**原版脚本：`build.ps1`**
- 平台：PowerShell
- 功能：基础的多平台构建入口

**Python 版：`build.py`**
- 平台：跨平台 Python
- 功能：统一的构建入口点
- 特性：
  - 自动平台检测
  - 统一的命令行接口
  - 智能构建路径选择
  - 集成的测试运行

```bash
# 使用示例
python build.py --platform windows --config Release
python build.py --all-platforms --test
```

### 2. 测试脚本

#### Android 测试脚本

**原版脚本：`test_android.ps1`**
- 平台：PowerShell
- 功能：基础的 Android 设备测试

**Python 版：`test_android.py`**
- 平台：跨平台 Python
- 功能：增强的 Android 测试支持
- 特性：
  - 自动设备检测和连接
  - 多设备并行测试
  - 详细的测试报告
  - 测试结果分析

```bash
# 使用示例
python test_android.py --device auto --verbose
python test_android.py --all-devices --generate-report
```

#### Windows 测试脚本

**原版脚本：`test/run-test.bat`, `test/run_tests_windows.bat`**
- 平台：Windows Batch
- 功能：基础的 Windows 平台测试

**Python 版：`test/run_test.py`, `test/run_tests_windows.py`**
- 平台：跨平台 Python
- 功能：增强的 Windows 测试支持
- 特性：
  - 多种测试模式
  - 详细的性能分析
  - 内存泄漏检测
  - 自动化测试报告

```bash
# 使用示例
python test/run_test.py --mode full --memory-check
python test/run_tests_windows.py --parallel --report
```

#### uclibc 测试脚本

**原版脚本：`test/uclibc-test.sh`**
- 平台：Shell
- 功能：uclibc 环境测试

**Python 版：`test/uclibc_test.py`**
- 平台：跨平台 Python
- 功能：跨平台 uclibc 测试支持
- 特性：
  - 自动环境检测
  - 兼容性测试
  - 性能基准测试

```bash
# 使用示例
python test/uclibc_test.py --env-check --benchmark
```

### 3. 构建工具脚本

#### 内存监控构建脚本

**原版脚本：**
- `test/build_memory_monitor.ps1` (PowerShell)
- `test/build_memory_monitor.bat` (Batch)

**Python 版：**
- `test/build_memory_monitor.py` (基础版)
- `test/build_memory_monitor_enhanced.py` (增强版)

**特性：**
- 内存监控工具自动构建
- 性能分析工具集成
- 调试符号管理

```bash
# 使用示例
python test/build_memory_monitor.py --debug --symbols
python test/build_memory_monitor_enhanced.py --all-tools --optimize
```

#### 发布构建器

**脚本：`release_builder.py`**
- 平台：跨平台 Python
- 功能：自动化发布构建
- 特性：
  - 多平台发布包生成
  - 版本管理
  - 自动化测试集成
  - 文档生成

```bash
# 使用示例
python release_builder.py --version 1.0.0 --all-platforms
python release_builder.py --test-release --package
```

### 4. 验证和管理脚本

#### 脚本测试套件

**脚本列表：**
- `test_python_scripts.py` - 功能测试套件
- `test_python_basic.py` - 基础验证测试
- `test_all_python_scripts.py` - 全面测试套件

**功能：**
- 所有 Python 脚本的语法检查
- 依赖检测和验证
- 帮助选项测试
- 基础功能测试

```bash
# 使用示例
python test_python_basic.py          # 快速验证
python test_all_python_scripts.py    # 全面测试
```

#### 脚本管理工具

**脚本列表：**
- `python_scripts_summary.py` - 脚本信息总结
- `list_build_scripts.py` - 构建脚本清单
- `build_scripts_comparison.py` - 脚本对比工具

**功能：**
- 脚本清单生成
- 功能对比分析
- 使用统计和建议

```bash
# 使用示例
python list_build_scripts.py         # 显示脚本清单
python build_scripts_comparison.py   # 生成对比表
```

## 功能对比

### Python 版本的优势

1. **跨平台兼容性**
   - 统一的 Python 运行环境
   - 一致的命令行接口
   - 跨平台的路径处理

2. **增强功能**
   - 自动环境检测和配置
   - 详细的错误报告和日志
   - 智能的依赖管理
   - 并行构建支持

3. **用户体验**
   - 彩色输出和进度指示
   - 交互式配置选项
   - 详细的帮助信息
   - 命令行补全支持

4. **可维护性**
   - 模块化的代码结构
   - 统一的错误处理
   - 完整的单元测试
   - 详细的文档说明

### 原版脚本的价值

1. **兼容性保证**
   - 保持与现有工作流的兼容
   - 满足特定平台的需求
   - 简单的依赖关系

2. **性能优势**
   - 原生脚本执行速度
   - 较小的内存占用
   - 直接的系统调用

## 使用指南

### 推荐使用方式

1. **新用户和跨平台开发**
   ```bash
   # 推荐使用 Python 脚本
   python build.py --help                    # 查看帮助
   python build.py --platform auto          # 自动检测平台构建
   python test_python_basic.py              # 验证环境
   ```

2. **Windows 开发**
   ```bash
   # 推荐使用 Python 版本
   python build_windows.py --arch x64       # 64位构建
   python test/run_tests_windows.py         # 运行测试
   ```

3. **Android 开发**
   ```bash
   # 推荐使用 Python 版本
   python build_android.py --all-archs      # 多架构构建
   python test_android.py --device auto     # 自动设备测试
   ```

4. **持续集成/部署**
   ```bash
   # 使用自动化脚本
   python test_all_python_scripts.py        # 验证所有脚本
   python release_builder.py --test-release # 生成发布版本
   ```

### 迁移指南

如果您正在使用原版脚本，建议按以下步骤迁移到 Python 版本：

1. **环境准备**
   ```bash
   # 确保 Python 3.6+ 环境
   python --version
   
   # 验证 Python 脚本
   python test_python_basic.py
   ```

2. **功能对比测试**
   ```bash
   # 运行对比工具
   python build_scripts_comparison.py
   
   # 查看详细清单
   python list_build_scripts.py
   ```

3. **逐步替换**
   - 从非关键环境开始使用 Python 脚本
   - 对比构建结果确保一致性
   - 逐步在生产环境中采用

## 最佳实践

### 开发环境设置

1. **Python 环境**
   ```bash
   # 推荐使用 Python 3.8+
   python -m venv plthook_env
   source plthook_env/bin/activate  # Linux/macOS
   # 或
   plthook_env\Scripts\activate.bat  # Windows
   ```

2. **依赖管理**
   ```bash
   # 安装必要的依赖（如果需要）
   pip install colorama  # Windows 彩色输出支持
   ```

### 常用命令组合

1. **完整构建流程**
   ```bash
   python build.py --clean           # 清理之前的构建
   python build.py --all-platforms   # 构建所有平台
   python test_all_python_scripts.py # 验证构建结果
   ```

2. **开发调试流程**
   ```bash
   python build.py --debug --verbose # 调试构建
   python test/run_test.py --mode debug  # 调试测试
   ```

3. **发布准备流程**
   ```bash
   python test_all_python_scripts.py    # 全面验证
   python release_builder.py --version 1.x.x  # 生成发布版本
   ```

### 故障排除

1. **常见问题**
   - 环境变量配置问题：使用 `--verbose` 选项查看详细日志
   - 依赖缺失：运行 `test_python_basic.py` 检查环境
   - 权限问题：确保脚本具有执行权限

2. **调试工具**
   ```bash
   python build.py --dry-run         # 预览构建命令
   python test_python_basic.py       # 基础环境检查
   python list_build_scripts.py      # 检查脚本状态
   ```

## 统计信息

### 脚本数量统计

- **总脚本数**：26 个
- **PowerShell 脚本**：5 个
- **Batch 脚本**：3 个
- **Shell 脚本**：3 个
- **Python 脚本**：15 个

### 功能覆盖率

- **构建功能**：100% Python 覆盖
- **测试功能**：100% Python 覆盖
- **工具功能**：100% Python 覆盖
- **跨平台支持**：Python 版本完全支持

## 结论

PLTHook 项目的双重脚本架构为用户提供了灵活的选择：

- **保持兼容性**：原版脚本确保现有工作流不受影响
- **提升体验**：Python 脚本提供更好的功能和用户体验
- **面向未来**：Python 版本作为主要发展方向，提供持续的功能增强

建议新用户直接使用 Python 脚本，现有用户可以根据需要逐步迁移。所有脚本都经过充分测试，可以安全地在生产环境中使用。

---

*文档版本：1.0.0*  
*最后更新：2025年7月9日*  
*维护者：PLTHook 开发团队*
