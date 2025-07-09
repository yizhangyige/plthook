# 多线程内存监控测试使用指南

## 概述

`multithread_memory_test` 是一个专为 Android 平台设计的多线程内存监控测试程序，用于验证内存管理的正确性和监控内存使用情况。

## 功能特性

### 三线程架构
- **监测线程**: 每2秒输出详细的内存使用统计
- **申请线程**: 每0.5秒分配随机大小的内存块
- **释放线程**: 每1秒随机释放已分配的内存块

### 监控能力
- 实时堆内存统计（分配/释放/峰值）
- 系统内存信息（VSS/RSS/栈使用）
- 活跃内存块数量跟踪
- 自动内存泄漏防护

## 使用方法

### 构建
```bash
# 构建所有Android架构
.\build_android.ps1
```

### 部署和测试
```bash
# 自动部署并运行完整测试（包括多线程内存监控）
.\test_android.ps1 -All

# 仅部署文件
.\test_android.ps1 -Deploy

# 仅运行测试
.\test_android.ps1 -Test
```

### 单独运行
```bash
# 在Android设备上运行30秒测试
adb shell 'cd /data/local/tmp/plthook && ./multithread_memory_test -t 30'

# 无限期运行（按Ctrl+C停止）
adb shell 'cd /data/local/tmp/plthook && ./multithread_memory_test'
```

### 命令行选项
```
./multithread_memory_test [选项]
  -t, --time SECONDS    运行时间（秒），默认为无限
  -h, --help            显示帮助信息
```

## 输出示例

```
Android 多线程内存监控测试程序启动
==================================
配置:
  运行时间: 有限
  监控间隔: 2000 毫秒
  分配间隔: 500 毫秒
  释放间隔: 1000 毫秒
  最大内存块: 1000

所有线程已启动，开始监控...

========== 内存监测报告 [1751945609431] ==========
堆内存统计:
  当前分配: 8958.58 KB (15 个块)
  峰值使用: 8958.58 KB
  总计分配: 16716.62 KB
  总计释放: 7758.04 KB
系统内存信息:
  虚拟内存 (VSS): 23.91 MB
  物理内存 (RSS): 11.43 MB
  栈使用 (近似): 0.00 KB
=====================================

[申请] 分配 394989 字节内存 @ 0x76f400d8c0
[释放] 释放内存 @ 0x76f400d0c0

最终统计:
  总计分配: 18097.28 KB
  总计释放: 8707.85 KB
  峰值使用: 9389.43 KB
  剩余块数: 16

清理剩余内存...
清理完成: 释放了 16 个内存块，总计 9389.43 KB
程序正常退出
```

## 技术特点

### 线程安全
- 使用互斥锁保护所有共享数据结构
- 线程间无数据竞争
- 支持并发内存操作

### 内存管理
- 自动跟踪所有分配的内存块
- 程序退出时自动清理所有内存
- 有效防止内存泄漏

### 信号处理
- 支持 SIGINT (Ctrl+C) 和 SIGTERM 信号
- 优雅退出机制
- 确保清理工作完成

## 配置参数

可以通过修改源码中的宏定义来调整测试参数：

```c
#define MAX_MEMORY_BLOCKS 1000        // 最大内存块数量
#define MIN_BLOCK_SIZE 1024           // 最小块大小 (1KB)
#define MAX_BLOCK_SIZE (1024 * 1024)  // 最大块大小 (1MB)
#define MONITOR_INTERVAL_MS 2000      // 监控间隔 (2秒)
#define ALLOC_INTERVAL_MS 500         // 分配间隔 (0.5秒)
#define FREE_INTERVAL_MS 1000         // 释放间隔 (1秒)
```

## 注意事项

### 内存使用
- 测试程序会持续分配内存，请确保设备有足够的可用内存
- 默认情况下最多保持1000个活跃内存块
- 单个内存块大小在1KB到1MB之间随机

### 性能影响
- 程序运行期间会占用CPU和内存资源
- 建议在测试环境中运行，避免影响其他应用
- 长时间运行可能会影响设备性能

### 兼容性
- 适用于Android 8.0及以上版本
- 支持arm64-v8a、armeabi-v7a、x86_64架构
- 需要调试权限或root权限以访问某些系统信息

## 故障排除

### 常见问题

1. **程序启动失败**
   - 检查文件权限：`chmod +x multithread_memory_test`
   - 确认架构匹配：使用对应设备架构的版本

2. **内存分配失败**
   - 设备内存不足，尝试减少MAX_MEMORY_BLOCKS
   - 系统限制，可能需要root权限

3. **线程创建失败**
   - 系统资源不足
   - 重启设备后重试

### 调试方法

1. **查看Android日志**
   ```bash
   adb logcat | grep MemoryTest
   ```

2. **检查系统资源**
   ```bash
   adb shell cat /proc/meminfo
   adb shell cat /proc/[pid]/status
   ```

3. **监控CPU使用**
   ```bash
   adb shell top | grep multithread
   ```

## 相关文档

- [Android 多线程内存监控测试成功报告](ANDROID_MULTITHREAD_MEMORY_TEST_SUCCESS.md)
- [Android 测试成功报告](ANDROID_TEST_SUCCESS.md)
- [项目状态文档](PROJECT_STATUS.md)
