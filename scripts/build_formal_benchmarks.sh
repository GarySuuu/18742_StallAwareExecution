#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXT_DIR="${ROOT_DIR}/workloads/external"
POLY_DIR="${EXT_DIR}/polybench-c"
GAPBS_DIR="${EXT_DIR}/gapbs"

CC="${CC:-arm-linux-gnueabihf-gcc}"
CXX="${CXX:-arm-linux-gnueabihf-g++}"
COMMON_CFLAGS="${COMMON_CFLAGS:--O3 -static}"
COMMON_CXXFLAGS="${COMMON_CXXFLAGS:--std=c++11 -O3 -Wall -static}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $1"
    exit 1
  fi
}

need_file() {
  if [[ ! -e "$1" ]]; then
    echo "ERROR: required path not found: $1"
    exit 1
  fi
}

build_polybench_kernel() {
  local kernel_name="$1"
  local src_rel="$2"
  local src_dir
  src_dir="$(dirname "${src_rel}")"
  local out_dir="${POLY_DIR}/build-arm/${kernel_name}"
  local out_bin="${out_dir}/${kernel_name}"

  mkdir -p "${out_dir}"

  "${CC}" ${COMMON_CFLAGS} \
    "${POLY_DIR}/utilities/polybench.c" \
    "${POLY_DIR}/${src_rel}" \
    -I "${POLY_DIR}/utilities" \
    -I "${POLY_DIR}/${src_dir}" \
    -o "${out_bin}"

  echo "Built ${out_bin}"
}

build_gapbs() {
  make -C "${GAPBS_DIR}" clean
  make -C "${GAPBS_DIR}" SERIAL=1 \
    CXX="${CXX}" \
    CXX_FLAGS="${COMMON_CXXFLAGS}"
  echo "Built GAPBS kernels in ${GAPBS_DIR}"
}

need_cmd "${CC}"
need_cmd "${CXX}"
need_file "${POLY_DIR}/utilities/polybench.c"
need_file "${GAPBS_DIR}/Makefile"

build_polybench_kernel "atax" "linear-algebra/kernels/atax/atax.c"
build_polybench_kernel "bicg" "linear-algebra/kernels/bicg/bicg.c"
build_polybench_kernel "jacobi-2d" "stencils/jacobi-2d/jacobi-2d.c"
build_gapbs
