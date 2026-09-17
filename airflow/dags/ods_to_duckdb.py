import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_ROOT = Path(__file__).resolve().parents[2]

default_args = {
    "owner": "whitespace",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def project_command(command: str) -> str:
    return f"cd {PROJECT_ROOT} && {command}"


with DAG(
    dag_id="ods_to_duckdb",
    description="Incremental ingestion: ODS (SQLite) → warehouse (DuckDB)",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule="0 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["ingestion", "ods", "duckdb"],
) as dag:
    ingest = BashOperator(
        task_id="ingest_ods_to_duckdb",
        bash_command=project_command(
            "uv run python -c 'from whitespace_analyzer.analytics."
            "duckdb_ingest import ingest_ods_to_duckdb; "
            "print(ingest_ods_to_duckdb())'"
        ),
        env={
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", "/tmp"),
        },
    )
    ingest
