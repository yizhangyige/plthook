#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <plthook.h>

#ifdef _WIN32
#include <windows.h>
#define LIBRARY_NAME "msvcrt.dll"
#else
#include <dlfcn.h>
#define LIBRARY_NAME "libc.so.6"
#endif

// 原始 malloc 函数指针
static void* (*original_malloc)(size_t size) = NULL;

// 钩子函数：记录内存分配
static void* hook_malloc(size_t size) {
    printf("[HOOK] malloc called with size: %zu\n", size);
    
    // 调用原始的 malloc
    void* result = original_malloc(size);
    
    printf("[HOOK] malloc returned: %p\n", result);
    return result;
}

int main() {
    plthook_t *plthook;
    int ret;
    
    printf("PLTHook 示例: 拦截 malloc 函数调用\n");
    printf("===================================\n");
    
    // 打开当前进程
    ret = plthook_open(&plthook, NULL);
    if (ret != 0) {
        fprintf(stderr, "plthook_open 失败: %s\n", plthook_error());
        return 1;
    }
    
    // 替换 malloc 函数
    ret = plthook_replace(plthook, "malloc", (void*)hook_malloc, (void**)&original_malloc);
    if (ret != 0) {
        fprintf(stderr, "plthook_replace 失败: %s\n", plthook_error());
        plthook_close(plthook);
        return 1;
    }
    
#ifndef _WIN32
    // 在 Unix 系统上，需要通过 dlsym 获取原始函数地址
    if (original_malloc == NULL) {
        original_malloc = dlsym(RTLD_DEFAULT, "malloc");
        if (original_malloc == NULL) {
            fprintf(stderr, "无法获取原始 malloc 函数地址\n");
            plthook_close(plthook);
            return 1;
        }
    }
#endif
    
    printf("成功安装 malloc 钩子函数\n\n");
    
    // 测试：分配一些内存
    printf("测试内存分配:\n");
    void *ptr1 = malloc(100);
    void *ptr2 = malloc(256);
    void *ptr3 = malloc(1024);
    
    // 释放内存
    free(ptr1);
    free(ptr2);
    free(ptr3);
    
    printf("\n测试完成\n");
    
    // 清理
    plthook_close(plthook);
    
    return 0;
}
