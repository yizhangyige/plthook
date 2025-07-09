cmake_minimum_required(VERSION 3.16)
project(plthook VERSION 1.0.0 LANGUAGES C)

# 设置 C 标准
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# 构建选项
option(BUILD_SHARED_LIBS "Build shared libraries" ON)
option(BUILD_TESTS "Build test programs" ON)
option(BUILD_ANDROID "Build for Android" OFF)

# 平台检测
if(WIN32)
    set(PLTHOOK_SOURCE "plthook_win32.c")
    set(PLTHOOK_LIBS dbghelp)
elseif(APPLE)
    set(PLTHOOK_SOURCE "plthook_osx.c")
    set(PLTHOOK_LIBS dl)
elseif(UNIX)
    set(PLTHOOK_SOURCE "plthook_elf.c")
    set(PLTHOOK_LIBS dl m)
endif()

# 包含目录
include_directories(${CMAKE_CURRENT_SOURCE_DIR})

# PLTHook 库
if(BUILD_SHARED_LIBS)
    add_library(plthook SHARED ${PLTHOOK_SOURCE})
else()
    add_library(plthook STATIC ${PLTHOOK_SOURCE})
endif()

target_link_libraries(plthook ${PLTHOOK_LIBS})

# 设置库的输出属性
set_target_properties(plthook PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION 1
    PUBLIC_HEADER "plthook.h"
)

# 编译选项
if(MSVC)
    target_compile_options(plthook PRIVATE /W3)
else()
    target_compile_options(plthook PRIVATE -Wall -Wextra)
    if(CMAKE_SYSTEM_PROCESSOR MATCHES "arm|aarch64")
        target_compile_options(plthook PRIVATE -fPIC)
    endif()
endif()

# 测试程序
if(BUILD_TESTS)
    # libtest 共享库
    add_library(libtest SHARED test/libtest.c)
    target_include_directories(libtest PRIVATE test)
    target_compile_definitions(libtest PRIVATE LIBTEST_DLL)
    
    if(WIN32)
        target_link_libraries(libtest m)
        # Windows 需要 .def 文件
        if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/test/libtest.def")
            set_target_properties(libtest PROPERTIES
                LINK_FLAGS "/DEF:${CMAKE_CURRENT_SOURCE_DIR}/test/libtest.def"
            )
        endif()
    else()
        target_link_libraries(libtest m)
    endif()
    
    # 测试程序
    add_executable(testprog test/testprog.c ${PLTHOOK_SOURCE})
    target_include_directories(testprog PRIVATE . test)
    target_link_libraries(testprog libtest ${PLTHOOK_LIBS})
    
    # 内存监控程序
    add_executable(memory_monitor test/memory_monitor.c ${PLTHOOK_SOURCE})
    target_include_directories(memory_monitor PRIVATE . test)
    target_link_libraries(memory_monitor ${PLTHOOK_LIBS})
    
    # Windows 特定链接库
    if(WIN32)
        target_link_libraries(memory_monitor psapi)
    endif()
    
    # 设置运行时库路径
    if(UNIX AND NOT APPLE)
        set_target_properties(testprog PROPERTIES
            INSTALL_RPATH "$ORIGIN"
            BUILD_WITH_INSTALL_RPATH TRUE
        )
        set_target_properties(memory_monitor PROPERTIES
            INSTALL_RPATH "$ORIGIN"
            BUILD_WITH_INSTALL_RPATH TRUE
        )
    endif()
endif()

# Android 特定配置
if(ANDROID)
    set(BUILD_ANDROID ON)
    target_compile_definitions(plthook PRIVATE __ANDROID__)
    
    if(BUILD_TESTS)
        target_compile_definitions(libtest PRIVATE __ANDROID__)
        target_compile_definitions(testprog PRIVATE __ANDROID__)
        
        # Android 不需要 -lm，它是内置的
        target_link_libraries(libtest)
        target_link_libraries(testprog libtest dl)
    endif()
endif()

# 安装配置
include(GNUInstallDirs)

install(TARGETS plthook
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

if(BUILD_TESTS)
    install(TARGETS libtest testprog
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    )
endif()

# 打包配置
set(CPACK_PACKAGE_NAME "plthook")
set(CPACK_PACKAGE_VERSION ${PROJECT_VERSION})
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "PLT Hook Library")
set(CPACK_PACKAGE_VENDOR "Kubo Takehiro")

if(WIN32)
    set(CPACK_GENERATOR "ZIP")
elseif(APPLE)
    set(CPACK_GENERATOR "TGZ")
else()
    set(CPACK_GENERATOR "TGZ;DEB")
endif()

include(CPack)

# 自定义目标：显示构建信息
add_custom_target(info
    COMMAND ${CMAKE_COMMAND} -E echo "PLTHook Build Information:"
    COMMAND ${CMAKE_COMMAND} -E echo "  Platform: ${CMAKE_SYSTEM_NAME}"
    COMMAND ${CMAKE_COMMAND} -E echo "  Architecture: ${CMAKE_SYSTEM_PROCESSOR}"
    COMMAND ${CMAKE_COMMAND} -E echo "  Compiler: ${CMAKE_C_COMPILER_ID}"
    COMMAND ${CMAKE_COMMAND} -E echo "  Build Type: ${CMAKE_BUILD_TYPE}"
    COMMAND ${CMAKE_COMMAND} -E echo "  PLTHook Source: ${PLTHOOK_SOURCE}"
    COMMAND ${CMAKE_COMMAND} -E echo "  Build Shared: ${BUILD_SHARED_LIBS}"
    COMMAND ${CMAKE_COMMAND} -E echo "  Build Tests: ${BUILD_TESTS}"
    COMMAND ${CMAKE_COMMAND} -E echo "  Android Build: ${BUILD_ANDROID}"
)

# 测试目标
if(BUILD_TESTS)
    enable_testing()
    
    add_test(NAME test_open 
        COMMAND testprog open
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
    
    add_test(NAME test_open_by_handle 
        COMMAND testprog open_by_handle
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
    
    if(NOT WIN32)
        add_test(NAME test_open_by_address 
            COMMAND testprog open_by_address
            WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
    endif()
    
    # 设置测试环境
    if(UNIX AND NOT APPLE)
        set_tests_properties(test_open test_open_by_handle PROPERTIES
            ENVIRONMENT "LD_LIBRARY_PATH=${CMAKE_CURRENT_BINARY_DIR}")
        if(NOT WIN32)
            set_tests_properties(test_open_by_address PROPERTIES
                ENVIRONMENT "LD_LIBRARY_PATH=${CMAKE_CURRENT_BINARY_DIR}")
        endif()
    endif()
endif()
