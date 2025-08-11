#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/var/www/vhosts/mauriceb.nl/ChatGPT-Micro-Cap-Experiment"
VENV_DIR="/var/www/vhosts/mauriceb.nl/.venvs/microcap-bot"
LOG_DIR="$APP_DIR/logs"
REQ_SHA="$VENV_DIR/requirements.sha256"
TS="$(date +%F)"
LOG="$LOG_DIR/bot_${TS}.log"

mkdir -p "$LOG_DIR" "$(dirname "$VENV_DIR")"
cd "$APP_DIR"

# pick newest python
PYBIN=""
for c in /opt/plesk/python/3.12/bin/python3 /opt/plesk/python/3.11/bin/python3 \
          /opt/plesk/python/3.10/bin/python3 /opt/plesk/python/3.9/bin/python3 \
          /usr/bin/python3.12 /usr/bin/python3.11 /usr/bin/python3.10 /usr/bin/python3.9 \
          /usr/bin/python3; do
  [ -x "$c" ] && PYBIN="$c" && break
done
[ -z "$PYBIN" ] && echo "No python3 found" | tee -a "$LOG" && exit 1

PYMAJ="$($PYBIN -c 'import sys; print(sys.version_info.major)')"
PYMIN="$($PYBIN -c 'import sys; print(sys.version_info.minor)')"
PYVER_STR="$($PYBIN -c 'import sys; print(".".join(map(str,sys.version_info[:3])))')"
echo "Selected interpreter: $PYBIN (Python $PYVER_STR)" | tee -a "$LOG"
if [ "$PYMAJ" -lt 3 ] || { [ "$PYMAJ" -eq 3 ] && [ "$PYMIN" -lt 9 ]; }; then
  echo "Python $PYVER_STR is too old (need >= 3.9)" | tee -a "$LOG"
  exit 1
fi

# create venv once (no pip self-upgrade here)
if [ ! -d "$VENV_DIR" ]; then
  "$PYBIN" -m venv "$VENV_DIR"
fi
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# calmer pip
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_PYTHON_VERSION_WARNING=1

echo "VENV: $VIRTUAL_ENV" >> "$LOG"
python -c "import sys; print('Running Python:', sys.version)" >> "$LOG" 2>&1

# install deps only when requirements changed
if [ -f requirements.txt ]; then
  NEW_HASH="$(sha256sum requirements.txt | awk '{print $1}')"
  OLD_HASH="$(cat "$REQ_SHA" 2>/dev/null || true)"
  if [ "$NEW_HASH" != "$OLD_HASH" ]; then
    echo "[deps] installing requirements..." | tee -a "$LOG"
    pip install -r requirements.txt >> "$LOG" 2>&1
    echo "$NEW_HASH" > "$REQ_SHA"
  fi
fi

export PYTHONUNBUFFERED=1
export TZ=Europe/Amsterdam
export MPLBACKEND=Agg
export RUN_UNTIL="2025-09-01"

echo "[run] starting bot $(date -Iseconds)" | tee -a "$LOG"
set +e
python -m app.main_trading_bot >> "$LOG" 2>&1
RC=$?
set -e
echo "[run] finished with code $RC at $(date -Iseconds)" | tee -a "$LOG"
exit $RC
