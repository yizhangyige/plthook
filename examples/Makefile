# PLTHook 示例程序 Makefile

CC = gcc
CFLAGS = -Wall -Wextra -I..
LDFLAGS = -ldl

# 平台检测
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    PLTHOOK_SRC = ../plthook_osx.c
    LDFLAGS = -ldl
else ifeq ($(UNAME_S),Linux)
    PLTHOOK_SRC = ../plthook_elf.c
    LDFLAGS = -ldl -lm
else
    $(error Unsupported platform: $(UNAME_S))
endif

# 目标程序
TARGETS = malloc_hook

all: $(TARGETS)

malloc_hook: malloc_hook.c $(PLTHOOK_SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

clean:
	rm -f $(TARGETS)

.PHONY: all clean
