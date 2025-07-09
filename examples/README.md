# PLTHook 示例程序

本目录包含演示 PLTHook 使用方法的示例程序。

## 示例列表

### 1. malloc_hook.c
演示如何拦截和记录 `malloc` 函数调用。

**功能:**
- 钩取进程中的 `malloc` 函数
- 记录每次内存分配的大小和返回地址
- 调用原始的 `malloc` 函数完成实际分配

**编译方法:**

Windows (MSVC):
```cmd
cl /I.. malloc_hook.c ..\plthook_win32.c /link dbghelp.lib
```

Linux/macOS:
```bash
gcc -I.. -o malloc_hook malloc_hook.c ../plthook_elf.c -ldl
# macOS:
gcc -I.. -o malloc_hook malloc_hook.c ../plthook_osx.c -ldl
```

**运行:**
```bash
./malloc_hook
```

**预期输出:**
```
PLTHook 示例: 拦截 malloc 函数调用
===================================
成功安装 malloc 钩子函数

测试内存分配:
[HOOK] malloc called with size: 100
[HOOK] malloc returned: 0x7f8b4c000b70
[HOOK] malloc called with size: 256
[HOOK] malloc returned: 0x7f8b4c000bd0
[HOOK] malloc called with size: 1024
[HOOK] malloc returned: 0x7f8b4c000ce0

测试完成
```

## 构建所有示例

使用提供的 Makefile:

```bash
# 在 examples 目录中
make all

# 清理
make clean
```

## 注意事项

1. **Windows 平台**: 原始函数地址通过 `plthook_replace` 的第四个参数获取
2. **Unix 平台**: 需要使用 `dlsym(RTLD_DEFAULT, "function_name")` 获取原始函数地址
3. **安全性**: 在生产环境中使用时要小心处理错误情况
4. **性能**: 钩子函数会增加函数调用的开销，在性能敏感的场景中需要考虑

## 进阶用法

- 钩取自定义库中的函数
- 条件性函数替换
- 函数调用统计和分析
- 动态库加载时的自动钩取
