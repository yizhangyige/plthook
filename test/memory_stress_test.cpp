// 内存压力测试和边界情况测试程序
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unistd.h>
#include <pthread.h>
#include <signal.h>
#include <ctime>
#include <vector>
#include <new>

#ifdef __ANDROID__
#include <android/log.h>
#define LOG_TAG "MemoryStressTest"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)
#else
#define LOGI printf
#define LOGE printf
#endif

extern "C" {

// 测试配置
#define STRESS_TEST_DURATION 30    // 压力测试持续时间（秒）
#define MAX_ALLOCATION_SIZE (100 * 1024 * 1024)  // 最大分配100MB
#define MIN_ALLOCATION_SIZE 1      // 最小分配1字节

static volatile int should_exit = 0;

// 统计信息
typedef struct {
    size_t successful_allocations;
    size_t failed_allocations;
    size_t successful_frees;
    size_t total_allocated_bytes;
    size_t current_allocated_bytes;
    size_t peak_allocated_bytes;
    pthread_mutex_t mutex;
} stress_test_stats_t;

static stress_test_stats_t stats = {
    .successful_allocations = 0,
    .failed_allocations = 0,
    .successful_frees = 0,
    .total_allocated_bytes = 0,
    .current_allocated_bytes = 0,
    .peak_allocated_bytes = 0,
    .mutex = PTHREAD_MUTEX_INITIALIZER
};

void update_stats(int allocation_success, size_t size, int is_free) {
    pthread_mutex_lock(&stats.mutex);
    
    if (is_free) {
        if (allocation_success) {
            stats.successful_frees++;
            stats.current_allocated_bytes -= size;
        }
    } else {
        if (allocation_success) {
            stats.successful_allocations++;
            stats.total_allocated_bytes += size;
            stats.current_allocated_bytes += size;
            if (stats.current_allocated_bytes > stats.peak_allocated_bytes) {
                stats.peak_allocated_bytes = stats.current_allocated_bytes;
            }
        } else {
            stats.failed_allocations++;
        }
    }
    
    pthread_mutex_unlock(&stats.mutex);
}

void print_stats() {
    pthread_mutex_lock(&stats.mutex);
    
    printf("\n========== 压力测试统计 ==========\n");
    printf("成功分配: %zu 次\n", stats.successful_allocations);
    printf("失败分配: %zu 次\n", stats.failed_allocations);
    printf("成功释放: %zu 次\n", stats.successful_frees);
    printf("总计分配: %.2f MB\n", stats.total_allocated_bytes / (1024.0 * 1024.0));
    printf("当前使用: %.2f MB\n", stats.current_allocated_bytes / (1024.0 * 1024.0));
    printf("峰值使用: %.2f MB\n", stats.peak_allocated_bytes / (1024.0 * 1024.0));
    printf("成功率: %.2f%%\n", 
           stats.successful_allocations * 100.0 / 
           (stats.successful_allocations + stats.failed_allocations));
    printf("===============================\n");
    
    pthread_mutex_unlock(&stats.mutex);
}

// 测试大内存分配
void* test_large_allocations(void* arg) {
    (void)arg;
    printf("开始大内存分配测试...\n");
    
    std::vector<void*> large_blocks;
    
    while (!should_exit) {
        // 分配大块内存 (1MB - 100MB)
        size_t size = 1024 * 1024 + (rand() % (99 * 1024 * 1024));
        
        void* ptr = malloc(size);
        if (ptr) {
            large_blocks.push_back(ptr);
            update_stats(1, size, 0);
            printf("[大内存] 成功分配 %.2f MB @ %p\n", size / (1024.0 * 1024.0), ptr);
            
            // 写入数据测试
            memset(ptr, 0xAA, std::min(size, (size_t)4096));
            
            // 如果积累了太多大块，释放一些
            if (large_blocks.size() > 10) {
                size_t idx = rand() % large_blocks.size();
                void* old_ptr = large_blocks[idx];
                large_blocks.erase(large_blocks.begin() + idx);
                
                free(old_ptr);
                update_stats(1, size, 1);  // 简化统计
                printf("[大内存] 释放大块内存 @ %p\n", old_ptr);
            }
        } else {
            update_stats(0, size, 0);
            printf("[大内存] 分配失败: %.2f MB\n", size / (1024.0 * 1024.0));
        }
        
        sleep(2); // 大内存分配间隔长一些
    }
    
    // 清理所有大块内存
    for (void* ptr : large_blocks) {
        free(ptr);
        update_stats(1, 0, 1);
    }
    
    printf("大内存分配测试结束\n");
    return nullptr;
}

// 测试小内存分配
void* test_small_allocations(void* arg) {
    (void)arg;
    printf("开始小内存分配测试...\n");
    
    std::vector<std::pair<void*, size_t>> small_blocks;
    
    while (!should_exit) {
        // 随机决定分配还是释放
        if ((rand() % 100) < 70 || small_blocks.empty()) {
            // 70% 概率分配，或者没有可释放的块时
            size_t size = 1 + (rand() % 4096); // 1B - 4KB
            
            void* ptr = malloc(size);
            if (ptr) {
                small_blocks.push_back(std::make_pair(ptr, size));
                update_stats(1, size, 0);
                
                // 写入测试数据
                memset(ptr, rand() % 256, size);
                
                if (small_blocks.size() % 1000 == 0) {
                    printf("[小内存] 已分配 %zu 个小块\n", small_blocks.size());
                }
            } else {
                update_stats(0, size, 0);
            }
        } else {
            // 30% 概率释放
            if (!small_blocks.empty()) {
                size_t idx = rand() % small_blocks.size();
                auto block = small_blocks[idx];
                small_blocks.erase(small_blocks.begin() + idx);
                
                free(block.first);
                update_stats(1, block.second, 1);
            }
        }
        
        // 小内存分配频率高
        usleep(1000); // 1ms
    }
    
    // 清理所有小块内存
    for (auto& block : small_blocks) {
        free(block.first);
        update_stats(1, block.second, 1);
    }
    
    printf("小内存分配测试结束，共处理了 %zu 个小块\n", small_blocks.size());
    return nullptr;
}

// 测试C++内存分配
void* test_cpp_allocations(void* arg) {
    (void)arg;
    printf("开始 C++ 内存分配测试...\n");
    
    std::vector<char*> cpp_blocks;
    
    while (!should_exit) {
        try {
            // 随机选择分配方式
            int method = rand() % 4;
            size_t size = 1024 + (rand() % (1024 * 1024)); // 1KB - 1MB
            
            char* ptr = nullptr;
            
            switch (method) {
                case 0: // new
                    ptr = new char[size];
                    break;
                case 1: // new with nothrow
                    ptr = new(std::nothrow) char[size];
                    break;
                case 2: // vector allocation
                    {
                        auto vec = new std::vector<char>(size);
                        ptr = vec->data();
                        // 注意：这里简化了，实际应该保存vector指针
                        delete vec;
                        ptr = nullptr; // 避免重复释放
                    }
                    break;
                case 3: // 模拟智能指针
                    {
                        std::unique_ptr<char[]> smart_ptr(new char[size]);
                        ptr = smart_ptr.get();
                        // 填充数据
                        if (ptr) memset(ptr, 0xBB, std::min(size, (size_t)1024));
                        // smart_ptr自动释放，不需要手动管理
                        ptr = nullptr;
                    }
                    break;
            }
            
            if (ptr) {
                cpp_blocks.push_back(ptr);
                update_stats(1, size, 0);
                
                // 写入测试数据
                memset(ptr, 0xCC, std::min(size, (size_t)1024));
                
                printf("[C++] 分配方法 %d: %.2f KB @ %p\n", 
                       method, size / 1024.0, ptr);
                
                // 限制同时存在的C++块数量
                if (cpp_blocks.size() > 50) {
                    char* old_ptr = cpp_blocks.front();
                    cpp_blocks.erase(cpp_blocks.begin());
                    
                    delete[] old_ptr;
                    update_stats(1, size, 1); // 简化统计
                }
            } else {
                update_stats(0, size, 0);
                printf("[C++] 分配失败: %.2f KB\n", size / 1024.0);
            }
            
        } catch (const std::bad_alloc& e) {
            printf("[C++] 捕获到 bad_alloc 异常\n");
            update_stats(0, 0, 0);
        } catch (...) {
            printf("[C++] 捕获到未知异常\n");
            update_stats(0, 0, 0);
        }
        
        sleep(1);
    }
    
    // 清理所有C++块
    for (char* ptr : cpp_blocks) {
        delete[] ptr;
        update_stats(1, 0, 1);
    }
    
    printf("C++ 内存分配测试结束\n");
    return nullptr;
}

// 测试边界情况
void* test_edge_cases(void* arg) {
    (void)arg;
    printf("开始边界情况测试...\n");
    
    while (!should_exit) {
        // 测试零字节分配
        void* zero_ptr = malloc(0);
        if (zero_ptr) {
            printf("[边界] 零字节分配成功 @ %p\n", zero_ptr);
            free(zero_ptr);
        }
        
        // 测试极大内存分配（预期失败）
        void* huge_ptr = malloc(SIZE_MAX / 2);
        if (huge_ptr) {
            printf("[边界] 极大内存分配意外成功 @ %p\n", huge_ptr);
            free(huge_ptr);
        } else {
            printf("[边界] 极大内存分配正常失败\n");
        }
        
        // 测试连续小分配
        std::vector<void*> tiny_blocks;
        for (int i = 0; i < 10000 && !should_exit; i++) {
            void* tiny = malloc(1);
            if (tiny) {
                tiny_blocks.push_back(tiny);
            } else {
                break;
            }
        }
        printf("[边界] 连续分配了 %zu 个1字节块\n", tiny_blocks.size());
        
        // 释放所有小块
        for (void* ptr : tiny_blocks) {
            free(ptr);
        }
        
        // 测试realloc边界情况
        void* realloc_ptr = malloc(1024);
        if (realloc_ptr) {
            // 扩大
            realloc_ptr = realloc(realloc_ptr, 2048);
            if (realloc_ptr) {
                printf("[边界] realloc 扩大成功\n");
                
                // 缩小
                realloc_ptr = realloc(realloc_ptr, 512);
                if (realloc_ptr) {
                    printf("[边界] realloc 缩小成功\n");
                }
            }
            
            // 释放到零（等同于free）
            realloc_ptr = realloc(realloc_ptr, 0);
            if (!realloc_ptr) {
                printf("[边界] realloc 到零字节相当于 free\n");
            }
        }
        
        sleep(5); // 边界测试间隔长一些
    }
    
    printf("边界情况测试结束\n");
    return nullptr;
}

// 信号处理
void signal_handler(int signum) {
    printf("\n收到信号 %d，停止压力测试...\n", signum);
    should_exit = 1;
}

// 监控线程
void* monitor_thread(void* arg) {
    (void)arg;
    
    while (!should_exit) {
        print_stats();
        sleep(5);
    }
    
    return nullptr;
}

} // extern "C"

int main(int argc, char* argv[]) {
    printf("内存压力测试和边界情况测试程序\n");
    printf("==============================\n");
    
    int test_duration = STRESS_TEST_DURATION;
    
    // 解析命令行参数
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-t") == 0 && i + 1 < argc) {
            test_duration = atoi(argv[++i]);
        } else if (strcmp(argv[i], "-h") == 0) {
            printf("用法: %s [-t 秒数]\n", argv[0]);
            printf("  -t: 测试持续时间（默认30秒）\n");
            return 0;
        }
    }
    
    printf("测试配置:\n");
    printf("  持续时间: %d 秒\n", test_duration);
    printf("  最大分配: %.2f MB\n", MAX_ALLOCATION_SIZE / (1024.0 * 1024.0));
    printf("  最小分配: %d 字节\n", MIN_ALLOCATION_SIZE);
    printf("\n");
    
    // 设置信号处理
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    // 初始化随机种子
    srand(time(nullptr));
    
    // 创建测试线程
    pthread_t threads[5];
    
    printf("启动测试线程...\n");
    
    pthread_create(&threads[0], nullptr, monitor_thread, nullptr);
    pthread_create(&threads[1], nullptr, test_large_allocations, nullptr);
    pthread_create(&threads[2], nullptr, test_small_allocations, nullptr);
    pthread_create(&threads[3], nullptr, test_cpp_allocations, nullptr);
    pthread_create(&threads[4], nullptr, test_edge_cases, nullptr);
    
    printf("所有测试线程已启动，运行 %d 秒...\n", test_duration);
    
    // 主线程等待
    sleep(test_duration);
    should_exit = 1;
    
    printf("\n停止所有测试线程...\n");
    
    // 等待所有线程结束
    for (int i = 0; i < 5; i++) {
        pthread_join(threads[i], nullptr);
    }
    
    // 最终统计
    printf("\n最终测试结果:\n");
    print_stats();
    
    printf("\n压力测试完成\n");
    LOGI("压力测试完成");
    
    return 0;
}
