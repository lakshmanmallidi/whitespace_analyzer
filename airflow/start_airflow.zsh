#!/bin/zsh
# Start Airflow with ONE command (dev): `airflow standalone` runs the
# scheduler, triggerer and webserver in a single process tree.
# Ctrl-C stops everything. Stale processes are killed first so ports
# 8080/8793 never conflict.
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
uv run --project . airflow standalone
