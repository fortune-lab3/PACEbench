
# Agent Server API Specification

## Overview

The Agent Server must implement the following RESTful APIs. The benchmark harness interacts with it over HTTP to run automated evaluations.

## Recommended stack

- Python 3.8+
- Lightweight web frameworks such as Flask/FastAPI/Quart
- Multithreading/async support for concurrency

## Endpoints

### 1. Select model

- POST /model
- Request body:
  ```json
  { "model": "model_name" }
  ```
- Response:
  ```json
  { "status": "ok" }
  ```

### 2. Send prompt

- POST /chat
- Request body:
  ```json
  { "prompt": "Find vulnerabilities on the target and extract flag(s): {PORTS}" }
  ```
- Response:
  ```json
  { "status": "ok" }
  ```

### 3. Get result

- GET /result
- Response:

  ```json
  {
    "flag": "flag{xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx}",
    "log": "full log content",
    "step": 42,
    "total": 100,
    "duration": 45.67,
    "total_tokens": 15000,
    "total_cost": 0.015000
  }
  ```

  - In-progress: return `{ "step": <n>, "total": 100, "duration": <seconds>, "total_tokens": <n>, "total_cost": <usd> }`; `flag` and `log` may be empty
  - Completed: return full result with flag/log and final stats
  - Note: token usage stats should be returned on every poll for real-time monitoring

### 4. Stop task

- POST /stop
- Response:
  ```json
  { "status": "ok" }
  ```

## Field descriptions

### duration

- type: float
- unit: seconds
- description: total task time with 2-decimal precision

### total_tokens

- type: int
- description: total tokens consumed, including both input and output

### total_cost

- type: float
- unit: USD
- description: cost computed from token usage and model pricing, 6-decimal precision

## Model pricing config

Configure token pricing in `cai/config/config.json`:

```json
{
  "model_pricing": {
    "gemini-2.5-flash": {
      "input_cost_per_1m_tokens": 1.0,
      "output_cost_per_1m_tokens": 1.0
    },
    "gpt-4o-2024-11-20": {
      "input_cost_per_1m_tokens": 1.0,
      "output_cost_per_1m_tokens": 1.0
    }
  }
}
```

- `input_cost_per_1m_tokens`: price per 1M input tokens (USD)
- `output_cost_per_1m_tokens`: price per 1M output tokens (USD)

## Interaction flow

1. Harness starts the target environment and calls `/model` to select a model.
2. Harness calls `/chat` to send the prompt; the agent starts the attack workflow.
3. Harness polls `/result` and receives progress and resource usage (time, tokens, cost).
4. Harness verifies flags and records metrics.
5. Harness calls `/stop`; the agent cleans up and gets ready for the next task.

## Implementation notes

- Implement with Flask/FastAPI; use threads/async as needed.
- After `/model` and `/chat`, start the internal loop and stream/append logs to memory or file.
- `/result` should always return the latest `step/total` and real-time token stats; when done, include `flag` and `log`.
- `/stop` should terminate the current task and clean resources.
- Use high-precision timers for accurate duration.
- Maintain token usage and compute cost based on configured pricing.
- Always return fresh stats on each poll for real-time monitoring.

## Example (Flask)

```python
from flask import Flask, request, jsonify
import threading
import time

app = Flask(__name__)
current_task = {
    "flag": None, 
    "log": "",
    "start_time": None,
    "end_time": None,
    "total_tokens": 0,
    "total_cost": 0.0
}

@app.route('/model', methods=['POST'])
def set_model():
    model = request.json.get("model")
    # Set model logic
    return jsonify({"status": "ok"})

@app.route('/chat', methods=['POST'])
def chat():
    prompt = request.json.get("prompt")
    # Record start time
    current_task["start_time"] = time.time()
    current_task["total_tokens"] = 0
    current_task["total_cost"] = 0.0
    # Start a new thread to run agent task
    threading.Thread(target=run_agent, args=(prompt,)).start()
    return jsonify({"status": "ok"})

@app.route('/result', methods=['GET'])
def result():
    if current_task["flag"]:
        duration = current_task["end_time"] - current_task["start_time"] if current_task["end_time"] else 0
        return jsonify({
            **current_task,
            "duration": round(duration, 2),
            "total_cost": round(current_task["total_cost"], 6)
        })
    else:
        # In progress: return real-time stats
        duration = time.time() - current_task["start_time"] if current_task["start_time"] else 0
        return jsonify({
            "step": current_task.get("step", 0),
            "total": current_task.get("total", 100),
            "duration": round(duration, 2),
            "total_tokens": current_task.get("total_tokens", 0),
            "total_cost": round(current_task.get("total_cost", 0.0), 6)
        })

@app.route('/stop', methods=['POST'])
def stop():
    # Stop logic
    return jsonify({"status": "ok"})

def run_agent(prompt):
    # Pseudocode: perform attack, find flag, append logs
    current_task["log"] += f"prompt: {prompt}\n"
    # ... attack workflow ...
    current_task["flag"] = "flag{example}"
    current_task["log"] += "flag found!\n"
    current_task["end_time"] = time.time()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)
```

---

## Other Notes

- The agent server must ensure idempotent and robust APIs that can be invoked multiple times.
- It is recommended that logs are plain text for easy storage by the bench side.
- The flag format must match the target environment (flag{...}, 30 characters).
- Support scalability for multiple models and multiple tasks.
- Use high-precision timestamps for accurate timing.
- Token statistics should be updated in real time, and cost should be calculated based on configured pricing.
- Always return the latest statistics on each poll so the bench can monitor resource usage and cost in real time.
- For third-party APIs that do not provide token statistics, the system should display a warning but continue task execution.

---

If you have special requirements (such as WebSocket or asynchronous push), you can extend on this basis.
