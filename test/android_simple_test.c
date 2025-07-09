// Android PLTHook 简化测试程序
#include <plthook.h>
#include <stdio.h>
#include <dlfcn.h>
#include <string.h>

// 简单的测试函数
static void show_hooked_functions(plthook_t *plthook) {
    unsigned int pos = 0;
    const char *name;
    void **addr;
    int count = 0;
    
    printf("可用的钩子函数:\n");
    while (plthook_enum(plthook, &pos, &name, &addr) == 0) {
        printf("  %d: %s @ %p\n", ++count, name, addr);
        if (count >= 20) {  // 只显示前20个
            printf("  ... (总共更多函数)\n");
            break;
        }
    }
    printf("总共枚举到 %d+ 个函数\n", count);
}

int main(int argc, char *argv[]) {
    plthook_t *plthook = NULL;
    int ret;
    
    printf("Android PLTHook 简化测试\n");
    printf("========================\n");
    
    if (argc < 2) {
        printf("用法: %s <mode>\n", argv[0]);
        printf("模式:\n");
        printf("  open        - 测试 plthook_open\n");
        printf("  handle      - 测试 plthook_open_by_handle\n");
        printf("  address     - 测试 plthook_open_by_address\n");
        return 1;
    }
    
    const char *mode = argv[1];
    
    if (strcmp(mode, "open") == 0) {
        printf("测试 plthook_open...\n");
        ret = plthook_open(&plthook, NULL);
        if (ret != 0) {
            printf("plthook_open 失败: %s\n", plthook_error());
            return 1;
        }
        printf("✓ plthook_open 成功\n");
        show_hooked_functions(plthook);
        
    } else if (strcmp(mode, "handle") == 0) {
        printf("测试 plthook_open_by_handle...\n");
        void *handle = dlopen("./libtest.so", RTLD_LAZY);
        if (!handle) {
            printf("无法加载 libtest.so: %s\n", dlerror());
            return 1;
        }
        
        ret = plthook_open_by_handle(&plthook, handle);
        if (ret != 0) {
            printf("plthook_open_by_handle 失败: %s\n", plthook_error());
            dlclose(handle);
            return 1;
        }
        printf("✓ plthook_open_by_handle 成功\n");
        show_hooked_functions(plthook);
        dlclose(handle);
        
    } else if (strcmp(mode, "address") == 0) {
        printf("测试 plthook_open_by_address...\n");
        void *handle = dlopen("./libtest.so", RTLD_LAZY);
        if (!handle) {
            printf("无法加载 libtest.so: %s\n", dlerror());
            return 1;
        }
        
        void *symbol = dlsym(handle, "libtest_strcmp");
        if (!symbol) {
            printf("无法找到符号: %s\n", dlerror());
            dlclose(handle);
            return 1;
        }
        
        ret = plthook_open_by_address(&plthook, symbol);
        if (ret != 0) {
            printf("plthook_open_by_address 失败: %s\n", plthook_error());
            dlclose(handle);
            return 1;
        }
        printf("✓ plthook_open_by_address 成功\n");
        show_hooked_functions(plthook);
        dlclose(handle);
        
    } else {
        printf("未知模式: %s\n", mode);
        return 1;
    }
    
    if (plthook) {
        plthook_close(plthook);
    }
    
    printf("✓ 测试完成\n");
    return 0;
}
