CROSS_COMPILE ?= arm-none-linux-gnueabihf-
SUITE_DIRS := \
	serialized_pointer_chase \
	branch_entropy \
	hash_probe_chain \
	phase_scan_mix \
	stream_cluster_reduce \
	compute_queue_pressure \
	fetch_bandwidth_stress \
	iq_pressure_stress \
	lsq_pressure_stress \
	rename_dispatch_stress
EXTERNAL_SUITES := \
	polybench-c \
	gapbs

.PHONY: all clean list list-external

all:
	@for d in $(SUITE_DIRS); do \
	  echo "==> Building $$d"; \
	  $(MAKE) -C $$d CROSS_COMPILE=$(CROSS_COMPILE); \
	done

clean:
	@for d in $(SUITE_DIRS); do \
	  echo "==> Cleaning $$d"; \
	  $(MAKE) -C $$d clean; \
	done

list:
	@printf '%s\n' $(SUITE_DIRS)

list-external:
	@printf '%s\n' $(EXTERNAL_SUITES)
