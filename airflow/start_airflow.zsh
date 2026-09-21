#!/bin/zsh
# Start Airflow with ONE command (dev): `airflow standalone` runs the
# scheduler, triggerer and webserver in a single process tree.
# Ctrl-C stops everything. Stale processes are killed first so ports
# 8080/8793 never conflict.
# Login is always admin / admin (see the credential pin below).
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/airflow_env.sh"

pkill -f "airflow standalone" 2>/dev/null || true
pkill -f "airflow scheduler" 2>/dev/null || true
pkill -f "airflow webserver" 2>/dev/null || true
pkill -f "airflow triggerer" 2>/dev/null || true
lsof -ti:8080 -ti:8793 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

cd "$DIR"

# Pin the dev login to the credentials the README documents. `airflow
# standalone` only creates `admin` when it is missing, so seed or refresh it
# first; otherwise a fresh AIRFLOW_HOME silently hands out a random password.
uv run --project . airflow db migrate >/dev/null
if ! uv run --project . airflow users reset-password \
  --username admin --password admin >/dev/null 2>&1; then
  uv run --project . airflow users create --username admin --password admin \
    --firstname Admin --lastname User --role Admin --email admin@example.com
fi
# Keep Airflow's own ready-banner password in sync with the real login; it
# reads this file verbatim when the user already exists.
printf 'admin' >"$AIRFLOW_HOME/standalone_admin_password.txt"
chmod 600 "$AIRFLOW_HOME/standalone_admin_password.txt"
echo "Airflow login: admin / admin"

uv run --project . airflow standalone
