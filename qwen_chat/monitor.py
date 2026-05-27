import time
import tkinter as tk

import psutil
from pynvml import (
    NVMLError,
    nvmlDeviceGetHandleByIndex,
    nvmlDeviceGetMemoryInfo,
    nvmlDeviceGetName,
    nvmlDeviceGetUtilizationRates,
    nvmlInit,
    nvmlShutdown,
)


# How often the window checks GPU and memory usage, in milliseconds.
UPDATE_INTERVAL_MS = 1000

# How many seconds of history to show on the chart.
MAX_HISTORY_SECONDS = 120


class ResourceMonitor:
    """
    A small popup window that shows GPU and memory usage over time.

    This program is intentionally simple:
    - Tkinter creates the window.
    - A Canvas draws the chart.
    - psutil reads normal computer memory usage.
    - pynvml reads NVIDIA GPU usage.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Qwen Model Resource Monitor")
        self.root.geometry("900x520")
        self.root.minsize(700, 420)

        self.start_time = time.time()
        self.samples = []

        self.gpu_available = False
        self.gpu_name = "NVIDIA GPU not available"
        self.gpu_handle = None

        self._setup_gpu()
        self._build_window()
        self._update()

    def _setup_gpu(self):
        """Connect to the first NVIDIA GPU if one is available."""
        try:
            nvmlInit()
            self.gpu_handle = nvmlDeviceGetHandleByIndex(0)
            gpu_name = nvmlDeviceGetName(self.gpu_handle)

            if isinstance(gpu_name, bytes):
                gpu_name = gpu_name.decode("utf-8")

            self.gpu_name = gpu_name
            self.gpu_available = True
        except NVMLError:
            self.gpu_available = False

    def _build_window(self):
        """Create the text labels and chart area."""
        self.title_label = tk.Label(
            self.root,
            text="Qwen / Ollama GPU and Memory Monitor",
            font=("Arial", 16, "bold"),
        )
        self.title_label.pack(pady=(12, 4))

        self.status_label = tk.Label(
            self.root,
            text=f"GPU: {self.gpu_name}",
            font=("Arial", 10),
        )
        self.status_label.pack(pady=(0, 8))

        self.current_label = tk.Label(
            self.root,
            text="Collecting data...",
            font=("Consolas", 10),
        )
        self.current_label.pack(pady=(0, 8))

        self.canvas = tk.Canvas(self.root, bg="white", highlightthickness=1)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _read_stats(self):
        """
        Read current GPU and memory usage.

        All chart values are percentages from 0 to 100, which makes them easy
        to draw on the same chart.
        """
        elapsed_seconds = int(time.time() - self.start_time)

        ram = psutil.virtual_memory()
        ram_percent = ram.percent
        ram_used_gb = ram.used / (1024 ** 3)
        ram_total_gb = ram.total / (1024 ** 3)

        gpu_util_percent = 0
        gpu_memory_percent = 0
        gpu_memory_used_gb = 0
        gpu_memory_total_gb = 0

        if self.gpu_available:
            try:
                utilization = nvmlDeviceGetUtilizationRates(self.gpu_handle)
                memory = nvmlDeviceGetMemoryInfo(self.gpu_handle)

                gpu_util_percent = utilization.gpu
                gpu_memory_used_gb = memory.used / (1024 ** 3)
                gpu_memory_total_gb = memory.total / (1024 ** 3)
                gpu_memory_percent = (memory.used / memory.total) * 100
            except NVMLError:
                self.gpu_available = False

        return {
            "time": elapsed_seconds,
            "gpu_util": gpu_util_percent,
            "gpu_memory": gpu_memory_percent,
            "gpu_memory_used_gb": gpu_memory_used_gb,
            "gpu_memory_total_gb": gpu_memory_total_gb,
            "ram": ram_percent,
            "ram_used_gb": ram_used_gb,
            "ram_total_gb": ram_total_gb,
        }

    def _update(self):
        """Collect one new sample, redraw the chart, then schedule the next update."""
        sample = self._read_stats()
        self.samples.append(sample)
        self.samples = self.samples[-MAX_HISTORY_SECONDS:]

        self._draw_chart()
        self.root.after(UPDATE_INTERVAL_MS, self._update)

    def _draw_chart(self):
        """Draw the chart, legend, and current numbers."""
        self.canvas.delete("all")

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width < 50 or height < 50:
            return

        left = 55
        right = width - 25
        top = 25
        bottom = height - 45

        latest = self.samples[-1]
        self.current_label.config(
            text=(
                f"GPU: {latest['gpu_util']:5.1f}%   "
                f"VRAM: {latest['gpu_memory']:5.1f}% "
                f"({latest['gpu_memory_used_gb']:.1f}/"
                f"{latest['gpu_memory_total_gb']:.1f} GB)   "
                f"RAM: {latest['ram']:5.1f}% "
                f"({latest['ram_used_gb']:.1f}/"
                f"{latest['ram_total_gb']:.1f} GB)"
            )
        )

        self._draw_axes(left, right, top, bottom)
        self._draw_line("gpu_util", "red", left, right, top, bottom)
        self._draw_line("gpu_memory", "blue", left, right, top, bottom)
        self._draw_line("ram", "green", left, right, top, bottom)
        self._draw_legend(left, top)

    def _draw_axes(self, left, right, top, bottom):
        """Draw a simple 0 to 100 percent chart background."""
        self.canvas.create_line(left, bottom, right, bottom, fill="black")
        self.canvas.create_line(left, top, left, bottom, fill="black")

        for percent in [0, 25, 50, 75, 100]:
            y = bottom - ((percent / 100) * (bottom - top))
            self.canvas.create_line(left, y, right, y, fill="#eeeeee")
            self.canvas.create_text(
                left - 10,
                y,
                text=f"{percent}%",
                anchor="e",
                font=("Arial", 8),
            )

        self.canvas.create_text(
            (left + right) / 2,
            bottom + 28,
            text=f"Last {MAX_HISTORY_SECONDS} seconds, updated every 1 second",
            font=("Arial", 9),
        )

    def _draw_line(self, key, color, left, right, top, bottom):
        """Draw one usage line on the chart."""
        if len(self.samples) < 2:
            return

        chart_width = right - left
        chart_height = bottom - top
        point_count = max(1, len(self.samples) - 1)
        points = []

        for index, sample in enumerate(self.samples):
            x = left + (index / point_count) * chart_width
            y = bottom - (sample[key] / 100) * chart_height
            points.extend([x, y])

        self.canvas.create_line(points, fill=color, width=2, smooth=True)

    def _draw_legend(self, left, top):
        """Draw labels for the colored lines."""
        items = [
            ("GPU usage", "red"),
            ("GPU memory", "blue"),
            ("System RAM", "green"),
        ]

        x = left + 10
        y = top + 10

        for text, color in items:
            self.canvas.create_line(x, y, x + 24, y, fill=color, width=3)
            self.canvas.create_text(x + 32, y, text=text, anchor="w", font=("Arial", 9))
            x += 150

    def _close(self):
        """Close the monitor window cleanly."""
        if self.gpu_available:
            try:
                nvmlShutdown()
            except NVMLError:
                pass

        self.root.destroy()


def main():
    root = tk.Tk()
    ResourceMonitor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
