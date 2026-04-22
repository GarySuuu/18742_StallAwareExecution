CROSS_COMPILE ?= arm-linux-gnueabihf-
CC := $(CROSS_COMPILE)gcc
CFLAGS := -O2 -static -nostdlib -ffreestanding -fno-builtin -std=c11 -Wall -Wextra
LDFLAGS := -Wl,-e,_start -lgcc
SRC := adaptive_showcase_worst.c
OUTDIR := bin/arm/linux
BIN := $(OUTDIR)/adaptive_showcase_worst
.PHONY: all clean
all: $(BIN)
$(BIN): $(SRC) ../common/mini_runtime.h
	@mkdir -p $(OUTDIR)
	$(CC) $(CFLAGS) $(SRC) -o $(BIN) $(LDFLAGS)
clean:
	rm -rf bin
