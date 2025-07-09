// Android 多线程内存监控测试程序
// 包含监测线程、内存申请线程、内存释放线程
// 使用 PLTHook 监控内存操作
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <signal.h>
#include <time.h>
#include <sys/time.h>
#include <errno.h>
#include <plthook.h>
#include <dlfcn.h>

#ifdef __ANDROID__
#include <android/log.h>
#define LOG_TAG "MemoryTest"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)
#else
#define LOGI printf
#define LOGE printf
#endif

// 全局配置
#define MAX_MEMORY_BLOCKS 1000
#define MIN_BLOCK_SIZE 1024
#define MAX_BLOCK_SIZE (1024 * 1024)  // 1MB
#define MONITOR_INTERVAL_MS 2000      // 2秒
#define ALLOC_INTERVAL_MS 500         // 0.5秒
#define FREE_INTERVAL_MS 1000         // 1秒

// 内存操作类型和统计
typedef enum {
    MEM_MALLOC = 0,
    MEM_FREE,
    MEM_REALLOC,
    MEM_CALLOC,
    MEM_OPERATION_COUNT
} memory_operation_type_t;

const char* memory_operation_names[] = {
    "malloc",
    "free", 
    "realloc",
    "calloc"
};

// 内存操作统计
typedef struct {
    size_t count;
    size_t total_size;
} memory_operation_stats_t;

// 原始函数指针
static void* (*original_malloc)(size_t size) = NULL;
static void (*original_free)(void *ptr) = NULL;
static void* (*original_realloc)(void *ptr, size_t size) = NULL;
static void* (*original_calloc)(size_t nmemb, size_t size) = NULL;

// 前向声明
static void add_memory_block(void *ptr, size_t size, memory_operation_type_t type);
static int remove_memory_block(void *ptr, memory_operation_type_t free_type);

// 内存块管理结构
typedef struct memory_block {
    void *ptr;
    size_t size;
    time_t alloc_time;
    memory_operation_type_t alloc_type;
    struct memory_block *next;
} memory_block_t;

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
    .allocated_blocks = NULL,
    .total_allocated = 0,
    .total_freed = 0,
    .current_usage = 0,
    .peak_usage = 0,
    .active_blocks = 0,
    .should_exit = 0,
    .monitor_thread = 0,
    .alloc_thread = 0,
    .free_thread = 0,
    .alloc_stats = {{0}},
    .free_stats = {{0}},
    .plthook = NULL,
    .hooks_installed = 0
};

// 时间工具函数
static long long get_timestamp_ms() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
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
    static char *stack_start = NULL;
    
    if (stack_start == NULL) {
        stack_start = &stack_var;
    }
    
    return (size_t)labs(&stack_var - stack_start);
}

// 内存钩子函数
static void* hooked_malloc(size_t size) {
    void *ptr = original_malloc(size);
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
    original_free(ptr);
}

static void* hooked_realloc(void *ptr, size_t size) {
    // 如果 ptr 不为 NULL，先移除旧的记录
    if (ptr && g_state.hooks_installed) {
        remove_memory_block(ptr, MEM_FREE);
    }
    
    void *new_ptr = original_realloc(ptr, size);
    
    if (new_ptr && size > 0 && g_state.hooks_installed) {
        add_memory_block(new_ptr, size, MEM_REALLOC);
        printf("[钩子] realloc(%p, %zu) = %p\n", ptr, size, new_ptr);
    }
    
    return new_ptr;
}

static void* hooked_calloc(size_t nmemb, size_t size) {
    void *ptr = original_calloc(nmemb, size);
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
    original_malloc = dlsym(RTLD_NEXT, "malloc");
    original_free = dlsym(RTLD_NEXT, "free");
    original_realloc = dlsym(RTLD_NEXT, "realloc");
    original_calloc = dlsym(RTLD_NEXT, "calloc");
    
    if (!original_malloc || !original_free || !original_realloc || !original_calloc) {
        LOGE("获取原始函数指针失败");
        return -1;
    }
    
    // 打开 PLT 钩子
    if (plthook_open(&g_state.plthook, NULL) != 0) {
        LOGE("plthook_open 失败: %s", plthook_error());
        return -1;
    }
    
    // 安装钩子
    if (plthook_replace(g_state.plthook, "malloc", (void*)hooked_malloc, NULL) != 0) {
        LOGE("无法钩住 malloc: %s", plthook_error());
    }
    
    if (plthook_replace(g_state.plthook, "free", (void*)hooked_free, NULL) != 0) {
        LOGE("无法钩住 free: %s", plthook_error());
    }
    
    if (plthook_replace(g_state.plthook, "realloc", (void*)hooked_realloc, NULL) != 0) {
        LOGE("无法钩住 realloc: %s", plthook_error());
    }
    
    if (plthook_replace(g_state.plthook, "calloc", (void*)hooked_calloc, NULL) != 0) {
        LOGE("无法钩住 calloc: %s", plthook_error());
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
        g_state.plthook = NULL;
        printf("内存钩子已卸载\n");
    }
}

// 添加内存块到链表
static void add_memory_block(void *ptr, size_t size, memory_operation_type_t type) {
    memory_block_t *block = original_malloc ? original_malloc(sizeof(memory_block_t)) : malloc(sizeof(memory_block_t));
    if (!block) return;
    
    block->ptr = ptr;
    block->size = size;
    block->alloc_time = time(NULL);
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
static int remove_memory_block(void *ptr, memory_operation_type_t free_type) {
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
            
            if (original_free) {
                original_free(to_remove);
            } else {
                free(to_remove);
            }
            pthread_mutex_unlock(&g_state.mutex);
            return 1;
        }
        current = &(*current)->next;
    }
    
    pthread_mutex_unlock(&g_state.mutex);
    return 0;
}

// 获取随机的已分配内存块
static void* get_random_allocated_block() {
    pthread_mutex_lock(&g_state.mutex);
    
    if (!g_state.allocated_blocks || g_state.active_blocks == 0) {
        pthread_mutex_unlock(&g_state.mutex);
        return NULL;
    }
    
    int target_index = rand() % g_state.active_blocks;
    memory_block_t *current = g_state.allocated_blocks;
    
    for (int i = 0; i < target_index && current; i++) {
        current = current->next;
    }
    
    void *ptr = current ? current->ptr : NULL;
    pthread_mutex_unlock(&g_state.mutex);
    return ptr;
}

// 测试不同的内存分配方式
static void* test_memory_allocation(size_t size, memory_operation_type_t *alloc_type) {
    void *ptr = NULL;
    int operation = rand() % 4; // 支持4种分配方式
    
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
            
        case 2: // realloc from existing block
            {
                void *existing = get_random_allocated_block();
                if (existing) {
                    ptr = realloc(existing, size);
                    *alloc_type = MEM_REALLOC;
                    if (ptr && ptr != existing) {
                        // 新地址，需要更新记录
                        remove_memory_block(existing, MEM_FREE);
                    }
                } else {
                    // 没有现有块，使用 malloc
                    ptr = malloc(size);
                    *alloc_type = MEM_MALLOC;
                }
                if (ptr) memset(ptr, rand() % 256, size);
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

// 内存监测线程
static void* monitor_thread_func(void *arg) {
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
            
            // 同时输出到 Android 日志
            LOGI("堆内存: %.2fKB (%d块), 峰值: %.2fKB, RSS: %.2fMB", 
                 g_state.current_usage / 1024.0, g_state.active_blocks,
                 g_state.peak_usage / 1024.0, rss / (1024.0 * 1024.0));
        }
        
        sleep_ms(MONITOR_INTERVAL_MS);
    }
    
    LOGI("内存监测线程退出\n");
    return NULL;
}

// 内存申请线程
static void* alloc_thread_func(void *arg) {
    LOGI("内存申请线程启动\n");
    
    while (!g_state.should_exit) {
        // 检查是否已达到最大内存块数量
        pthread_mutex_lock(&g_state.mutex);
        int current_blocks = g_state.active_blocks;
        pthread_mutex_unlock(&g_state.mutex);
        
        if (current_blocks < MAX_MEMORY_BLOCKS) {
            // 随机大小的内存块
            size_t size = MIN_BLOCK_SIZE + (rand() % (MAX_BLOCK_SIZE - MIN_BLOCK_SIZE));
            memory_operation_type_t alloc_type;
            
            void *ptr = test_memory_allocation(size, &alloc_type);
            
            if (ptr) {
                // 注意：如果启用了钩子，内存块会在钩子函数中自动添加
                if (!g_state.hooks_installed) {
                    add_memory_block(ptr, size, alloc_type);
                }
                printf("[申请] %s 分配 %zu 字节内存 @ %p\n", 
                       memory_operation_names[alloc_type], size, ptr);
            } else {
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
    return NULL;
}

// 内存释放线程
static void* free_thread_func(void *arg) {
    LOGI("内存释放线程启动\n");
    
    while (!g_state.should_exit) {
        void *ptr = get_random_allocated_block();
        
        if (ptr) {
            printf("[释放] 释放内存 @ %p\n", ptr);
            
            // 注意：如果启用了钩子，内存块会在钩子函数中自动移除
            if (!g_state.hooks_installed) {
                remove_memory_block(ptr, MEM_FREE);
            }
            free(ptr);
        } else {
            printf("[释放] 没有可释放的内存块\n");
        }
        
        sleep_ms(FREE_INTERVAL_MS);
    }
    
    LOGI("内存释放线程退出\n");
    return NULL;
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
        
        // 使用原始的 free 函数避免递归调用钩子
        if (original_free) {
            original_free(current->ptr);
        } else {
            free(current->ptr);
        }
        
        freed_size += current->size;
        freed_count++;
        
        if (original_free) {
            original_free(current);
        } else {
            free(current);
        }
        
        current = next;
    }
    
    g_state.allocated_blocks = NULL;
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
    printf("Android 多线程内存监控测试程序 - 增强版\n");
    printf("======================================\n");
    printf("用法: %s [选项]\n", program_name);
    printf("选项:\n");
    printf("  -t, --time SECONDS    运行时间（秒），默认为无限\n");
    printf("  -m, --monitor MS      监控间隔（毫秒），默认 2000\n");
    printf("  -a, --alloc MS        分配间隔（毫秒），默认 500\n");
    printf("  -f, --free MS         释放间隔（毫秒），默认 1000\n");
    printf("  -b, --blocks NUM      最大内存块数量，默认 1000\n");
    printf("  --no-hooks            禁用内存钩子\n");
    printf("  -h, --help            显示此帮助信息\n");
    printf("\n");
    printf("支持的内存操作:\n");
    printf("  malloc/free           标准 C 内存分配\n");
    printf("  calloc               清零的内存分配\n");
    printf("  realloc              重新分配内存大小\n");
    printf("\n");
    printf("功能说明:\n");
    printf("  监测线程: 定期报告堆内存和系统内存使用情况\n");
    printf("  申请线程: 使用多种方式持续分配随机大小的内存块\n");
    printf("  释放线程: 随机释放已分配的内存块\n");
    printf("  内存钩子: 使用 PLTHook 监控所有内存分配和释放\n");
    printf("  程序结束时会自动清理所有内存防止泄漏\n");
    printf("  分别统计每种内存操作的使用情况\n");
}

int main(int argc, char *argv[]) {
    int runtime_seconds = 0; // 0 表示无限运行
    int enable_hooks = 1;    // 默认启用钩子
    
    printf("Android 多线程内存监控测试程序 - 增强版\n");
    printf("=====================================\n");
    
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
        // 其他参数可以根据需要添加
    }
    
    // 设置信号处理
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    // 初始化随机数种子
    srand(time(NULL));
    
    printf("配置:\n");
    printf("  运行时间: %s\n", runtime_seconds > 0 ? "有限" : "无限");
    printf("  监控间隔: %d 毫秒\n", MONITOR_INTERVAL_MS);
    printf("  分配间隔: %d 毫秒\n", ALLOC_INTERVAL_MS);
    printf("  释放间隔: %d 毫秒\n", FREE_INTERVAL_MS);
    printf("  最大内存块: %d\n", MAX_MEMORY_BLOCKS);
    printf("  内存钩子: %s\n", enable_hooks ? "启用" : "禁用");
    printf("  支持的内存操作: malloc, calloc, realloc\n");
    printf("\n");
    
    // 安装内存钩子
    if (enable_hooks) {
        if (install_memory_hooks() != 0) {
            printf("警告: 内存钩子安装失败，将使用手动监控模式\n");
            enable_hooks = 0;
        }
    }
    
    LOGI("程序启动，开始创建线程...");
    
    // 创建三个线程
    if (pthread_create(&g_state.monitor_thread, NULL, monitor_thread_func, NULL) != 0) {
        LOGE("创建监测线程失败");
        if (enable_hooks) uninstall_memory_hooks();
        return 1;
    }
    
    if (pthread_create(&g_state.alloc_thread, NULL, alloc_thread_func, NULL) != 0) {
        LOGE("创建内存申请线程失败");
        if (enable_hooks) uninstall_memory_hooks();
        return 1;
    }
    
    if (pthread_create(&g_state.free_thread, NULL, free_thread_func, NULL) != 0) {
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
        // 无限运行直到收到信号
        while (!g_state.should_exit) {
            sleep(1);
        }
    }
    
    printf("等待所有线程退出...\n");
    
    // 等待所有线程结束
    pthread_join(g_state.monitor_thread, NULL);
    pthread_join(g_state.alloc_thread, NULL);
    pthread_join(g_state.free_thread, NULL);
    
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
