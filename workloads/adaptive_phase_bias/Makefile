CROSS_COMPILE ?= arm-none-linux-gnueabihf-
CC := $(CROSS_COMPILE)gcc

CFLAGS := -O2 -static -nostdlib -ffreestanding -fno-builtin -std=c11 -Wall -Wextra
LDFLAGS := -Wl,-e,_start

SRC := adaptive_phase_bias.c
OUTDIR := bin/arm/linux
BIN := $(OUTDIR)/adaptive_phase_bias

.PHONY: all clean print-toolchain check-compiler

all: print-toolchain check-compiler $(BIN)

print-toolchain:
	@echo "Using compiler: $(CC)"
	@echo "Override with: make CROSS_COMPILE=<prefix>"

check-compiler:
	@command -v $(CC) >/dev/null 2>&1 || { \
	  echo "ERROR: compiler not found: $(CC)"; \
	  exit 1; \
	}

$(BIN): $(SRC)
	@mkdir -p $(OUTDIR)
	$(CC) $(CFLAGS) $(SRC) -o $(BIN) $(LDFLAGS)

clean:
	rm -rf bin
