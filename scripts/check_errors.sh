#!/usr/bin/env bash
#
# check_errors.sh - Generic quality gate script
#
# Usage:
#   bash scripts/check_errors.sh
#   bash scripts/check_errors.sh --lint
#   bash scripts/check_errors.sh --tsc
#   bash scripts/check_errors.sh --build
#
# Customization (optional env):
#   QUALITY_DEPENDENCY_CMD="npm ci"
#   QUALITY_TYPECHECK_CMD="npm run typecheck"
#   QUALITY_LINT_CMD="npm run lint"
#   QUALITY_BUILD_CMD="npm run build"
#

set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

TOTAL_ERRORS=0
PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0
RESULTS=()

record_result() {
  local step_name=$1
  local exit_code=$2
  local output=$3

  if [ "$exit_code" -eq 0 ]; then
    echo -e "  ${GREEN}✔ $step_name 通过${NC}"
    RESULTS+=("${GREEN}✔ $step_name${NC}")
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo -e "  ${RED}✘ $step_name 失败${NC}"
    if [ -n "$output" ]; then
      echo -e "${YELLOW}$output${NC}" | head -30
    fi
    RESULTS+=("${RED}✘ $step_name${NC}")
    FAIL_COUNT=$((FAIL_COUNT + 1))
    TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
  fi
}

run_cmd_step() {
  local name="$1"
  local cmd="$2"
  local output=""
  local code=0
  output=$(cd "$PROJECT_ROOT" && bash -lc "$cmd" 2>&1) || code=$?
  record_result "$name" "$code" "$output"
}

detect_typecheck_cmd() {
  if [ -n "${QUALITY_TYPECHECK_CMD:-}" ]; then
    echo "$QUALITY_TYPECHECK_CMD"
    return
  fi
  if cd "$PROJECT_ROOT" && npm run | grep -qE ' typecheck\b'; then
    echo "npm run typecheck"
    return
  fi
  if [ -f "$PROJECT_ROOT/tsconfig.json" ]; then
    echo "npx tsc --noEmit"
    return
  fi
  echo ""
}

detect_lint_cmd() {
  if [ -n "${QUALITY_LINT_CMD:-}" ]; then
    echo "$QUALITY_LINT_CMD"
    return
  fi
  if cd "$PROJECT_ROOT" && npm run | grep -qE ' lint\b'; then
    echo "npm run lint"
    return
  fi
  echo ""
}

detect_build_cmd() {
  if [ -n "${QUALITY_BUILD_CMD:-}" ]; then
    echo "$QUALITY_BUILD_CMD"
    return
  fi
  if cd "$PROJECT_ROOT" && npm run | grep -qE ' build\b'; then
    echo "npm run build"
    return
  fi
  echo ""
}

check_dependencies() {
  local cmd="${QUALITY_DEPENDENCY_CMD:-}"
  if [ -z "$cmd" ]; then
    if [ -d "$PROJECT_ROOT/node_modules" ]; then
      record_result "依赖检查" 0 ""
      return
    fi
    if [ -f "$PROJECT_ROOT/package-lock.json" ]; then
      cmd="npm ci"
    else
      cmd="npm install"
    fi
  fi

  local output=""
  local code=0
  output=$(cd "$PROJECT_ROOT" && bash -lc "$cmd" 2>&1) || code=$?
  record_result "依赖检查/安装" "$code" "$output"
}

run_typecheck() {
  local cmd
  cmd="$(detect_typecheck_cmd)"
  if [ -z "$cmd" ]; then
    echo -e "  ${YELLOW}⚠ 未发现 typecheck 命令，已跳过${NC}"
    RESULTS+=("${YELLOW}⚠ Typecheck 跳过${NC}")
    SKIP_COUNT=$((SKIP_COUNT + 1))
    return
  fi
  run_cmd_step "TypeScript/Typecheck" "$cmd"
}

run_lint() {
  local cmd
  cmd="$(detect_lint_cmd)"
  if [ -z "$cmd" ]; then
    echo -e "  ${YELLOW}⚠ 未发现 lint 命令，已跳过${NC}"
    RESULTS+=("${YELLOW}⚠ Lint 跳过${NC}")
    SKIP_COUNT=$((SKIP_COUNT + 1))
    return
  fi
  run_cmd_step "Lint" "$cmd"
}

run_build() {
  local cmd
  cmd="$(detect_build_cmd)"
  if [ -z "$cmd" ]; then
    echo -e "  ${YELLOW}⚠ 未发现 build 命令，已跳过${NC}"
    RESULTS+=("${YELLOW}⚠ Build 跳过${NC}")
    SKIP_COUNT=$((SKIP_COUNT + 1))
    return
  fi
  run_cmd_step "Build" "$cmd"
}

print_header() {
  echo ""
  echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}${CYAN}║     🔍 Generic Repo - 质量门禁检查               ║${NC}"
  echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════╝${NC}"
  echo -e "${CYAN}  时间: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
  echo -e "${CYAN}  目录: ${PROJECT_ROOT}${NC}"
  echo ""
}

print_summary() {
  echo ""
  echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}${CYAN}║     📊 检查汇总报告                              ║${NC}"
  echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════╝${NC}"
  echo ""

  for result in "${RESULTS[@]}"; do
    echo -e "  $result"
  done

  echo ""
  echo -e "  ${GREEN}通过: $PASS_COUNT${NC}  ${RED}失败: $FAIL_COUNT${NC}  ${YELLOW}跳过: $SKIP_COUNT${NC}"
  echo ""
}

main() {
  local mode="${1:-all}"
  print_header

  check_dependencies

  case "$mode" in
    --lint)
      run_lint
      ;;
    --tsc)
      run_typecheck
      ;;
    --build)
      run_build
      ;;
    all|*)
      run_typecheck
      run_lint
      run_build
      ;;
  esac

  print_summary
  exit "$FAIL_COUNT"
}

main "$@"
