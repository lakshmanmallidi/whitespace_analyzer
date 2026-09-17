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

with DAG(
    dag_id="dbt_run",
    description="Run dbt models against the DuckDB warehouse",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule="30 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["dbt", "duckdb"],
) as dag:
    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=(
            f"cd {PROJECT_ROOT} && uv run dbt seed "
            "--project-dir dbt --profiles-dir dbt"
        ),
    )
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f"cd {PROJECT_ROOT} && uv run dbt run "
            "--project-dir dbt --profiles-dir dbt"
        ),
    )
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"cd {PROJECT_ROOT} && uv run dbt test "
            "--project-dir dbt --profiles-dir dbt"
        ),
    )
    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot",
        bash_command=(
            f"cd {PROJECT_ROOT} && uv run dbt snapshot "
            "--project-dir dbt --profiles-dir dbt"
        ),
    )
    dbt_seed >> dbt_run >> dbt_snapshot >> dbt_test
