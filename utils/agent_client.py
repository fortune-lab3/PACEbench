import requests
import time
from rich.progress import Progress

class AgentClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')

    def set_model(self, model):
        resp = requests.post(f"{self.base_url}/model", json={"model": model})
        resp.raise_for_status()
        return resp.json()

    def send_prompt(self, prompt):
        resp = requests.post(f"{self.base_url}/chat", json={"prompt": prompt})
        resp.raise_for_status()
        return resp.json()

    def get_result(self, timeout=300, interval=2):
        start = time.time()
        while time.time() - start < timeout:
            resp = requests.get(f"{self.base_url}/result")
            if resp.status_code == 200:
                data = resp.json()
                if "flag" in data:
                    return data
            time.sleep(interval)
        return {"flag": "Fail", "log": "Timeout"}

    def get_result_with_progress(self, total=100, interval=0.5):
        with Progress(transient=True) as progress:
            task = progress.add_task("Agent Progress", total=total)
            last_step = 0
            # Persist the latest valid stats to avoid None when final result lacks fields
            last_stats = {
                "duration": None,
                "total_tokens": None,
                "total_cost": None,
                "logfile": None,
            }
            while True:
                resp = requests.get(f"{self.base_url}/result")
                if resp.status_code == 200:
                    data = resp.json()
                    step = data.get("step", last_step)
                    # If server provides total, align the progress bar; otherwise use provided total
                    srv_total = data.get("total")
                    if isinstance(srv_total, (int, float)) and srv_total > 0:
                        progress.update(task, total=srv_total)
                    # Avoid early completion interfering with polling
                    try:
                        current_total = progress.tasks[0].total
                    except Exception:
                        current_total = total
                    progress.update(task, completed=min(step, current_total if current_total else step))

                    # Accumulate latest stats when present; only overwrite logfile when non-empty
                    if data.get("duration") is not None:
                        last_stats["duration"] = data.get("duration")
                    if data.get("total_tokens") is not None:
                        last_stats["total_tokens"] = data.get("total_tokens")
                    if data.get("total_cost") is not None:
                        last_stats["total_cost"] = data.get("total_cost")
                    lf = data.get("logfile")
                    if lf:
                        last_stats["logfile"] = lf

                    # Print stats only when step changes
                    if step != last_step:
                        duration = data.get('duration', last_stats.get('duration'))
                        total_tokens = data.get('total_tokens', last_stats.get('total_tokens'))
                        total_cost = data.get('total_cost', last_stats.get('total_cost'))

                        if duration is not None or total_tokens is not None or total_cost is not None:
                            stats_info = []
                            if duration is not None:
                                try:
                                    stats_info.append(f"Duration: {float(duration):.2f}s")
                                except Exception:
                                    stats_info.append(f"Duration: {duration}s")
                            if total_tokens is not None:
                                stats_info.append(f"Token: {total_tokens}")
                            if total_cost is not None:
                                try:
                                    stats_info.append(f"Cost: ${float(total_cost):.6f}")
                                except Exception:
                                    stats_info.append(f"Cost: ${total_cost}")
                            if stats_info:
                                progress.print(f"📊 Stats: {' | '.join(stats_info)}")

                        last_step = step

                    # Completed when either flag or report appears
                    if ("flag" in data) or ("report" in data):
                        final = dict(data)
                        for k, v in last_stats.items():
                            if final.get(k) in (None, "") and v not in (None, ""):
                                final[k] = v
                        return final
                time.sleep(interval)

    def stop(self):
        resp = requests.post(f"{self.base_url}/stop")
        resp.raise_for_status()
        return resp.json() 