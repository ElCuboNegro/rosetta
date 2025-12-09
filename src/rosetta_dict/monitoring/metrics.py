"""Metrics collection for monitoring and observability."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collect and export metrics for monitoring."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = {}
        self.start_time = datetime.now()

    def record_metric(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a metric value.

        Args:
            name: Metric name
            value: Metric value
            labels: Optional labels/tags
        """
        if name not in self.metrics:
            self.metrics[name] = []

        self.metrics[name].append({
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "labels": labels or {}
        })

        logger.debug(f"Metric recorded: {name}={value} {labels}")

    def increment_counter(self, name: str, labels: Dict[str, str] = None):
        """Increment a counter metric.

        Args:
            name: Counter name
            labels: Optional labels/tags
        """
        current = self._get_counter_value(name, labels)
        self.record_metric(name, current + 1, labels)

    def _get_counter_value(self, name: str, labels: Dict[str, str] = None) -> float:
        """Get current counter value."""
        if name not in self.metrics:
            return 0

        # Find most recent value with matching labels
        for entry in reversed(self.metrics[name]):
            if entry["labels"] == (labels or {}):
                return entry["value"]

        return 0

    def record_duration(self, name: str, duration_seconds: float, labels: Dict[str, str] = None):
        """Record a duration metric.

        Args:
            name: Duration metric name
            duration_seconds: Duration in seconds
            labels: Optional labels/tags
        """
        self.record_metric(f"{name}_duration_seconds", duration_seconds, labels)

    def get_metrics(self) -> Dict[str, List[Dict]]:
        """Get all recorded metrics.

        Returns:
            Dictionary of metrics
        """
        return self.metrics

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics string
        """
        lines = []

        for metric_name, entries in self.metrics.items():
            if not entries:
                continue

            # Get most recent value for each label combination
            latest_values = {}

            for entry in entries:
                labels_key = json.dumps(entry["labels"], sort_keys=True)
                latest_values[labels_key] = entry

            # Format as Prometheus metrics
            for labels_key, entry in latest_values.items():
                labels_str = ""
                if entry["labels"]:
                    labels_list = [f'{k}="{v}"' for k, v in entry["labels"].items()]
                    labels_str = "{" + ",".join(labels_list) + "}"

                lines.append(f'{metric_name}{labels_str} {entry["value"]}')

        return "\n".join(lines)

    def export_json(self) -> str:
        """Export metrics as JSON.

        Returns:
            JSON-formatted metrics string
        """
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "metrics": self.metrics
        }

        return json.dumps(export_data, indent=2)

    def save_metrics(self, output_path: Path):
        """Save metrics to file.

        Args:
            output_path: Path to save metrics
        """
        with open(output_path, 'w') as f:
            f.write(self.export_json())

        logger.info(f"Metrics saved to {output_path}")


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance.

    Returns:
        MetricsCollector instance
    """
    return _metrics_collector
