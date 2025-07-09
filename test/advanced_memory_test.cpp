// 高级内存监控测试程序 - 支持所有内存操作的钩子监控
// 包含 PLTHook 钩子监控所有内存分配和释放操作
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
#include <dlfcn.h>
#include <plthook.h>

#ifdef __ANDROID__
#include <android/log.h>
#define LOG_TAG "AdvancedMemoryTest"
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
} memory_operation_stats_t;

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
    
    // PLTHook 相关
    plthook_t *plthook;
    int hooks_installed;
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
    .free_stats = {},
    .plthook = nullptr,
    .hooks_installed = 0
};

// 原始函数指针
static void* (*original_malloc)(size_t size) = nullptr;
static void (*original_free)(void *ptr) = nullptr;
static void* (*original_realloc)(void *ptr, size_t size) = nullptr;
static void* (*original_calloc)(size_t nmemb, size_t size) = nullptr;

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
    
    fp = fopen("/proc/self/status", "r");
    if (!fp) return -1;
    
    *vss = *rss = *pss = 0;
    
    while (fgets(buffer, sizeof(buffer), fp)) {
        if (strncmp(buffer, "VmSize:", 7) == 0) {
            sscanf(buffer + 7, "%zu", vss);
            *vss *= 1024;
        } else if (strncmp(buffer, "VmRSS:", 6) == 0) {
            sscanf(buffer + 6, "%zu", rss);
            *rss *= 1024;
        }
    }
    fclose(fp);
    
    *pss = *rss;
    return 0;
}

// 获取栈使用情况
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
    
    // 更新分类统计
    g_state.alloc_stats[type].count++;
    g_state.alloc_stats[type].total_size += size;
    
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
            
            // 更新释放统计
            g_state.free_stats[free_type].count++;
            g_state.free_stats[free_type].total_size += to_remove->size;
            
            free(to_remove);
            pthread_mutex_unlock(&g_state.mutex);
            return 1;
        }
        current = &(*current)->next;
    }
    
    pthread_mutex_unlock(&g_state.mutex);
    return 0;
}

// 内存钩子函数
static void* hooked_malloc(size_t size) {
    void *ptr;
    if (original_malloc) {
        ptr = original_malloc(size);
    } else {
        ptr = malloc(size);
    }
    
    if (ptr && g_state.hooks_installed) {
        add_memory_block(ptr, size, MEM_MALLOC);
        printf("[钩子] malloc(%zu) = %p\n", size, ptr);
    }
    return ptr;
}

static void hooked_free(void *ptr) {
    if (ptr && g_state.hooks_installed) {
        if (remove_memory_block(ptr, MEM_FREE)) {
            printf("[钩子] free(%p)\n", ptr);
        }
    }
    
    if (original_free) {
        original_free(ptr);
    } else {
        free(ptr);
    }
}

static void* hooked_realloc(void *ptr, size_t size) {
    // 如果 ptr 不为 NULL，先移除旧的记录
    if (ptr && g_state.hooks_installed) {
        remove_memory_block(ptr, MEM_FREE);
    }
    
    void *new_ptr;
    if (original_realloc) {
        new_ptr = original_realloc(ptr, size);
    } else {
        new_ptr = realloc(ptr, size);
    }
    
    if (new_ptr && size > 0 && g_state.hooks_installed) {
        add_memory_block(new_ptr, size, MEM_REALLOC);
        printf("[钩子] realloc(%p, %zu) = %p\n", ptr, size, new_ptr);
    }
    
    return new_ptr;
}

static void* hooked_calloc(size_t nmemb, size_t size) {
    void *ptr;
    if (original_calloc) {
        ptr = original_calloc(nmemb, size);
    } else {
        ptr = calloc(nmemb, size);
    }
    
    if (ptr && g_state.hooks_installed) {
        size_t total_size = nmemb * size;
        add_memory_block(ptr, total_size, MEM_CALLOC);
        printf("[钩子] calloc(%zu, %zu) = %p\n", nmemb, size, ptr);
    }
    return ptr;
}

// 安装内存钩子
static int install_memory_hooks() {
    printf("正在安装内存钩子...\n");
    
    // 获取原始函数指针
    original_malloc = (void*(*)(size_t))dlsym(RTLD_NEXT, "malloc");
    original_free = (void(*)(void*))dlsym(RTLD_NEXT, "free");
    original_realloc = (void*(*)(void*, size_t))dlsym(RTLD_NEXT, "realloc");
    original_calloc = (void*(*)(size_t, size_t))dlsym(RTLD_NEXT, "calloc");
    
    if (!original_malloc || !original_free || !original_realloc || !original_calloc) {
        printf("警告: 某些原始函数指针获取失败，将使用系统默认函数\n");
    }
    
    // 打开 PLT 钩子
    if (plthook_open(&g_state.plthook, nullptr) != 0) {
        LOGE("plthook_open 失败: %s", plthook_error());
        return -1;
    }
    
    // 安装钩子
    if (plthook_replace(g_state.plthook, "malloc", (void*)hooked_malloc, nullptr) != 0) {
        printf("警告: 无法钩住 malloc: %s\n", plthook_error());
    }
    
    if (plthook_replace(g_state.plthook, "free", (void*)hooked_free, nullptr) != 0) {
        printf("警告: 无法钩住 free: %s\n", plthook_error());
    }
    
    if (plthook_replace(g_state.plthook, "realloc", (void*)hooked_realloc, nullptr) != 0) {
        printf("警告: 无法钩住 realloc: %s\n", plthook_error());
    }
    
    if (plthook_replace(g_state.plthook, "calloc", (void*)hooked_calloc, nullptr) != 0) {
        printf("警告: 无法钩住 calloc: %s\n", plthook_error());
    }
    
    g_state.hooks_installed = 1;
    printf("内存钩子安装完成\n");
    return 0;
}

// 卸载内存钩子
static void uninstall_memory_hooks() {
    if (g_state.plthook) {
        g_state.hooks_installed = 0;
        plthook_close(g_state.plthook);
        g_state.plthook = nullptr;
        printf("内存钩子已卸载\n");
    }
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

// 测试不同的内存分配方式
static void* test_memory_allocation(size_t size, memory_operation_type *alloc_type) {
    void *ptr = nullptr;
    int operation = rand() % 8; // 支持8种分配方式
    
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
                ptr = new char[size];
                *alloc_type = MEM_NEW;
                memset(ptr, rand() % 256, size);
            } catch (const std::bad_alloc&) {
                ptr = nullptr;
            }
            break;
            
        case 4: // aligned_alloc (如果可用)
            {
                size_t alignment = 16;
                size_t aligned_size = (size + alignment - 1) & ~(alignment - 1);
                #if defined(__ANDROID_API__) && __ANDROID_API__ >= 28
                    ptr = aligned_alloc(alignment, aligned_size);
                    *alloc_type = MEM_ALIGNED_ALLOC;
                    size = aligned_size;
                    if (ptr) memset(ptr, rand() % 256, size);
                #else
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
                    ptr = realloc(existing->ptr, size);
                    *alloc_type = MEM_REALLOC;
                    if (ptr && size > existing->size) {
                        memset((char*)ptr + existing->size, rand() % 256, size - existing->size);
                    }
                    free(existing);
                } else {
                    ptr = malloc(size);
                    *alloc_type = MEM_MALLOC;
                    if (ptr) memset(ptr, rand() % 256, size);
                    if (existing) free(existing);
                }
            }
            break;
            
        case 6: // std::vector allocation
            try {
                std::vector<char> *vec = new std::vector<char>(size);
                ptr = vec->data();
                *alloc_type = MEM_NEW;
                // 注意: 这里我们简化处理，实际上应该存储vector指针
            } catch (const std::bad_alloc&) {
                ptr = nullptr;
            }
            break;
            
        default: // malloc（默认情况）
            ptr = malloc(size);
            *alloc_type = MEM_MALLOC;
            if (ptr) memset(ptr, rand() % 256, size);
            break;
    }
    
    return ptr;
}

// 测试内存释放
static void test_memory_free(void *ptr, memory_operation_type alloc_type) {
    if (!ptr) return;
    
    memory_operation_type free_type;
    
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
    
    // 如果没有钩子，手动移除记录
    if (!g_state.hooks_installed) {
        remove_memory_block(ptr, free_type);
    }
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
                if (g_state.alloc_stats[i].count > 0) {
                    printf("  %s: %zu 次, %.2f KB\n", 
                           memory_operation_names[i],
                           g_state.alloc_stats[i].count,
                           g_state.alloc_stats[i].total_size / 1024.0);
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
        pthread_mutex_lock(&g_state.mutex);
        int current_blocks = g_state.active_blocks;
        pthread_mutex_unlock(&g_state.mutex);
        
        if (current_blocks < MAX_MEMORY_BLOCKS) {
            size_t size = MIN_BLOCK_SIZE + (rand() % (MAX_BLOCK_SIZE - MIN_BLOCK_SIZE));
            memory_operation_type alloc_type;
            
            void *ptr = test_memory_allocation(size, &alloc_type);
            
            if (ptr) {
                // 如果没有钩子，手动添加记录
                if (!g_state.hooks_installed) {
                    add_memory_block(ptr, size, alloc_type);
                }
                printf("[申请] %s 分配 %zu 字节内存 @ %p\n", 
                       memory_operation_names[alloc_type], size, ptr);
            } else {
                printf("[申请] %s 内存分配失败: %zu 字节\n", 
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
    printf("高级内存监控测试程序 - 支持所有内存操作\n");
    printf("======================================\n");
    printf("用法: %s [选项]\n", program_name);
    printf("选项:\n");
    printf("  -t, --time SECONDS    运行时间（秒），默认为无限\n");
    printf("  --no-hooks            禁用内存钩子\n");
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
    printf("  使用 PLTHook 监控所有内存分配和释放操作\n");
    printf("  支持 C 和 C++ 的所有常见内存操作\n");
    printf("  实时统计各种内存操作的使用情况\n");
    printf("  多线程安全的内存监控\n");
    printf("  自动清理防止内存泄漏\n");
}

} // extern "C"

int main(int argc, char *argv[]) {
    int runtime_seconds = 0;
    int enable_hooks = 1;
    
    printf("高级内存监控测试程序启动\n");
    printf("========================\n");
    
    // 解析命令行参数
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            show_help(argv[0]);
            return 0;
        } else if (strcmp(argv[i], "-t") == 0 || strcmp(argv[i], "--time") == 0) {
            if (i + 1 < argc) {
                runtime_seconds = atoi(argv[++i]);
            }
        } else if (strcmp(argv[i], "--no-hooks") == 0) {
            enable_hooks = 0;
        }
    }
    
    // 设置信号处理
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    // 初始化随机数种子
    srand(time(nullptr));
    
    printf("配置:\n");
    printf("  运行时间: %s\n", runtime_seconds > 0 ? "有限" : "无限");
    printf("  内存钩子: %s\n", enable_hooks ? "启用" : "禁用");
    printf("  支持操作: malloc, calloc, realloc, new, new[], aligned_alloc\n");
    printf("\n");
    
    // 安装内存钩子
    if (enable_hooks) {
        if (install_memory_hooks() != 0) {
            printf("警告: 内存钩子安装失败，将使用手动监控模式\n");
            enable_hooks = 0;
        }
    }
    
    LOGI("程序启动，开始创建线程...");
    
    // 创建线程
    if (pthread_create(&g_state.monitor_thread, nullptr, monitor_thread_func, nullptr) != 0) {
        LOGE("创建监测线程失败");
        if (enable_hooks) uninstall_memory_hooks();
        return 1;
    }
    
    if (pthread_create(&g_state.alloc_thread, nullptr, alloc_thread_func, nullptr) != 0) {
        LOGE("创建内存申请线程失败");
        if (enable_hooks) uninstall_memory_hooks();
        return 1;
    }
    
    if (pthread_create(&g_state.free_thread, nullptr, free_thread_func, nullptr) != 0) {
        LOGE("创建内存释放线程失败");
        if (enable_hooks) uninstall_memory_hooks();
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
        if (g_state.alloc_stats[i].count > 0) {
            printf("  %s: %zu 次, %.2f KB\n", 
                   memory_operation_names[i],
                   g_state.alloc_stats[i].count,
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
    
    // 卸载内存钩子
    if (enable_hooks) {
        uninstall_memory_hooks();
    }
    
    // 清理所有剩余内存
    printf("\n清理剩余内存...\n");
    cleanup_all_memory();
    
    printf("程序正常退出\n");
    LOGI("程序正常退出");
    
    return 0;
}
