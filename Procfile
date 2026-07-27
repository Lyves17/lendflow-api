[build]
  command = "pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port $PORT"

[deploy]
  restart_policy.type = "on_failure"
  restart_policy.max_retries = 3
