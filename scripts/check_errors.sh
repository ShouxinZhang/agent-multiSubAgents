#!/usr/bin/env bash
#
# check_errors.sh - 通用全链路构建检查脚本
#
# 功能:
#   1. 自动识别目标工程（workspace/web/根目录/子项目 package.json）
#   2. 静态检查: TypeScript + ESLint
#   3. 构建检查: build/build:frontend/Vite
#   4. 汇总报告: 通过/失败/跳过
#
# 用法:
#   bash scripts/check_errors.sh            # 完整检查
#   bash scripts/check_errors.sh --lint     # 仅 ESLint
#   bash scripts/check_errors.sh --tsc      # 仅 TypeScript
#   bash scripts/check_errors.sh --build    # 仅构建
#
# 可选环境变量:
#   CHECK_TARGET_DIR=/abs/path/to/project   # 指定检查目标目录
#   CHECK_WORKSPACE=web                     # workspace 模式下的目标 workspace 名称

set -uo pipefail

# ── 颜色定义 ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# ── 项目路径 ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
WEB_DIR="$PROJECT_ROOT/web"
ROOT_NODE_MODULES="$PROJECT_ROOT/node_modules"
ROOT_LOCK="$PROJECT_ROOT/package-lock.json"
ROOT_PACKAGE_JSON="$PROJECT_ROOT/package.json"
WORKSPACE_NAME="${CHECK_WORKSPACE:-web}"

TARGET_DIR=""
TARGET_PACKAGE_JSON=""
TARGET_NODE_MODULES=""
TARGET_LOCK=""
TARGET_MODE="single"

# ── 结果计数器 ──
TOTAL_ERRORS=0
PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0
RESULTS=()

is_workspace_mode() {
  [ -f "$ROOT_PACKAGE_JSON" ] && grep -q '"workspaces"' "$ROOT_PACKAGE_JSON"
}

has_script_in_package() {
  local pkg_json=$1
  local script_name=$2
  node -e '
const fs = require("node:fs");
const pkg = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
const scripts = pkg.scripts || {};
process.exit(Object.prototype.hasOwnProperty.call(scripts, process.argv[2]) ? 0 : 1);
' "$pkg_json" "$script_name" >/dev/null 2>&1
}

has_script() {
  has_script_in_package "$TARGET_PACKAGE_JSON" "$1"
}

pick_best_package() {
  mapfile -t package_files < <(find "$PROJECT_ROOT" -mindepth 2 -maxdepth 5 -name package.json -not -path '*/node_modules/*' | sort)
  if [ "${#package_files[@]}" -eq 0 ]; then
    return 1
  fi

  local best_file=""
  local best_score=-99999

  for pkg in "${package_files[@]}"; do
    local dir
    dir="$(dirname "$pkg")"
    local score=0

    # 路径偏好：业务 demo/web 优先，脚本工具目录降权。
    if [[ "$dir" == *"/demos/"* ]]; then score=$((score + 50)); fi
    if [[ "$dir" == *"/web"* ]] || [[ "$dir" == *"/web-react"* ]]; then score=$((score + 30)); fi
    if [[ "$dir" == *"/scripts/"* ]]; then score=$((score - 25)); fi

    has_script_in_package "$pkg" "lint" && score=$((score + 10))
    has_script_in_package "$pkg" "build" && score=$((score + 10))
    has_script_in_package "$pkg" "build:frontend" && score=$((score + 8))
    has_script_in_package "$pkg" "typecheck" && score=$((score + 5))
    has_script_in_package "$pkg" "tsc" && score=$((score + 3))

    if [ "$score" -gt "$best_score" ]; then
      best_score=$score
      best_file="$pkg"
    fi
  done

  if [ -z "$best_file" ]; then
    return 1
  fi

  echo "$best_file"
  return 0
}

detect_target() {
  if [ -n "${CHECK_TARGET_DIR:-}" ]; then
    TARGET_DIR="$CHECK_TARGET_DIR"
    TARGET_MODE="single"
  elif is_workspace_mode; then
    TARGET_MODE="workspace"
    TARGET_DIR="$PROJECT_ROOT"
  elif [ -f "$WEB_DIR/package.json" ]; then
    TARGET_MODE="single"
    TARGET_DIR="$WEB_DIR"
  elif [ -f "$PROJECT_ROOT/package.json" ]; then
    TARGET_MODE="single"
    TARGET_DIR="$PROJECT_ROOT"
  else
    local best_pkg
    if ! best_pkg="$(pick_best_package)"; then
      echo -e "${RED}❌ 未找到可检查的 package.json（也不存在 workspace/web）。${NC}" >&2
      exit 2
    fi
    TARGET_MODE="single"
    TARGET_DIR="$(dirname "$best_pkg")"
  fi

  TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
  TARGET_PACKAGE_JSON="$TARGET_DIR/package.json"
  TARGET_NODE_MODULES="$TARGET_DIR/node_modules"
  TARGET_LOCK="$TARGET_DIR/package-lock.json"

  if [ "$TARGET_MODE" = "single" ] && [ ! -f "$TARGET_PACKAGE_JSON" ]; then
    echo -e "${RED}❌ 目标目录缺少 package.json: $TARGET_DIR${NC}" >&2
    exit 2
  fi
}

# ── 工具函数 ──
print_header() {
  echo ""
  echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}${CYAN}║     🔍 AI Journey - 全链路构建检查               ║${NC}"
  echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════╝${NC}"
  echo -e "${CYAN}  时间: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
  echo -e "${CYAN}  模式: ${TARGET_MODE}${NC}"
  echo -e "${CYAN}  目录: ${TARGET_DIR}${NC}"
  echo ""
}

print_step() {
  echo -e "${BOLD}${BLUE}── [$1/$TOTAL_STEPS] $2 ──${NC}"
}

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
      local line_count
      line_count=$(echo "$output" | wc -l)
      if [ "$line_count" -gt 30 ]; then
        echo -e "  ${YELLOW}... 省略 $((line_count - 30)) 行${NC}"
      fi
    fi
    RESULTS+=("${RED}✘ $step_name${NC}")
    FAIL_COUNT=$((FAIL_COUNT + 1))
    TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
  fi
}

record_skip() {
  local step_name=$1
  local reason=$2
  echo -e "  ${YELLOW}○ $step_name 跳过${NC}"
  if [ -n "$reason" ]; then
    echo -e "    ${YELLOW}$reason${NC}"
  fi
  RESULTS+=("${YELLOW}○ $step_name (skip)${NC}")
  SKIP_COUNT=$((SKIP_COUNT + 1))
}

# ── 检查步骤 ──
check_dependencies() {
  print_step "$STEP" "检查依赖是否安装"
  STEP=$((STEP + 1))

  if [ "$TARGET_MODE" = "workspace" ]; then
    if [ ! -d "$ROOT_NODE_MODULES" ] || [ ! -f "$ROOT_LOCK" ]; then
      echo -e "  ${YELLOW}⚠ 检测到 workspace，正在根目录统一安装依赖...${NC}"
      local output
      local install_exit=0
      if [ -f "$ROOT_LOCK" ]; then
        output=$(cd "$PROJECT_ROOT" && npm ci 2>&1) || install_exit=$?
      else
        output=$(cd "$PROJECT_ROOT" && npm install 2>&1) || install_exit=$?
      fi
      if [ "$install_exit" -ne 0 ] || [ ! -d "$ROOT_NODE_MODULES" ]; then
        record_result "依赖安装（workspace）" 1 "$output"
        return 1
      fi
    fi
    record_result "依赖检查（workspace）" 0 ""
    return 0
  fi

  if [ ! -d "$TARGET_NODE_MODULES" ] || [ ! -f "$TARGET_LOCK" ]; then
    echo -e "  ${YELLOW}⚠ 依赖未安装或缺少 lock 文件，正在安装...${NC}"
    local output
    local install_exit=0
    if [ -f "$TARGET_LOCK" ]; then
      output=$(cd "$TARGET_DIR" && npm ci 2>&1) || install_exit=$?
    else
      output=$(cd "$TARGET_DIR" && npm install 2>&1) || install_exit=$?
    fi
    if [ "$install_exit" -ne 0 ] || [ ! -d "$TARGET_NODE_MODULES" ]; then
      record_result "依赖安装" 1 "$output"
      return 1
    fi
  fi

  record_result "依赖检查" 0 ""
}

check_typescript() {
  print_step "$STEP" "TypeScript 类型检查"
  STEP=$((STEP + 1))

  local output=""
  local exit_code=0

  if [ "$TARGET_MODE" = "workspace" ]; then
    output=$(cd "$PROJECT_ROOT" && npm exec --workspace "$WORKSPACE_NAME" -- tsc --noEmit 2>&1) || exit_code=$?
    record_result "TypeScript 类型检查（workspace:$WORKSPACE_NAME）" "$exit_code" "$output"
    return
  fi

  if has_script "typecheck"; then
    output=$(cd "$TARGET_DIR" && npm run typecheck 2>&1) || exit_code=$?
    record_result "TypeScript 类型检查（script:typecheck）" "$exit_code" "$output"
    return
  fi

  if has_script "tsc"; then
    output=$(cd "$TARGET_DIR" && npm run tsc 2>&1) || exit_code=$?
    record_result "TypeScript 类型检查（script:tsc）" "$exit_code" "$output"
    return
  fi

  if [ -f "$TARGET_DIR/tsconfig.json" ]; then
    output=$(cd "$TARGET_DIR" && npx tsc --noEmit 2>&1) || exit_code=$?
    record_result "TypeScript 类型检查（npx tsc）" "$exit_code" "$output"
    return
  fi

  record_skip "TypeScript 类型检查" "未检测到 typecheck/tsc 脚本，且不存在 tsconfig.json"
}

check_eslint() {
  print_step "$STEP" "ESLint 代码规范检查"
  STEP=$((STEP + 1))

  local output=""
  local exit_code=0

  if [ "$TARGET_MODE" = "workspace" ]; then
    output=$(cd "$PROJECT_ROOT" && npm run --workspace "$WORKSPACE_NAME" lint 2>&1) || exit_code=$?
    record_result "ESLint 代码规范（workspace:$WORKSPACE_NAME）" "$exit_code" "$output"
    return
  fi

  if has_script "lint"; then
    output=$(cd "$TARGET_DIR" && npm run lint 2>&1) || exit_code=$?
    record_result "ESLint 代码规范（script:lint）" "$exit_code" "$output"
    return
  fi

  if compgen -G "$TARGET_DIR/eslint.config.*" >/dev/null || compgen -G "$TARGET_DIR/.eslintrc*" >/dev/null; then
    output=$(cd "$TARGET_DIR" && npx eslint . --max-warnings 0 2>&1) || exit_code=$?
    record_result "ESLint 代码规范（npx eslint）" "$exit_code" "$output"
    return
  fi

  record_skip "ESLint 代码规范" "未检测到 lint 脚本或 ESLint 配置文件"
}

check_build() {
  print_step "$STEP" "构建检查"
  STEP=$((STEP + 1))

  local output=""
  local exit_code=0

  if [ "$TARGET_MODE" = "workspace" ]; then
    output=$(cd "$PROJECT_ROOT" && npm run --workspace "$WORKSPACE_NAME" build 2>&1) || exit_code=$?
    record_result "构建检查（workspace:$WORKSPACE_NAME）" "$exit_code" "$output"
    return
  fi

  if has_script "build"; then
    output=$(cd "$TARGET_DIR" && npm run build 2>&1) || exit_code=$?
    record_result "构建检查（script:build）" "$exit_code" "$output"
    return
  fi

  if has_script "build:frontend"; then
    output=$(cd "$TARGET_DIR" && npm run build:frontend 2>&1) || exit_code=$?
    record_result "构建检查（script:build:frontend）" "$exit_code" "$output"
    return
  fi

  if compgen -G "$TARGET_DIR/vite.config.*" >/dev/null; then
    output=$(cd "$TARGET_DIR" && npx vite build 2>&1) || exit_code=$?
    record_result "构建检查（npx vite build）" "$exit_code" "$output"
    return
  fi

  record_skip "构建检查" "未检测到 build/build:frontend 脚本或 vite.config"
}

# ── 汇总报告 ──
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

  if [ "$FAIL_COUNT" -eq 0 ]; then
    echo -e "${BOLD}${GREEN}  🎉 全部检查通过！代码已准备就绪。${NC}"
  else
    echo -e "${BOLD}${RED}  ⚠ 存在 $FAIL_COUNT 个检查失败，请修复后重试。${NC}"
  fi
  echo ""
}

# ── 主流程 ──
main() {
  local mode="${1:-all}"

  detect_target

  STEP=1

  case "$mode" in
    --lint)
      TOTAL_STEPS=2
      print_header
      check_dependencies
      check_eslint
      ;;
    --tsc)
      TOTAL_STEPS=2
      print_header
      check_dependencies
      check_typescript
      ;;
    --build)
      TOTAL_STEPS=2
      print_header
      check_dependencies
      check_build
      ;;
    all|*)
      TOTAL_STEPS=4
      print_header
      check_dependencies
      check_typescript
      check_eslint
      check_build
      ;;
  esac

  print_summary

  exit "$FAIL_COUNT"
}

main "$@"
