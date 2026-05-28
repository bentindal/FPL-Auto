"""
Apache Airflow DAG for FPL Model Retraining Pipeline

Post-GW automated retraining orchestration:
- Schedule: Tuesday 19:00 UTC (post-GW); runs Tue-Sun (times 2-7)
- Tasks: collect → validate → retrain → evaluate → export (5 sequential)
- Each task calls wrapper functions from fpl_auto.retrainer module

DAG Configuration:
- DAG ID: fpl_retrain_schedule
- Schedule Interval: 0 19 * * 2-7 (Tue-Sun 19:00 UTC)
- Retries: 1 per task
- Retry Delay: 10 minutes
- Start Date: 2024-08-01 (post-season start)
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Default arguments for all tasks
default_args = {
    'owner': 'fpl_ml',
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
    'start_date': datetime(2024, 8, 1),
    'email_on_failure': False,  # Can enable if mail configured
}

# DAG definition
dag = DAG(
    dag_id='fpl_retrain_schedule',
    default_args=default_args,
    schedule_interval='0 19 * * 2-7',  # 19:00 Tue-Sun UTC
    description='Post-GW model retraining pipeline',
    catchup=False,
    tags=['fpl', 'retraining', 'ml']
)

# Import task callables from retrainer module
from fpl_auto.retrainer import (
    collect_gw_data,
    validate_week_data,
    retrain_on_schedule,
    check_drift,
    write_predictions_tsv
)

# Task 1: Collect GW data
collect_task = PythonOperator(
    task_id='collect',
    python_callable=collect_gw_data,
    op_args=[1, '2024-25'],  # Will be overridden by Airflow context
    dag=dag,
)

# Task 2: Validate collected data
validate_task = PythonOperator(
    task_id='validate',
    python_callable=validate_week_data,
    op_args=[1, '2024-25'],
    dag=dag,
)

# Task 3: Retrain models
retrain_task = PythonOperator(
    task_id='retrain',
    python_callable=retrain_on_schedule,
    op_args=[1, '2024-25'],
    depends_on_past=False,
    dag=dag,
)

# Task 4: Evaluate metrics and detect drift
evaluate_task = PythonOperator(
    task_id='evaluate',
    python_callable=check_drift,
    op_args=[1, '2024-25'],
    dag=dag,
)

# Task 5: Export predictions to TSV
export_task = PythonOperator(
    task_id='export',
    python_callable=write_predictions_tsv,
    op_args=[1, '2024-25'],
    dag=dag,
)

# Task dependencies: collect >> validate >> retrain >> evaluate >> export
collect_task >> validate_task
validate_task >> retrain_task
retrain_task >> evaluate_task
evaluate_task >> export_task
