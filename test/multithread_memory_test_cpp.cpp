// Android 多线程内存监控测试程序 - C++ 增强版
// 包含监测线程、内存申请线程、内存释放线程
// 支持 malloc/free、new/delete、realloc/calloc 等所有内存操作
// 版本: 2.0 - 增强版，支持完整的 C++ 内存操作监控
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unistd.h>
#include <pthread.h>
#include <signal.h>
#include <ctime>
#include <sys/time.h>
#include <errno.h>
#include <iostream>
#include <vector>
#include <memory>
#include <new>
#include <stdexcept>
#include <plthook.h>

#ifdef __ANDROID__
#include <android/log.h>
#define LOG_TAG "MemoryTest"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)
#else
#define LOGI printf
#define LOGE printf
#endif

extern "C" {

// 全局配置
#define MAX_MEMORY_BLOCKS 1000
#define MIN_BLOCK_SIZE 1024
#define MAX_BLOCK_SIZE (1024 * 1024)  // 1MB
#define MONITOR_INTERVAL_MS 2000      // 2秒
#define ALLOC_INTERVAL_MS 500         // 0.5秒
#define FREE_INTERVAL_MS 1000         // 1秒

// 内存操作类型
enum memory_operation_type {
    MEM_MALLOC = 0,
    MEM_FREE,
    MEM_REALLOC,
    MEM_CALLOC,
    MEM_NEW,
    MEM_DELETE,
    MEM_NEW_ARRAY,
    MEM_DELETE_ARRAY,
    MEM_ALIGNED_ALLOC,
    MEM_POSIX_MEMALIGN,
    MEM_OPERATION_COUNT
};

const char* memory_operation_names[] = {
    "malloc",
    "free", 
    "realloc",
    "calloc",
    "new",
    "delete",
    "new[]",
    "delete[]",
    "aligned_alloc",
    "posix_memalign"
};

// 内存块管理结构
typedef struct memory_block {
    void *ptr;
    size_t size;
    time_t alloc_time;
    memory_operation_type alloc_type;
    struct memory_block *next;
} memory_block_t;

// 内存操作统计
typedef struct {
    size_t count;
    size_t total_size;
    size_t success_count;
    size_t failure_count;
} memory_operation_stats_t;

// 函数声明
static void update_alloc_stats(memory_operation_type type, size_t size, bool success);
static void update_free_stats(memory_operation_type type, size_t size);

// 全局状态
typedef struct {
    pthread_mutex_t mutex;
    memory_block_t *allocated_blocks;
    size_t total_allocated;
    size_t total_freed;
    size_t current_usage;
    size_t peak_usage;
    int active_blocks;
    int should_exit;
    pthread_t monitor_thread;
    pthread_t alloc_thread;
    pthread_t free_thread;
    
    // 分操作类型的统计
    memory_operation_stats_t alloc_stats[MEM_OPERATION_COUNT];
    memory_operation_stats_t free_stats[MEM_OPERATION_COUNT];
} memory_test_state_t;

static memory_test_state_t g_state = {
    .mutex = PTHREAD_MUTEX_INITIALIZER,
    .allocated_blocks = nullptr,
    .total_allocated = 0,
    .total_freed = 0,
    .current_usage = 0,
    .peak_usage = 0,
    .active_blocks = 0,
    .should_exit = 0,
    .monitor_thread = 0,
    .alloc_thread = 0,
    .free_thread = 0,
    .alloc_stats = {},
    .free_stats = {}
};

// 时间工具函数
static long long get_timestamp_ms() {
    struct timeval tv;
    gettimeofday(&tv, nullptr);
    return (long long)tv.tv_sec * 1000 + tv.tv_usec / 1000;
}

static void sleep_ms(int ms) {
    usleep(ms * 1000);
}

// 获取进程内存信息
static int get_process_memory_info(size_t *vss, size_t *rss, size_t *pss) {
    FILE *fp;
    char buffer[256];
    
    // 从 /proc/self/status 读取内存信息
    fp = fopen("/proc/self/status", "r");
    if (!fp) return -1;
    
    *vss = *rss = *pss = 0;
    
    while (fgets(buffer, sizeof(buffer), fp)) {
        if (strncmp(buffer, "VmSize:", 7) == 0) {
            sscanf(buffer + 7, "%zu", vss);
            *vss *= 1024; // 转换为字节
        } else if (strncmp(buffer, "VmRSS:", 6) == 0) {
            sscanf(buffer + 6, "%zu", rss);
            *rss *= 1024; // 转换为字节
        }
    }
    fclose(fp);
    
    // PSS 需要从 /proc/self/smaps 读取，这里简化处理
    *pss = *rss; // 简化：使用 RSS 作为 PSS 的近似值
    
    return 0;
}

// 获取栈使用情况（近似）
static size_t get_stack_usage() {
    char stack_var;
    static char *stack_start = nullptr;
    
    if (stack_start == nullptr) {
        stack_start = &stack_var;
    }
    
    return (size_t)labs(&stack_var - stack_start);
}

// 添加内存块到链表
static void add_memory_block(void *ptr, size_t size, memory_operation_type type) {
    if (!ptr) return;
    
    memory_block_t *block = (memory_block_t*)malloc(sizeof(memory_block_t));
    if (!block) return;
    
    block->ptr = ptr;
    block->size = size;
    block->alloc_time = time(nullptr);
    block->alloc_type = type;
    
    pthread_mutex_lock(&g_state.mutex);
    block->next = g_state.allocated_blocks;
    g_state.allocated_blocks = block;
    g_state.total_allocated += size;
    g_state.current_usage += size;
    g_state.active_blocks++;
    
    if (g_state.current_usage > g_state.peak_usage) {
        g_state.peak_usage = g_state.current_usage;
    }
    pthread_mutex_unlock(&g_state.mutex);
}

// 从链表中移除内存块
static int remove_memory_block(void *ptr, memory_operation_type free_type) {
    if (!ptr) return 0;
    
    pthread_mutex_lock(&g_state.mutex);
    
    memory_block_t **current = &g_state.allocated_blocks;
    while (*current) {
        if ((*current)->ptr == ptr) {
            memory_block_t *to_remove = *current;
            *current = (*current)->next;
            
            g_state.total_freed += to_remove->size;
            g_state.current_usage -= to_remove->size;
            g_state.active_blocks--;
            
            size_t freed_size = to_remove->size;
            free(to_remove);
            pthread_mutex_unlock(&g_state.mutex);
            
            // 更新释放统计（在mutex外）
            update_free_stats(free_type, freed_size);
            return 1;
        }
        current = &(*current)->next;
    }
    
    pthread_mutex_unlock(&g_state.mutex);
    return 0;
}

// 获取随机的已分配内存块
static memory_block_t* get_random_allocated_block() {
    pthread_mutex_lock(&g_state.mutex);
    
    if (!g_state.allocated_blocks || g_state.active_blocks == 0) {
        pthread_mutex_unlock(&g_state.mutex);
        return nullptr;
    }
    
    int target_index = rand() % g_state.active_blocks;
    memory_block_t *current = g_state.allocated_blocks;
    
    for (int i = 0; i < target_index && current; i++) {
        current = current->next;
    }
    
    memory_block_t *result = nullptr;
    if (current) {
        result = (memory_block_t*)malloc(sizeof(memory_block_t));
        if (result) {
            *result = *current;
        }
    }
    
    pthread_mutex_unlock(&g_state.mutex);
    return result;
}

// 更新内存操作统计
static void update_alloc_stats(memory_operation_type type, size_t size, bool success) {
    pthread_mutex_lock(&g_state.mutex);
    if (success) {
        g_state.alloc_stats[type].success_count++;
        g_state.alloc_stats[type].count++;
        g_state.alloc_stats[type].total_size += size;
    } else {
        g_state.alloc_stats[type].failure_count++;
    }
    pthread_mutex_unlock(&g_state.mutex);
}

static void update_free_stats(memory_operation_type type, size_t size) {
    pthread_mutex_lock(&g_state.mutex);
    g_state.free_stats[type].count++;
    g_state.free_stats[type].success_count++;
    g_state.free_stats[type].total_size += size;
    pthread_mutex_unlock(&g_state.mutex);
}

// 测试不同的内存分配方式
static void* test_memory_allocation(size_t size, memory_operation_type *alloc_type) {
    void *ptr = nullptr;
    int operation = rand() % 6; // 支持6种分配方式
    
    switch (operation) {
        case 0: // malloc
            ptr = malloc(size);
            *alloc_type = MEM_MALLOC;
            if (ptr) memset(ptr, rand() % 256, size);
            break;
            
        case 1: // calloc
            {
                size_t count = (size / sizeof(int)) + 1;
                ptr = calloc(count, sizeof(int));
                *alloc_type = MEM_CALLOC;
                size = count * sizeof(int);
            }
            break;
            
        case 2: // C++ new
            try {
                ptr = new char[size];
                *alloc_type = MEM_NEW_ARRAY;
                memset(ptr, rand() % 256, size);
            } catch (const std::bad_alloc&) {
                ptr = nullptr;
            }
            break;
            
        case 3: // C++ new single object
            try {
                // 为了简化，我们分配一个大对象（char数组）
                ptr = new char[size];
                *alloc_type = MEM_NEW;
                memset(ptr, rand() % 256, size);
            } catch (const std::bad_alloc&) {
                ptr = nullptr;
            }
            break;
            
        case 4: // aligned_alloc (如果可用)
            {
                size_t alignment = 16; // 16字节对齐
                size_t aligned_size = (size + alignment - 1) & ~(alignment - 1);
                #if defined(__ANDROID_API__) && __ANDROID_API__ >= 28
                    ptr = aligned_alloc(alignment, aligned_size);
                    *alloc_type = MEM_ALIGNED_ALLOC;
                    size = aligned_size;
                    if (ptr) memset(ptr, rand() % 256, size);
                #else
                    // fallback to posix_memalign
                    if (posix_memalign(&ptr, alignment, aligned_size) == 0) {
                        *alloc_type = MEM_POSIX_MEMALIGN;
                        size = aligned_size;
                        if (ptr) memset(ptr, rand() % 256, size);
                    } else {
                        ptr = nullptr;
                    }
                #endif
            }
            break;
            
        case 5: // realloc from existing block
            {
                memory_block_t *existing = get_random_allocated_block();
                if (existing && existing->ptr) {
                    // 先从列表中移除原块
                    remove_memory_block(existing->ptr, MEM_FREE);
                    
                    // realloc
                    ptr = realloc(existing->ptr, size);
                    *alloc_type = MEM_REALLOC;
                    if (ptr && size > existing->size) {
                        // 新增的部分填充随机数据
                        memset((char*)ptr + existing->size, rand() % 256, size - existing->size);
                    }
                    free(existing);
                } else {
                    // 没有现有块，使用 malloc
                    ptr = malloc(size);
                    *alloc_type = MEM_MALLOC;
                    if (ptr) memset(ptr, rand() % 256, size);
                    if (existing) free(existing);
                }
            }
            break;
    }
    
    return ptr;
}

// 测试内存释放
static void test_memory_free(void *ptr, memory_operation_type alloc_type) {
    if (!ptr) return;
    
    memory_operation_type free_type;
    
    // 根据分配类型选择对应的释放方式
    switch (alloc_type) {
        case MEM_MALLOC:
        case MEM_CALLOC:
        case MEM_REALLOC:
        case MEM_ALIGNED_ALLOC:
        case MEM_POSIX_MEMALIGN:
            free(ptr);
            free_type = MEM_FREE;
            break;
            
        case MEM_NEW:
            delete (char*)ptr;
            free_type = MEM_DELETE;
            break;
            
        case MEM_NEW_ARRAY:
            delete[] (char*)ptr;
            free_type = MEM_DELETE_ARRAY;
            break;
            
        default:
            free(ptr);
            free_type = MEM_FREE;
            break;
    }
    
    remove_memory_block(ptr, free_type);
}

// 内存监测线程
static void* monitor_thread_func(void *arg) {
    (void)arg;
    LOGI("内存监测线程启动\n");
    
    while (!g_state.should_exit) {
        size_t vss, rss, pss;
        size_t stack_usage = get_stack_usage();
        
        if (get_process_memory_info(&vss, &rss, &pss) == 0) {
            pthread_mutex_lock(&g_state.mutex);
            
            printf("\n========== 内存监测报告 [%lld] ==========\n", get_timestamp_ms());
            printf("堆内存统计:\n");
            printf("  当前分配: %.2f KB (%d 个块)\n", 
                   g_state.current_usage / 1024.0, g_state.active_blocks);
            printf("  峰值使用: %.2f KB\n", g_state.peak_usage / 1024.0);
            printf("  总计分配: %.2f KB\n", g_state.total_allocated / 1024.0);
            printf("  总计释放: %.2f KB\n", g_state.total_freed / 1024.0);
            
            printf("分配操作统计:\n");
            for (int i = 0; i < MEM_OPERATION_COUNT; i++) {
                if (g_state.alloc_stats[i].count > 0 || g_state.alloc_stats[i].failure_count > 0) {
                    printf("  %s: 成功 %zu 次, 失败 %zu 次, %.2f KB (成功率: %.1f%%)\n", 
                           memory_operation_names[i],
                           g_state.alloc_stats[i].success_count,
                           g_state.alloc_stats[i].failure_count,
                           g_state.alloc_stats[i].total_size / 1024.0,
                           g_state.alloc_stats[i].count > 0 ? 
                           (100.0 * g_state.alloc_stats[i].success_count / 
                            (g_state.alloc_stats[i].success_count + g_state.alloc_stats[i].failure_count)) : 0.0);
                }
            }
            
            printf("释放操作统计:\n");
            for (int i = 0; i < MEM_OPERATION_COUNT; i++) {
                if (g_state.free_stats[i].count > 0) {
                    printf("  %s: %zu 次, %.2f KB\n", 
                           memory_operation_names[i],
                           g_state.free_stats[i].count,
                           g_state.free_stats[i].total_size / 1024.0);
                }
            }
            
            printf("系统内存信息:\n");
            printf("  虚拟内存 (VSS): %.2f MB\n", vss / (1024.0 * 1024.0));
            printf("  物理内存 (RSS): %.2f MB\n", rss / (1024.0 * 1024.0));
            printf("  栈使用 (近似): %.2f KB\n", stack_usage / 1024.0);
            printf("=====================================\n");
            
            pthread_mutex_unlock(&g_state.mutex);
            
            // 同时输出到 Android 日志
            LOGI("堆内存: %.2fKB (%d块), 峰值: %.2fKB, RSS: %.2fMB", 
                 g_state.current_usage / 1024.0, g_state.active_blocks,
                 g_state.peak_usage / 1024.0, rss / (1024.0 * 1024.0));
        }
        
        sleep_ms(MONITOR_INTERVAL_MS);
    }
    
    LOGI("内存监测线程退出\n");
    return nullptr;
}

// 内存申请线程
static void* alloc_thread_func(void *arg) {
    (void)arg;
    LOGI("内存申请线程启动\n");
    
    while (!g_state.should_exit) {
        // 检查是否已达到最大内存块数量
        pthread_mutex_lock(&g_state.mutex);
        int current_blocks = g_state.active_blocks;
        pthread_mutex_unlock(&g_state.mutex);
        
        if (current_blocks < MAX_MEMORY_BLOCKS) {
            // 随机大小的内存块
            size_t size = MIN_BLOCK_SIZE + (rand() % (MAX_BLOCK_SIZE - MIN_BLOCK_SIZE));
            memory_operation_type alloc_type;
            
            void *ptr = test_memory_allocation(size, &alloc_type);
            
            if (ptr) {
                add_memory_block(ptr, size, alloc_type);
                update_alloc_stats(alloc_type, size, true);
                printf("[申请] %s 分配 %zu 字节内存 @ %p\n", 
                       memory_operation_names[alloc_type], size, ptr);
            } else {
                update_alloc_stats(alloc_type, size, false);
                printf("[申请] %s 内存分配失败: %zu 字节\n", 
                       memory_operation_names[alloc_type], size);
                LOGE("%s 内存分配失败: %zu 字节", 
                     memory_operation_names[alloc_type], size);
            }
        } else {
            printf("[申请] 已达到最大内存块数量 (%d)，跳过分配\n", MAX_MEMORY_BLOCKS);
        }
        
        sleep_ms(ALLOC_INTERVAL_MS);
    }
    
    LOGI("内存申请线程退出\n");
    return nullptr;
}

// 内存释放线程
static void* free_thread_func(void *arg) {
    (void)arg;
    LOGI("内存释放线程启动\n");
    
    while (!g_state.should_exit) {
        memory_block_t *block = get_random_allocated_block();
        
        if (block) {
            printf("[释放] %s 释放内存 @ %p (%zu 字节)\n", 
                   memory_operation_names[block->alloc_type], 
                   block->ptr, block->size);
            
            test_memory_free(block->ptr, block->alloc_type);
            free(block);
        } else {
            printf("[释放] 没有可释放的内存块\n");
        }
        
        sleep_ms(FREE_INTERVAL_MS);
    }
    
    LOGI("内存释放线程退出\n");
    return nullptr;
}

// 信号处理函数
static void signal_handler(int signum) {
    printf("\n收到信号 %d，准备退出...\n", signum);
    g_state.should_exit = 1;
}

// 清理所有分配的内存
static void cleanup_all_memory() {
    pthread_mutex_lock(&g_state.mutex);
    
    memory_block_t *current = g_state.allocated_blocks;
    int freed_count = 0;
    size_t freed_size = 0;
    
    while (current) {
        memory_block_t *next = current->next;
        
        // 根据分配类型使用对应的释放方式
        switch (current->alloc_type) {
            case MEM_MALLOC:
            case MEM_CALLOC:
            case MEM_REALLOC:
            case MEM_ALIGNED_ALLOC:
            case MEM_POSIX_MEMALIGN:
                free(current->ptr);
                break;
                
            case MEM_NEW:
                delete (char*)current->ptr;
                break;
                
            case MEM_NEW_ARRAY:
                delete[] (char*)current->ptr;
                break;
                
            default:
                free(current->ptr);
                break;
        }
        
        freed_size += current->size;
        freed_count++;
        free(current);
        current = next;
    }
    
    g_state.allocated_blocks = nullptr;
    g_state.active_blocks = 0;
    g_state.current_usage = 0;
    
    pthread_mutex_unlock(&g_state.mutex);
    
    printf("清理完成: 释放了 %d 个内存块，总计 %.2f KB\n", 
           freed_count, freed_size / 1024.0);
    LOGI("清理完成: 释放了 %d 个内存块，总计 %.2f KB", 
         freed_count, freed_size / 1024.0);
}

// 显示帮助信息
static void show_help(const char *program_name) {
    printf("Android 多线程内存监控测试程序 - C++ 增强版\n");
    printf("==========================================\n");
    printf("用法: %s [选项]\n", program_name);
    printf("选项:\n");
    printf("  -t, --time SECONDS    运行时间（秒），默认为无限\n");
    printf("  -m, --monitor MS      监控间隔（毫秒），默认 2000\n");
    printf("  -a, --alloc MS        分配间隔（毫秒），默认 500\n");
    printf("  -f, --free MS         释放间隔（毫秒），默认 1000\n");
    printf("  -b, --blocks NUM      最大内存块数量，默认 1000\n");
    printf("  -h, --help            显示此帮助信息\n");
    printf("\n");
    printf("支持的内存操作:\n");
    printf("  malloc/free           标准 C 内存分配\n");
    printf("  calloc               清零的内存分配\n");
    printf("  realloc              重新分配内存大小\n");
    printf("  new/delete           C++ 单对象分配\n");
    printf("  new[]/delete[]       C++ 数组分配\n");
    printf("  aligned_alloc        对齐内存分配\n");
    printf("  posix_memalign       POSIX 对齐分配\n");
    printf("\n");
    printf("功能说明:\n");
    printf("  监测线程: 定期报告堆内存和系统内存使用情况\n");
    printf("  申请线程: 使用多种方式持续分配随机大小的内存块\n");
    printf("  释放线程: 使用对应方式随机释放已分配的内存块\n");
    printf("  程序结束时会自动清理所有内存防止泄漏\n");
    printf("  分别统计每种内存操作的使用情况\n");
}

} // extern "C"

int main(int argc, char *argv[]) {
    int runtime_seconds = 0; // 0 表示无限运行
    
    printf("Android 多线程内存监控测试程序 - C++ 增强版\n");
    printf("==========================================\n");
    
    // 解析命令行参数
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            show_help(argv[0]);
            return 0;
        } else if (strcmp(argv[i], "-t") == 0 || strcmp(argv[i], "--time") == 0) {
            if (i + 1 < argc) {
                runtime_seconds = atoi(argv[++i]);
            }
        }
        // 其他参数可以根据需要添加
    }
    
    // 设置信号处理
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    // 初始化随机数种子
    srand(time(nullptr));
    
    printf("配置:\n");
    printf("  运行时间: %s\n", runtime_seconds > 0 ? "有限" : "无限");
    printf("  监控间隔: %d 毫秒\n", MONITOR_INTERVAL_MS);
    printf("  分配间隔: %d 毫秒\n", ALLOC_INTERVAL_MS);
    printf("  释放间隔: %d 毫秒\n", FREE_INTERVAL_MS);
    printf("  最大内存块: %d\n", MAX_MEMORY_BLOCKS);
    printf("  支持的内存操作: malloc, calloc, realloc, new, new[], aligned_alloc\n");
    printf("\n");
    
    LOGI("程序启动，开始创建线程...");
    
    // 创建三个线程
    if (pthread_create(&g_state.monitor_thread, nullptr, monitor_thread_func, nullptr) != 0) {
        LOGE("创建监测线程失败");
        return 1;
    }
    
    if (pthread_create(&g_state.alloc_thread, nullptr, alloc_thread_func, nullptr) != 0) {
        LOGE("创建内存申请线程失败");
        return 1;
    }
    
    if (pthread_create(&g_state.free_thread, nullptr, free_thread_func, nullptr) != 0) {
        LOGE("创建内存释放线程失败");
        return 1;
    }
    
    printf("所有线程已启动，开始监控...\n");
    LOGI("所有线程已启动");
    
    // 主线程等待
    if (runtime_seconds > 0) {
        sleep(runtime_seconds);
        printf("达到指定运行时间，准备退出...\n");
        g_state.should_exit = 1;
    } else {
        // 无限运行直到收到信号
        while (!g_state.should_exit) {
            sleep(1);
        }
    }
    
    printf("等待所有线程退出...\n");
    
    // 等待所有线程结束
    pthread_join(g_state.monitor_thread, nullptr);
    pthread_join(g_state.alloc_thread, nullptr);
    pthread_join(g_state.free_thread, nullptr);
    
    printf("\n最终统计:\n");
    printf("  总计分配: %.2f KB\n", g_state.total_allocated / 1024.0);
    printf("  总计释放: %.2f KB\n", g_state.total_freed / 1024.0);
    printf("  峰值使用: %.2f KB\n", g_state.peak_usage / 1024.0);
    printf("  剩余块数: %d\n", g_state.active_blocks);
    
    // 显示详细的操作统计
    printf("\n详细操作统计:\n");
    printf("分配操作:\n");
    for (int i = 0; i < MEM_OPERATION_COUNT; i++) {
        if (g_state.alloc_stats[i].count > 0 || g_state.alloc_stats[i].failure_count > 0) {
            printf("  %s: 成功 %zu 次, 失败 %zu 次, %.2f KB\n", 
                   memory_operation_names[i],
                   g_state.alloc_stats[i].success_count,
                   g_state.alloc_stats[i].failure_count,
                   g_state.alloc_stats[i].total_size / 1024.0);
        }
    }
    
    printf("释放操作:\n");
    for (int i = 0; i < MEM_OPERATION_COUNT; i++) {
        if (g_state.free_stats[i].count > 0) {
            printf("  %s: %zu 次, %.2f KB\n", 
                   memory_operation_names[i],
                   g_state.free_stats[i].count,
                   g_state.free_stats[i].total_size / 1024.0);
        }
    }
    
    // 清理所有剩余内存
    printf("\n清理剩余内存...\n");
    cleanup_all_memory();
    
    printf("程序正常退出\n");
    LOGI("程序正常退出");
    
    return 0;
}
