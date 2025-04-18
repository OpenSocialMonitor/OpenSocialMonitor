import os
from celery import Celery
from dotenv import load_dotenv

# Load .env file BEFORE Celery configuration reads environment variables
# Ensure this runs early, especially if tasks might be imported elsewhere too.
load_dotenv()

# Get the broker URL from environment variable
broker_url = os.environ.get("CELERY_BROKER_URL")
if not broker_url:
    # Provide a default or raise a more informative error
    # raise ValueError("CELERY_BROKER_URL not found in environment variables (.env file). Please configure it (e.g., redis://localhost:6379/0).")
    print("Warning: CELERY_BROKER_URL not found in environment variables. Using default redis://localhost:6379/0")
    print("Ensure Redis is running and accessible at this address.")
    broker_url = "redis://localhost:6379/0"

# --- Celery Application Definition ---

# The first argument is the "main name" of the project module, used for naming tasks.
# Let's use 'src' as it's the root of your main code.
# The 'include' list tells Celery where to look for files containing @app.task decorators.
# We'll assume tasks will be defined in 'src/tasks.py'.
app = Celery(
    'src', # Project module name
    broker=broker_url,
    backend=broker_url, # Using Redis as backend too (to store task results, optional but useful)
    include=['src.tasks'] # Tells Celery to look for tasks in src/tasks.py
)

# --- Optional Celery Configuration ---
# See Celery documentation for more options: https://docs.celeryq.dev/en/stable/userguide/configuration.html
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC', # Use UTC for consistency
    enable_utc=True,
    # Example: Default task time limits (optional)
    # task_time_limit=300, # Hard time limit (5 minutes)
    # task_soft_time_limit=240, # Soft time limit (4 minutes)

    # Example: Settings for task retries (can also be set per-task)
    task_acks_late = True, # Acknowledge task only after completion/failure (requires reliable broker)
    task_reject_on_worker_lost = True, # Requeue task if worker dies unexpectedly
    # broker_connection_retry_on_startup = True, # For Celery 5.2.3+
)

# Optional: If you want to run the worker directly via 'python celery_app.py worker'
# (though the standard 'celery -A celery_app worker' command is preferred)
# if __name__ == '__main__':
#    app.start()

print("Celery app configured.")