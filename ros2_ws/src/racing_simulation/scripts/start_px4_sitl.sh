#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: start_px4_sitl.sh [options]

Start PX4 SITL with a configurable Gazebo model and world.

Options:
  --px4-dir PATH      PX4-Autopilot checkout.
  --model TARGET      PX4 Gazebo target (default: gz_x500_depth).
  --world NAME        Gazebo world name (default: default).
  --pose CSV          Spawn pose x,y,z,roll,pitch,yaw.
  --models-dir PATH   Additional project-owned Gazebo model directory.
  --worlds-dir PATH   Additional project-owned Gazebo world directory.
  --headless          Start Gazebo without its GUI.
  --dry-run           Print the resolved environment and command only.
  -h, --help          Show this help text.
EOF
}

px4_dir="${PX4_AUTOPILOT_DIR:-/root/docker_ws/uav_test/src/PX4-Autopilot}"
model="${PX4_SIM_MODEL:-gz_x500_depth}"
world="${PX4_GZ_WORLD:-default}"
pose="${PX4_GZ_MODEL_POSE:-0,0,0,0,0,0}"
models_dir="${RACING_GZ_MODELS_DIR:-}"
worlds_dir="${RACING_GZ_WORLDS_DIR:-}"
case "${RACING_HEADLESS:-false}" in
  1|true|TRUE|yes|YES)
    headless=1
    ;;
  *)
    headless=0
    ;;
esac
dry_run=0

while (($#)); do
  case "$1" in
    --px4-dir)
      px4_dir="$2"
      shift 2
      ;;
    --model)
      model="$2"
      shift 2
      ;;
    --world)
      world="$2"
      shift 2
      ;;
    --pose)
      pose="$2"
      shift 2
      ;;
    --pose=*)
      pose="${1#*=}"
      shift
      ;;
    --models-dir)
      models_dir="$2"
      shift 2
      ;;
    --worlds-dir)
      worlds_dir="$2"
      shift 2
      ;;
    --headless)
      headless=1
      shift
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! "$model" =~ ^gz_[A-Za-z0-9_]+$ ]]; then
  printf 'Invalid PX4 model target: %s\n' "$model" >&2
  exit 2
fi

if [[ ! "$world" =~ ^[A-Za-z0-9_]+$ ]]; then
  printf 'Invalid Gazebo world name: %s\n' "$world" >&2
  exit 2
fi

if [[ ! "$pose" =~ ^-?[0-9.]+(,-?[0-9.]+){5}$ ]]; then
  printf 'Invalid model pose: %s\n' "$pose" >&2
  exit 2
fi

if [[ ! -d "$px4_dir" ]]; then
  printf 'PX4 checkout does not exist: %s\n' "$px4_dir" >&2
  exit 2
fi

resource_paths=()
px4_models_dir="$px4_dir/Tools/simulation/gz/models"
if [[ -d "$px4_models_dir" ]]; then
  resource_paths+=("$px4_models_dir")
fi
if [[ -n "$models_dir" ]]; then
  [[ -d "$models_dir" ]] || {
    printf 'Gazebo model directory does not exist: %s\n' "$models_dir" >&2
    exit 2
  }
  resource_paths+=("$models_dir")
fi
if [[ -n "$worlds_dir" ]]; then
  [[ -d "$worlds_dir" ]] || {
    printf 'Gazebo world directory does not exist: %s\n' "$worlds_dir" >&2
    exit 2
  }
  resource_paths+=("$worlds_dir")
fi
if [[ -n "${GZ_SIM_RESOURCE_PATH:-}" ]]; then
  resource_paths+=("$GZ_SIM_RESOURCE_PATH")
fi

if ((${#resource_paths[@]})); then
  GZ_SIM_RESOURCE_PATH="$(IFS=:; printf '%s' "${resource_paths[*]}")"
  export GZ_SIM_RESOURCE_PATH
fi

project_world=""
if [[ -n "$worlds_dir" && -f "$worlds_dir/$world.sdf" ]]; then
  project_world="$worlds_dir/$world.sdf"
fi

export PX4_SIM_MODEL="$model"
export PX4_GZ_WORLD="$world"
export PX4_GZ_MODEL_POSE="$pose"
export GZ_IP="${GZ_IP:-127.0.0.1}"
if ((headless)); then
  export HEADLESS=1
else
  unset HEADLESS || true
fi

if ((dry_run)); then
  printf 'PX4_AUTOPILOT_DIR=%s\n' "$px4_dir"
  printf 'PX4_SIM_MODEL=%s\n' "$PX4_SIM_MODEL"
  printf 'PX4_GZ_WORLD=%s\n' "$PX4_GZ_WORLD"
  printf 'PX4_GZ_MODEL_POSE=%s\n' "$PX4_GZ_MODEL_POSE"
  printf 'GZ_SIM_RESOURCE_PATH=%s\n' "${GZ_SIM_RESOURCE_PATH:-}"
  printf 'GZ_IP=%s\n' "$GZ_IP"
  if [[ -n "$project_world" ]]; then
    printf 'PROJECT_GZ_WORLD=%s\n' "$project_world"
    if ((headless)); then
      printf 'gz sim -r -s %s\n' "$project_world"
    else
      printf 'gz sim -r %s\n' "$project_world"
    fi
    printf 'PX4_GZ_STANDALONE=1 make px4_sitl %s\n' "$model"
  else
    printf 'make px4_sitl %s\n' "$model"
  fi
  exit 0
fi

if [[ -n "$project_world" ]]; then
  gz_args=(-r)
  if ((headless)); then
    gz_args+=(-s)
  fi
  gz_args+=("$project_world")

  gz sim "${gz_args[@]}" </dev/null &
  gz_pid=$!
  cleanup() {
    kill -INT "$gz_pid" 2>/dev/null || true
    wait "$gz_pid" 2>/dev/null || true
  }
  trap cleanup EXIT

  export PX4_GZ_STANDALONE=1
  make -C "$px4_dir" px4_sitl "$model"
  exit $?
fi

exec make -C "$px4_dir" px4_sitl "$model"
