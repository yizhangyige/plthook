LOCAL_PATH := $(call my-dir)

# PLTHook 静态库
include $(CLEAR_VARS)
LOCAL_MODULE    := plthook
LOCAL_SRC_FILES := ../../../plthook_elf.c
LOCAL_C_INCLUDES := ../../..
LOCAL_CFLAGS := -Wall -Wextra -fPIC
include $(BUILD_STATIC_LIBRARY)

# 测试共享库
include $(CLEAR_VARS)
LOCAL_MODULE    := libtest
LOCAL_SRC_FILES := ../../libtest.c
LOCAL_C_INCLUDES := ../..
LOCAL_CFLAGS := -fno-builtin-ceil -DLIBTEST_DLL -Wall
LOCAL_LDLIBS := -lm
include $(BUILD_SHARED_LIBRARY)

# 测试程序
include $(CLEAR_VARS)
LOCAL_MODULE    := testprog
LOCAL_SRC_FILES := ../../testprog.c
LOCAL_C_INCLUDES := ../.. ../../..
LOCAL_STATIC_LIBRARIES := plthook
LOCAL_SHARED_LIBRARIES := libtest
LOCAL_LDLIBS := -ldl -lm -llog
include $(BUILD_EXECUTABLE)

# 内存监控程序
include $(CLEAR_VARS)
LOCAL_MODULE    := memory_monitor
LOCAL_SRC_FILES := ../../memory_monitor.c ../../../plthook_elf.c
LOCAL_C_INCLUDES := ../.. ../../..
LOCAL_CFLAGS := -Wall -Wextra -DANDROID_PLATFORM
LOCAL_LDLIBS := -ldl -lm -llog
include $(BUILD_EXECUTABLE)

# Android 简化测试程序
include $(CLEAR_VARS)
LOCAL_MODULE    := android_simple_test
LOCAL_SRC_FILES := ../../android_simple_test.c ../../../plthook_elf.c
LOCAL_C_INCLUDES := ../.. ../../..
LOCAL_CFLAGS := -Wall -Wextra -DANDROID_PLATFORM
LOCAL_LDLIBS := -ldl -lm -llog
include $(BUILD_EXECUTABLE)

# 多线程内存监控测试程序
include $(CLEAR_VARS)
LOCAL_MODULE    := multithread_memory_test
LOCAL_SRC_FILES := ../../multithread_memory_test.c ../../../plthook_elf.c
LOCAL_C_INCLUDES := ../.. ../../..
LOCAL_CFLAGS := -Wall -Wextra -DANDROID_PLATFORM
LOCAL_LDLIBS := -ldl -lm -llog
include $(BUILD_EXECUTABLE)

# 多线程内存监控测试程序 - C++ 增强版
include $(CLEAR_VARS)
LOCAL_MODULE    := multithread_memory_test_cpp
LOCAL_SRC_FILES := ../../multithread_memory_test_cpp.cpp ../../../plthook_elf.c
LOCAL_C_INCLUDES := ../.. ../../..
LOCAL_CFLAGS := -Wall -Wextra -DANDROID_PLATFORM
LOCAL_CPPFLAGS := -std=c++11 -frtti -fexceptions
LOCAL_LDLIBS := -ldl -lm -llog
include $(BUILD_EXECUTABLE)

# 内存压力测试程序
include $(CLEAR_VARS)
LOCAL_MODULE    := memory_stress_test
LOCAL_SRC_FILES := ../../memory_stress_test.cpp
LOCAL_C_INCLUDES := ../.. ../../..
LOCAL_CFLAGS := -Wall -Wextra -DANDROID_PLATFORM
LOCAL_CPPFLAGS := -std=c++11 -frtti -fexceptions
LOCAL_LDLIBS := -ldl -lm -llog
include $(BUILD_EXECUTABLE)

# 高级内存监控测试程序 - 支持所有内存操作的钩子监控
include $(CLEAR_VARS)
LOCAL_MODULE    := advanced_memory_test
LOCAL_SRC_FILES := ../../advanced_memory_test.cpp ../../../plthook_elf.c
LOCAL_C_INCLUDES := ../.. ../../..
LOCAL_CFLAGS := -Wall -Wextra -DANDROID_PLATFORM
LOCAL_CPPFLAGS := -std=c++11 -frtti -fexceptions
LOCAL_LDLIBS := -ldl -lm -llog
include $(BUILD_EXECUTABLE)
