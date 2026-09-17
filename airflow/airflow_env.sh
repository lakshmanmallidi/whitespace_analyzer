#!/bin/zsh
# Airflow environment (isolated venv at airflow/.venv, sqlite metadata db).
# Source before running airflow commands. Paths resolve from this file's
# location, so sourcing works from any working directory.
_ENV_DIR="${${(%):-%x}:A:h}"
if [[ -z "$_ENV_DIR" || "$_ENV_DIR" != /* ]]; then
  _ENV_DIR="$PWD/airflow"
fi
_PROJECT_ROOT="${_ENV_DIR:h}"
set -a
export AIRFLOW_HOME="${AIRFLOW_HOME:-$_PROJECT_ROOT/airflow/airflow_home}"
# macOS: stop os_log/libsystem_trace from initializing pre-fork; setproctitle
# in forked gunicorn workers otherwise segfaults (CoreFoundation fork race).
export OS_ACTIVITY_MODE=disable
export AIRFLOW__CORE__EXECUTOR=SequentialExecutor
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="sqlite:///${AIRFLOW_HOME}/airflow.db"
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__CORE__DAGS_FOLDER="$_PROJECT_ROOT/airflow/dags"
export AIRFLOW__CORE__LOGS_FOLDER="$AIRFLOW_HOME/logs"
export AIRFLOW__WEBSERVER__WEB_SERVER_PORT=8080
set +a
unset _ENV_DIR _PROJECT_ROOT
