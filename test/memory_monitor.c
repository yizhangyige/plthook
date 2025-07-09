#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <signal.h>
#include <stdint.h>
#include <plthook.h>

#ifdef _WIN32
#include <windows.h>
#include <psapi.h>
#define sleep(x) Sleep((x) * 1000)
#else
#include <unistd.h>
#include <dlfcn.h>
#include <sys/resource.h>
#endif

// 内存统计结构
typedef struct {
    size_t total_malloc_calls;
    size_t total_free_calls;
    size_t total_allocated_bytes;
    size_t total_freed_bytes;
    size_t current_allocated_bytes;
    size_t peak_allocated_bytes;
    size_t active_blocks;
} memory_stats_t;

// 内存块跟踪结构
typedef struct memory_block {
    void *ptr;
    size_t size;
    time_t alloc_time;
    struct memory_block *next;
} memory_block_t;

// 全局变量
static memory_stats_t g_stats = {0};
static memory_block_t *g_block_list = NULL;
static int g_monitoring_enabled = 1;
static int g_detailed_logging = 0;

// 原始函数指针
static void* (*original_malloc)(size_t size) = NULL;
static void (*original_free)(void *ptr) = NULL;
static void* (*original_realloc)(void *ptr, size_t size) = NULL;
static void* (*original_calloc)(size_t nmemb, size_t size) = NULL;

// 互斥保护（简单的重入保护）
static volatile int g_in_hook = 0;

// 添加内存块到跟踪列表
static void add_memory_block(void *ptr, size_t size) {
    if (!ptr || g_in_hook) return;
    
    g_in_hook = 1;
    
    memory_block_t *block = (memory_block_t*)original_malloc(sizeof(memory_block_t));
    if (block) {
        block->ptr = ptr;
        block->size = size;
        block->alloc_time = time(NULL);
        block->next = g_block_list;
        g_block_list = block;
        
        g_stats.active_blocks++;
        g_stats.current_allocated_bytes += size;
        if (g_stats.current_allocated_bytes > g_stats.peak_allocated_bytes) {
            g_stats.peak_allocated_bytes = g_stats.current_allocated_bytes;
        }
    }
    
    g_in_hook = 0;
}

// 从跟踪列表中移除内存块
static size_t remove_memory_block(void *ptr) {
    if (!ptr || g_in_hook) return 0;
    
    g_in_hook = 1;
    
    memory_block_t **current = &g_block_list;
    size_t freed_size = 0;
    
    while (*current) {
        if ((*current)->ptr == ptr) {
            memory_block_t *to_remove = *current;
            freed_size = to_remove->size;
            *current = to_remove->next;
            
            g_stats.active_blocks--;
            g_stats.current_allocated_bytes -= freed_size;
            
            original_free(to_remove);
            break;
        }
        current = &(*current)->next;
    }
    
    g_in_hook = 0;
    return freed_size;
}

// malloc 钩子函数
static void* hook_malloc(size_t size) {
    if (!g_monitoring_enabled || g_in_hook) {
        return original_malloc(size);
    }
    
    void *result = original_malloc(size);
    
    if (result) {
        g_stats.total_malloc_calls++;
        g_stats.total_allocated_bytes += size;
        
        add_memory_block(result, size);
        
        if (g_detailed_logging) {
            printf("[MALLOC] %zu bytes allocated at %p\n", size, result);
        }
    }
    
    return result;
}

// free 钩子函数
static void hook_free(void *ptr) {
    if (!ptr) {
        original_free(ptr);
        return;
    }
    
    if (g_monitoring_enabled && !g_in_hook) {
        size_t freed_size = remove_memory_block(ptr);
        g_stats.total_free_calls++;
        g_stats.total_freed_bytes += freed_size;
        
        if (g_detailed_logging && freed_size > 0) {
            printf("[FREE] %zu bytes freed from %p\n", freed_size, ptr);
        }
    }
    
    original_free(ptr);
}

// realloc 钩子函数
static void* hook_realloc(void *ptr, size_t size) {
    if (!g_monitoring_enabled || g_in_hook) {
        return original_realloc(ptr, size);
    }
    
    size_t old_size = 0;
    if (ptr) {
        old_size = remove_memory_block(ptr);
    }
    
    void *result = original_realloc(ptr, size);
    
    if (result && size > 0) {
        add_memory_block(result, size);
        
        if (g_detailed_logging) {
            printf("[REALLOC] %p (%zu bytes) -> %p (%zu bytes)\n", 
                   ptr, old_size, result, size);
        }
    }
    
    return result;
}

// calloc 钩子函数
static void* hook_calloc(size_t nmemb, size_t size) {
    if (!g_monitoring_enabled || g_in_hook) {
        return original_calloc(nmemb, size);
    }
    
    void *result = original_calloc(nmemb, size);
    size_t total_size = nmemb * size;
    
    if (result) {
        g_stats.total_malloc_calls++; // calloc 计入 malloc 统计
        g_stats.total_allocated_bytes += total_size;
        
        add_memory_block(result, total_size);
        
        if (g_detailed_logging) {
            printf("[CALLOC] %zu bytes allocated at %p\n", total_size, result);
        }
    }
    
    return result;
}

// 获取系统内存信息
static void get_system_memory_info(size_t *total_mem, size_t *free_mem, size_t *process_mem) {
#ifdef _WIN32
    // Windows 系统内存信息
    MEMORYSTATUSEX statex;
    statex.dwLength = sizeof(statex);
    if (GlobalMemoryStatusEx(&statex)) {
        *total_mem = (size_t)statex.ullTotalPhys;
        *free_mem = (size_t)statex.ullAvailPhys;
    }
    
    // 进程内存信息
    PROCESS_MEMORY_COUNTERS pmc;
    if (GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc))) {
        *process_mem = pmc.WorkingSetSize;
    }
#else
    // Linux/Unix 系统内存信息
    FILE *meminfo = fopen("/proc/meminfo", "r");
    if (meminfo) {
        char line[256];
        while (fgets(line, sizeof(line), meminfo)) {
            if (strncmp(line, "MemTotal:", 9) == 0) {
                sscanf(line, "MemTotal: %zu kB", total_mem);
                *total_mem *= 1024;
            } else if (strncmp(line, "MemAvailable:", 13) == 0) {
                sscanf(line, "MemAvailable: %zu kB", free_mem);
                *free_mem *= 1024;
            }
        }
        fclose(meminfo);
    }
    
    // 进程内存信息
    struct rusage usage;
    if (getrusage(RUSAGE_SELF, &usage) == 0) {
        *process_mem = usage.ru_maxrss * 1024; // Linux 返回 KB
    }
#endif
}

// 格式化字节数显示
static void format_bytes(size_t bytes, char *buffer, size_t buffer_size) {
    const char *units[] = {"B", "KB", "MB", "GB"};
    double size = (double)bytes;
    int unit = 0;
    
    while (size >= 1024.0 && unit < 3) {
        size /= 1024.0;
        unit++;
    }
    
    if (unit == 0) {
        snprintf(buffer, buffer_size, "%zu %s", bytes, units[unit]);
    } else {
        snprintf(buffer, buffer_size, "%.2f %s", size, units[unit]);
    }
}

// 打印内存统计信息
static void print_memory_stats() {
    char allocated_str[64], freed_str[64], current_str[64], peak_str[64];
    char total_mem_str[64], free_mem_str[64], process_mem_str[64];
    
    format_bytes(g_stats.total_allocated_bytes, allocated_str, sizeof(allocated_str));
    format_bytes(g_stats.total_freed_bytes, freed_str, sizeof(freed_str));
    format_bytes(g_stats.current_allocated_bytes, current_str, sizeof(current_str));
    format_bytes(g_stats.peak_allocated_bytes, peak_str, sizeof(peak_str));
    
    size_t total_mem = 0, free_mem = 0, process_mem = 0;
    get_system_memory_info(&total_mem, &free_mem, &process_mem);
    
    format_bytes(total_mem, total_mem_str, sizeof(total_mem_str));
    format_bytes(free_mem, free_mem_str, sizeof(free_mem_str));
    format_bytes(process_mem, process_mem_str, sizeof(process_mem_str));
    
    time_t now = time(NULL);
    char time_str[64];
    strftime(time_str, sizeof(time_str), "%Y-%m-%d %H:%M:%S", localtime(&now));
    
    printf("\n==================== Memory Monitor Report [%s] ====================\n", time_str);
    printf("Memory Statistics:\n");
    printf("  * malloc calls:       %zu\n", g_stats.total_malloc_calls);
    printf("  * free calls:         %zu\n", g_stats.total_free_calls);
    printf("  * total allocated:    %s\n", allocated_str);
    printf("  * total freed:        %s\n", freed_str);
    printf("  * current usage:      %s\n", current_str);
    printf("  * peak usage:         %s\n", peak_str);
    printf("  * active blocks:      %zu\n", g_stats.active_blocks);
    
    printf("\nSystem Memory Info:\n");
    printf("  * total memory:       %s\n", total_mem_str);
    printf("  * available memory:   %s\n", free_mem_str);
    printf("  * process memory:     %s\n", process_mem_str);
    
    // 计算内存使用效率
    if (g_stats.total_malloc_calls > 0) {
        double avg_alloc = (double)g_stats.total_allocated_bytes / g_stats.total_malloc_calls;
        double leak_ratio = 0.0;
        if (g_stats.total_allocated_bytes > 0) {
            leak_ratio = (double)(g_stats.total_allocated_bytes - g_stats.total_freed_bytes) * 100.0 / g_stats.total_allocated_bytes;
        }
        
        printf("\nMemory Usage Analysis:\n");
        printf("  * average alloc size: %.2f bytes\n", avg_alloc);
        printf("  * memory leak ratio:  %.2f%%\n", leak_ratio);
        printf("  * fragmentation:      %zu active blocks\n", g_stats.active_blocks);
    }
    
    printf("================================================================\n\n");
}

// Signal handler
static void signal_handler(int sig) {
    printf("\nReceived signal %d, printing final statistics...\n", sig);
    print_memory_stats();
    exit(0);
}

// Simulate memory allocation testing
static void simulate_memory_operations() {
    printf("Starting memory allocation simulation...\n\n");
    
    // Test 1: Basic allocation and deallocation
    printf("Test 1: Basic memory allocation\n");
    void *ptrs[10];
    for (int i = 0; i < 10; i++) {
        ptrs[i] = malloc(1024 * (i + 1));
    }
    
    for (int i = 0; i < 5; i++) {
        free(ptrs[i]);
        ptrs[i] = NULL;
    }
    
    sleep(2);
    
    // Test 2: Large block allocation
    printf("Test 2: Large block allocation\n");
    void *big_block = malloc(1024 * 1024); // 1MB
    
    sleep(2);
    
    // Test 3: realloc test
    printf("Test 3: realloc test\n");
    void *realloc_ptr = malloc(1024);
    realloc_ptr = realloc(realloc_ptr, 2048);
    realloc_ptr = realloc(realloc_ptr, 512);
    
    sleep(2);
    
    // Test 4: calloc test
    printf("Test 4: calloc test\n");
    void *calloc_ptr = calloc(100, sizeof(int));
    
    sleep(2);
    
    // Cleanup remaining memory
    printf("Cleaning up remaining memory...\n");
    for (int i = 5; i < 10; i++) {
        if (ptrs[i]) free(ptrs[i]);
    }
    free(big_block);
    free(realloc_ptr);
    free(calloc_ptr);
    
    printf("Memory test completed\n\n");
}

// Install memory hooks
static int install_memory_hooks() {
    plthook_t *plthook;
    int ret;
    
    printf("Installing memory monitoring hooks...\n");
    
    // Open current process
    ret = plthook_open(&plthook, NULL);
    if (ret != 0) {
        printf("plthook_open failed: %s\n", plthook_error());
        return -1;
    }
    
    // Hook malloc
    ret = plthook_replace(plthook, "malloc", (void*)hook_malloc, (void**)&original_malloc);
    if (ret != 0) {
        printf("malloc hook failed: %s\n", plthook_error());
    }
    
    // Hook free
    ret = plthook_replace(plthook, "free", (void*)hook_free, (void**)&original_free);
    if (ret != 0) {
        printf("free hook failed: %s\n", plthook_error());
    }
    
    // Hook realloc
    ret = plthook_replace(plthook, "realloc", (void*)hook_realloc, (void**)&original_realloc);
    if (ret != 0) {
        printf("realloc hook failed: %s\n", plthook_error());
    }
    
    // Hook calloc
    ret = plthook_replace(plthook, "calloc", (void*)hook_calloc, (void**)&original_calloc);
    if (ret != 0) {
        printf("calloc hook failed: %s\n", plthook_error());
    }
    
#ifndef _WIN32
    // Get original function addresses on Unix systems
    if (!original_malloc) original_malloc = dlsym(RTLD_DEFAULT, "malloc");
    if (!original_free) original_free = dlsym(RTLD_DEFAULT, "free");
    if (!original_realloc) original_realloc = dlsym(RTLD_DEFAULT, "realloc");
    if (!original_calloc) original_calloc = dlsym(RTLD_DEFAULT, "calloc");
#endif
    
    plthook_close(plthook);
    
    printf("Memory monitoring hooks installed successfully\n\n");
    return 0;
}

// 显示帮助信息
static void show_usage(const char *program_name) {
    printf("PLTHook Memory Monitor Test Program\n");
    printf("===================================\n\n");
    printf("Usage: %s [options]\n\n", program_name);
    printf("Options:\n");
    printf("  -i, --interval SECONDS  Set monitoring output interval (default: 5 seconds)\n");
    printf("  -d, --detailed          Enable detailed logging (output every malloc/free)\n");
    printf("  -t, --test              Run simulation test\n");
    printf("  -r, --runtime SECONDS   Runtime duration (default: infinite)\n");
    printf("  -h, --help              Show this help information\n\n");
    printf("Examples:\n");
    printf("  %s -i 10 -d             Output every 10 seconds, enable detailed logs\n", program_name);
    printf("  %s -t -r 60             Run test, exit after 60 seconds\n", program_name);
    printf("  %s                      Continuous monitoring, output every 5 seconds\n", program_name);
}

int main(int argc, char *argv[]) {
    int interval = 5;
    int runtime = 0;
    int run_test = 0;
    
    // 解析命令行参数
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-i") == 0 || strcmp(argv[i], "--interval") == 0) {
            if (i + 1 < argc) {
                interval = atoi(argv[++i]);
                if (interval <= 0) interval = 5;
            }
        } else if (strcmp(argv[i], "-d") == 0 || strcmp(argv[i], "--detailed") == 0) {
            g_detailed_logging = 1;
        } else if (strcmp(argv[i], "-t") == 0 || strcmp(argv[i], "--test") == 0) {
            run_test = 1;
        } else if (strcmp(argv[i], "-r") == 0 || strcmp(argv[i], "--runtime") == 0) {
            if (i + 1 < argc) {
                runtime = atoi(argv[++i]);
            }
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            show_usage(argv[0]);
            return 0;
        }
    }
    
    printf("PLTHook Memory Monitor Test Program Started\n");
    printf("==========================================\n");
    printf("Configuration:\n");
    printf("  * Monitor interval: %d seconds\n", interval);
    printf("  * Detailed logging: %s\n", g_detailed_logging ? "enabled" : "disabled");
    printf("  * Run test: %s\n", run_test ? "yes" : "no");
    printf("  * Runtime: %s\n", runtime > 0 ? "limited" : "infinite");
    printf("==========================================\n\n");
    
    // 安装信号处理器
    signal(SIGINT, signal_handler);
#ifndef _WIN32
    signal(SIGTERM, signal_handler);
#endif
    
    // 安装内存钩子
    if (install_memory_hooks() != 0) {
        return 1;
    }
    
    // 运行模拟测试
    if (run_test) {
        simulate_memory_operations();
    }
    
    // 主监控循环
    time_t start_time = time(NULL);
    while (1) {
        print_memory_stats();
        
        // Check runtime duration
        if (runtime > 0 && (time(NULL) - start_time) >= runtime) {
            printf("Reached specified runtime duration, exiting monitor\n");
            break;
        }
        
        sleep(interval);
    }
    
    printf("Memory monitoring ended\n");
    return 0;
}
