# PLTHook 内存监控测试程序

## 概述

PLTHook 内存监控测试程序是一个专门用于监控和分析程序内存使用情况的工具。它利用 PLTHook 库拦截内存分配函数，实时收集内存使用统计信息。

## 功能特性

### 🔍 内存监控功能
- **实时监控**: 定时输出内存使用统计信息
- **详细日志**: 可选的每次分配/释放详细记录
- **系统信息**: 显示系统总内存、可用内存和进程内存使用
- **泄漏检测**: 计算内存泄漏率和碎片化程度

### 📊 统计信息
- malloc/HeapAlloc 调用次数
- free/HeapFree 调用次数
- 总分配内存量
- 总释放内存量
- 当前内存使用量
- 峰值内存使用量
- 活跃内存块数量

### 🧪 测试模式
- 模拟内存分配测试
- 基本分配和释放操作
- 大块内存分配测试
- realloc/HeapReAlloc 操作测试
- 内存清理验证

## 平台支持

### Windows 平台
- **实现方式**: 钩取 kernel32.dll 中的 HeapAlloc/HeapFree/HeapReAlloc 函数
- **程序文件**: `memory_monitor_win.exe`
- **依赖库**: dbghelp.lib, psapi.lib
- **特殊功能**: 
  - 直接获取进程堆句柄
  - 使用 HeapSize 精确计算释放内存大小
  - 集成 Windows 性能计数器

### Android/Linux 平台
- **实现方式**: 钩取 libc 中的 malloc/free/realloc/calloc 函数
- **程序文件**: `memory_monitor`
- **依赖库**: libdl, libm
- **特殊功能**:
  - 使用 /proc/meminfo 获取系统内存信息
  - 通过 rusage 获取进程内存统计
  - 支持交叉编译

## 使用方法

### 基本语法
```bash
memory_monitor [选项]
```

### 命令行选项

| 选项 | 长选项 | 参数 | 说明 |
|------|--------|------|------|
| `-i` | `--interval` | SECONDS | 设置监控输出间隔（默认: 5秒） |
| `-d` | `--detailed` | - | 启用详细日志（每次分配/释放都输出） |
| `-t` | `--test` | - | 运行模拟测试 |
| `-r` | `--runtime` | SECONDS | 运行时长（默认: 无限） |
| `-h` | `--help` | - | 显示帮助信息 |

### 使用示例

#### 基本监控
```bash
# 持续监控，每5秒输出一次统计信息
./memory_monitor

# Windows
memory_monitor_win.exe
```

#### 自定义间隔监控
```bash
# 每10秒输出一次统计信息
./memory_monitor -i 10

# 启用详细日志，每次内存操作都记录
./memory_monitor -i 10 -d
```

#### 测试模式
```bash
# 运行内存分配测试，30秒后自动退出
./memory_monitor -t -r 30

# 运行测试并启用详细日志
./memory_monitor -t -d -r 60
```

#### 短期监控
```bash
# 监控60秒后自动退出
./memory_monitor -r 60 -i 2
```

## 输出格式

### 内存监控报告示例

```
==================== Memory Monitor Report [2025-07-07 12:20:15] ====================
Windows Heap Statistics:
  * HeapAlloc calls:    156
  * HeapFree calls:     134
  * total allocated:    2.45 MB
  * total freed:        1.98 MB
  * current usage:      478.23 KB
  * peak usage:         1.12 MB
  * active blocks:      22

System Memory Info:
  * total memory:       47.72 GB
  * available memory:   29.18 GB
  * process memory:     5.66 MB

Memory Usage Analysis:
  * average alloc size: 16.09 KB
  * memory leak ratio:  19.18%
  * fragmentation:      22 active blocks
================================================================
```

### 详细日志示例

```
[HeapAlloc] 1024 bytes allocated at 0x000002A1B2C4D870
[HeapAlloc] 2048 bytes allocated at 0x000002A1B2C4DC80
[HeapFree] 1024 bytes freed from 0x000002A1B2C4D870
[HeapReAlloc] 0x000002A1B2C4DC80 (2048 bytes) -> 0x000002A1B2C4DC80 (4096 bytes)
```

## 构建方法

### Windows 构建
```cmd
REM 使用 Visual Studio 编译器
cl /O2 /I.. memory_monitor_win.c ..\plthook_win32.c /Fememory_monitor_win.exe dbghelp.lib psapi.lib

REM 或使用批处理脚本
.\build_memory_monitor.bat
```

### Linux/Android 构建
```bash
# 使用 GCC
gcc -O2 -I.. memory_monitor.c ../plthook_elf.c -o memory_monitor -ldl -lm

# 使用 Makefile
make -f Makefile.memory

# Android NDK 构建
$ANDROID_NDK_ROOT/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android21-clang \
    -O2 -I.. memory_monitor.c ../plthook_elf.c -o memory_monitor -ldl
```

### CMake 构建
```bash
mkdir build && cd build
cmake .. -DBUILD_TESTS=ON
make memory_monitor
```

## 技术实现

### Windows 实现要点

1. **堆函数钩取**
   ```c
   // 钩取 HeapAlloc 函数
   ret = plthook_replace(plthook, "HeapAlloc", (void*)hook_HeapAlloc, (void**)&original_HeapAlloc);
   
   // 钩取函数实现
   static LPVOID WINAPI hook_HeapAlloc(HANDLE hHeap, DWORD dwFlags, SIZE_T dwBytes) {
       LPVOID result = original_HeapAlloc(hHeap, dwFlags, dwBytes);
       // 统计逻辑
       return result;
   }
   ```

2. **内存大小获取**
   ```c
   // 使用 HeapSize 获取内存块大小
   SIZE_T size = HeapSize(hHeap, 0, lpMem);
   ```

3. **进程内存信息**
   ```c
   PROCESS_MEMORY_COUNTERS pmc;
   GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc));
   size_t process_memory = pmc.WorkingSetSize;
   ```

### Unix 实现要点

1. **libc 函数钩取**
   ```c
   // 钩取 malloc 函数
   ret = plthook_replace(plthook, "malloc", (void*)hook_malloc, (void**)&original_malloc);
   
   // 获取原始函数地址
   original_malloc = dlsym(RTLD_DEFAULT, "malloc");
   ```

2. **内存块跟踪**
   ```c
   typedef struct memory_block {
       void *ptr;
       size_t size;
       time_t alloc_time;
       struct memory_block *next;
   } memory_block_t;
   ```

3. **系统内存信息**
   ```c
   // 读取 /proc/meminfo
   FILE *meminfo = fopen("/proc/meminfo", "r");
   
   // 使用 rusage 获取进程信息
   struct rusage usage;
   getrusage(RUSAGE_SELF, &usage);
   ```

## 注意事项

### 使用限制

1. **PLTHook 限制**
   - 只能钩取通过动态链接调用的函数
   - 静态链接的内存分配无法监控
   - 编译器内联优化可能影响钩取效果

2. **Windows 特殊情况**
   - HeapAlloc 钩取可能不完整（如示例中只捕获 HeapFree）
   - 某些系统函数使用内部内存管理
   - 需要适当的权限运行

3. **性能影响**
   - 每次内存操作都会增加钩子函数的开销
   - 详细日志模式会显著影响性能
   - 大量内存操作时可能产生明显延迟

### 最佳实践

1. **监控配置**
   - 根据应用场景调整监控间隔
   - 在开发和测试阶段启用详细日志
   - 生产环境使用较长的监控间隔

2. **结果分析**
   - 关注内存泄漏率（应该接近0%）
   - 监控峰值内存使用情况
   - 分析内存碎片化程度

3. **故障排除**
   - 如果钩取失败，检查目标函数是否动态链接
   - 验证 PLTHook 库是否正确加载
   - 确保有足够的权限执行内存钩取

## 扩展功能

### 可能的改进方向

1. **更详细的统计**
   - 内存分配大小分布
   - 内存生命周期分析
   - 调用栈跟踪

2. **可视化输出**
   - 生成内存使用图表
   - 实时内存使用曲线
   - HTML 报告生成

3. **配置文件支持**
   - 可配置的监控参数
   - 自定义输出格式
   - 警告阈值设置

4. **多进程监控**
   - 跨进程内存统计
   - 系统级内存监控
   - 容器环境支持

## 故障排除

### 常见问题

**Q: 为什么没有捕获到内存分配？**
A: 可能的原因：
- 目标函数是静态链接的
- 编译器进行了内联优化
- PLTHook 无法找到目标函数
- 权限不足

**Q: 统计数据不准确怎么办？**
A: 检查项目：
- 确认钩子函数正确安装
- 验证内存大小计算逻辑
- 检查重入保护是否正常工作

**Q: 程序运行缓慢？**
A: 优化建议：
- 减少监控输出频率
- 关闭详细日志模式
- 优化钩子函数的执行效率

这个内存监控工具为 PLTHook 项目提供了强大的调试和分析能力，可以帮助开发者更好地理解和优化程序的内存使用情况。
