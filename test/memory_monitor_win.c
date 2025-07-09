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
#include <heapapi.h>
#define sleep(x) Sleep((x) * 1000)
#else
#include <unistd.h>
#include <dlfcn.h>
#include <sys/resource.h>
#endif

// 内存统计结构
typedef struct {
    size_t heap_alloc_calls;
    size_t heap_free_calls;
    size_t total_allocated_bytes;
    size_t total_freed_bytes;
    size_t current_allocated_bytes;
    size_t peak_allocated_bytes;
    size_t active_blocks;
} memory_stats_t;

// 全局变量
static memory_stats_t g_stats = {0};
static int g_monitoring_enabled = 1;
static int g_detailed_logging = 0;

#ifdef _WIN32
// Windows 特定的内存监控
static HANDLE g_heap_handle = NULL;

// 原始 HeapAlloc/HeapFree 函数指针
static LPVOID (WINAPI *original_HeapAlloc)(HANDLE hHeap, DWORD dwFlags, SIZE_T dwBytes) = NULL;
static BOOL (WINAPI *original_HeapFree)(HANDLE hHeap, DWORD dwFlags, LPVOID lpMem) = NULL;
static LPVOID (WINAPI *original_HeapReAlloc)(HANDLE hHeap, DWORD dwFlags, LPVOID lpMem, SIZE_T dwBytes) = NULL;

// HeapAlloc 钩子函数
static LPVOID WINAPI hook_HeapAlloc(HANDLE hHeap, DWORD dwFlags, SIZE_T dwBytes) {
    LPVOID result = original_HeapAlloc(hHeap, dwFlags, dwBytes);
    
    if (result && g_monitoring_enabled) {
        g_stats.heap_alloc_calls++;
        g_stats.total_allocated_bytes += dwBytes;
        g_stats.current_allocated_bytes += dwBytes;
        g_stats.active_blocks++;
        
        if (g_stats.current_allocated_bytes > g_stats.peak_allocated_bytes) {
            g_stats.peak_allocated_bytes = g_stats.current_allocated_bytes;
        }
        
        if (g_detailed_logging) {
            printf("[HeapAlloc] %zu bytes allocated at %p\n", dwBytes, result);
        }
    }
    
    return result;
}

// HeapFree 钩子函数
static BOOL WINAPI hook_HeapFree(HANDLE hHeap, DWORD dwFlags, LPVOID lpMem) {
    if (lpMem && g_monitoring_enabled) {
        // 尝试获取内存块大小
        SIZE_T size = HeapSize(hHeap, 0, lpMem);
        if (size != (SIZE_T)-1) {
            g_stats.heap_free_calls++;
            g_stats.total_freed_bytes += size;
            
            // 防止下溢
            if (g_stats.current_allocated_bytes >= size) {
                g_stats.current_allocated_bytes -= size;
            } else {
                g_stats.current_allocated_bytes = 0;
            }
            
            if (g_stats.active_blocks > 0) {
                g_stats.active_blocks--;
            }
            
            if (g_detailed_logging) {
                printf("[HeapFree] %zu bytes freed from %p\n", size, lpMem);
            }
        }
    }
    
    return original_HeapFree(hHeap, dwFlags, lpMem);
}

// HeapReAlloc 钩子函数
static LPVOID WINAPI hook_HeapReAlloc(HANDLE hHeap, DWORD dwFlags, LPVOID lpMem, SIZE_T dwBytes) {
    SIZE_T old_size = 0;
    if (lpMem && g_monitoring_enabled) {
        old_size = HeapSize(hHeap, 0, lpMem);
    }
    
    LPVOID result = original_HeapReAlloc(hHeap, dwFlags, lpMem, dwBytes);
    
    if (result && g_monitoring_enabled) {
        if (old_size != (SIZE_T)-1) {
            // 防止下溢
            if (g_stats.current_allocated_bytes >= old_size) {
                g_stats.current_allocated_bytes -= old_size;
            } else {
                g_stats.current_allocated_bytes = 0;
            }
        }
        g_stats.current_allocated_bytes += dwBytes;
        
        if (g_stats.current_allocated_bytes > g_stats.peak_allocated_bytes) {
            g_stats.peak_allocated_bytes = g_stats.current_allocated_bytes;
        }
        
        if (g_detailed_logging) {
            printf("[HeapReAlloc] %p (%zu bytes) -> %p (%zu bytes)\n", 
                   lpMem, old_size, result, dwBytes);
        }
    }
    
    return result;
}

// 安装 Windows 内存钩子
static int install_windows_memory_hooks() {
    plthook_t *plthook;
    int ret;
    
    printf("Installing Windows memory monitoring hooks...\n");
    
    // 获取进程堆句柄
    g_heap_handle = GetProcessHeap();
    if (!g_heap_handle) {
        printf("Failed to get process heap handle\n");
        return -1;
    }
    
    // 尝试钩取 kernel32.dll
    ret = plthook_open(&plthook, "kernel32.dll");
    if (ret != 0) {
        printf("Failed to open kernel32.dll: %s\n", plthook_error());
        return -1;
    }
    
    // 钩取 HeapAlloc
    ret = plthook_replace(plthook, "HeapAlloc", (void*)hook_HeapAlloc, (void**)&original_HeapAlloc);
    if (ret != 0) {
        printf("HeapAlloc hook failed: %s\n", plthook_error());
    } else {
        printf("HeapAlloc hook installed successfully\n");
    }
    
    // 钩取 HeapFree
    ret = plthook_replace(plthook, "HeapFree", (void*)hook_HeapFree, (void**)&original_HeapFree);
    if (ret != 0) {
        printf("HeapFree hook failed: %s\n", plthook_error());
    } else {
        printf("HeapFree hook installed successfully\n");
    }
    
    // 钩取 HeapReAlloc
    ret = plthook_replace(plthook, "HeapReAlloc", (void*)hook_HeapReAlloc, (void**)&original_HeapReAlloc);
    if (ret != 0) {
        printf("HeapReAlloc hook failed: %s\n", plthook_error());
    } else {
        printf("HeapReAlloc hook installed successfully\n");
    }
    
    plthook_close(plthook);
    return 0;
}

#endif

// 获取系统内存信息
static void get_system_memory_info(size_t *total_mem, size_t *free_mem, size_t *process_mem) {
    *total_mem = 0;
    *free_mem = 0;
    *process_mem = 0;
    
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
    
#ifdef _WIN32
    printf("Windows Heap Statistics:\n");
    printf("  * HeapAlloc calls:    %zu\n", g_stats.heap_alloc_calls);
    printf("  * HeapFree calls:     %zu\n", g_stats.heap_free_calls);
#else
    printf("Memory Statistics:\n");
    printf("  * malloc calls:       %zu\n", g_stats.heap_alloc_calls);
    printf("  * free calls:         %zu\n", g_stats.heap_free_calls);
#endif
    
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
    if (g_stats.heap_alloc_calls > 0) {
        double avg_alloc = (double)g_stats.total_allocated_bytes / g_stats.heap_alloc_calls;
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

// 模拟内存分配测试
static void simulate_memory_operations() {
    printf("Starting memory allocation simulation...\n\n");
    
#ifdef _WIN32
    printf("Test 1: HeapAlloc/HeapFree operations\n");
    HANDLE heap = GetProcessHeap();
    
    // 分配一些内存块
    void *ptrs[10];
    for (int i = 0; i < 10; i++) {
        ptrs[i] = HeapAlloc(heap, 0, 1024 * (i + 1));
        printf("Allocated %d KB at %p\n", i + 1, ptrs[i]);
    }
    
    sleep(2);
    
    // 释放一部分
    printf("Test 2: Freeing some blocks\n");
    for (int i = 0; i < 5; i++) {
        if (ptrs[i]) {
            HeapFree(heap, 0, ptrs[i]);
            printf("Freed block at %p\n", ptrs[i]);
            ptrs[i] = NULL;
        }
    }
    
    sleep(2);
    
    // 重新分配
    printf("Test 3: HeapReAlloc operations\n");
    if (ptrs[5]) {
        void *new_ptr = HeapReAlloc(heap, 0, ptrs[5], 2048);
        printf("Reallocated %p to %p (2 KB)\n", ptrs[5], new_ptr);
        ptrs[5] = new_ptr;
    }
    
    sleep(2);
    
    // 清理剩余内存
    printf("Cleaning up remaining memory...\n");
    for (int i = 5; i < 10; i++) {
        if (ptrs[i]) {
            HeapFree(heap, 0, ptrs[i]);
            printf("Freed block at %p\n", ptrs[i]);
        }
    }
    
#else
    // Unix 版本的测试代码
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
    
    printf("Test 2: Large block allocation\n");
    void *big_block = malloc(1024 * 1024); // 1MB
    
    sleep(2);
    
    printf("Cleaning up remaining memory...\n");
    for (int i = 5; i < 10; i++) {
        if (ptrs[i]) free(ptrs[i]);
    }
    free(big_block);
#endif
    
    printf("Memory test completed\n\n");
}

// 显示帮助信息
static void show_usage(const char *program_name) {
    printf("PLTHook Memory Monitor Test Program\n");
    printf("===================================\n\n");
    printf("Usage: %s [options]\n\n", program_name);
    printf("Options:\n");
    printf("  -i, --interval SECONDS  Set monitoring output interval (default: 5 seconds)\n");
    printf("  -d, --detailed          Enable detailed logging\n");
    printf("  -t, --test              Run simulation test\n");
    printf("  -r, --runtime SECONDS   Runtime duration (default: infinite)\n");
    printf("  -h, --help              Show this help information\n\n");
    printf("Examples:\n");
    printf("  %s -i 10 -d             Output every 10 seconds, enable detailed logs\n", program_name);
    printf("  %s -t -r 60             Run test, exit after 60 seconds\n", program_name);
    printf("  %s                      Continuous monitoring, output every 5 seconds\n", program_name);
}

// 信号处理函数
static void signal_handler(int sig) {
    printf("\nReceived signal %d, printing final statistics...\n", sig);
    print_memory_stats();
    exit(0);
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
    
#ifdef _WIN32
    // 安装 Windows 内存钩子
    if (install_windows_memory_hooks() != 0) {
        printf("Failed to install memory hooks, continuing with basic monitoring...\n");
    }
#else
    // 这里可以添加 Unix 版本的内存钩子安装
    printf("Unix memory monitoring not implemented in this version\n");
#endif
    
    // 运行模拟测试
    if (run_test) {
        simulate_memory_operations();
    }
    
    // 主监控循环
    time_t start_time = time(NULL);
    while (1) {
        print_memory_stats();
        
        // 检查运行时长
        if (runtime > 0 && (time(NULL) - start_time) >= runtime) {
            printf("Reached specified runtime duration, exiting monitor\n");
            break;
        }
        
        sleep(interval);
    }
    
    printf("Memory monitoring ended\n");
    return 0;
}
