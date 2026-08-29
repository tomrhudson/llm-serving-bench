from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass, field


REMOTE_COMMAND = (
    "free -b; "
    "nvidia-smi --query-gpu=utilization.gpu,temperature.gpu,power.draw "
    "--format=csv,noheader,nounits 2>/dev/null || true"
)


@dataclass
class HostMonitor:
    hosts: dict[str, str]
    interval: float = 5.0
    samples: list[dict[str, object]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self.hosts:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.interval + 10)

    def _sample(self, label: str, target: str) -> dict[str, object]:
        sample: dict[str, object] = {"time": time.time(), "host": label}
        try:
            result = subprocess.run(
                ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4",
                 target, REMOTE_COMMAND],
                check=False, capture_output=True, text=True, timeout=10,
            )
            lines = result.stdout.splitlines()
            mem_line = next((line for line in lines if line.startswith("Mem:")), None)
            swap_line = next((line for line in lines if line.startswith("Swap:")), None)
            if mem_line:
                fields = mem_line.split()
                sample.update({
                    "mem_total_bytes": int(fields[1]),
                    "mem_used_bytes": int(fields[2]),
                    "mem_available_bytes": int(fields[6]),
                })
            if swap_line:
                sample["swap_used_bytes"] = int(swap_line.split()[2])
            gpu_line = next(
                (line for line in reversed(lines)
                 if line.count(",") >= 2 and not line.startswith(("Mem:", "Swap:"))),
                None,
            )
            if gpu_line:
                gpu = [part.strip() for part in gpu_line.split(",")]
                sample["gpu_util_pct"] = _number(gpu[0])
                sample["gpu_temp_c"] = _number(gpu[1])
                sample["gpu_power_w"] = _number(gpu[2])
            if result.returncode:
                sample["error"] = f"ssh exit {result.returncode}"
        except Exception as exc:
            sample["error"] = f"{type(exc).__name__}: {exc}"
        return sample

    def _run(self) -> None:
        while not self._stop.is_set():
            started = time.monotonic()
            for label, target in self.hosts.items():
                self.samples.append(self._sample(label, target))
            elapsed = time.monotonic() - started
            self._stop.wait(max(0.1, self.interval - elapsed))


def _number(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None
