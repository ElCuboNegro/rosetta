"""Alert management system for production monitoring."""

import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert:
    """Represents a single alert."""

    def __init__(
        self,
        name: str,
        severity: AlertSeverity,
        message: str,
        context: Dict[str, Any] = None
    ):
        """Initialize alert.

        Args:
            name: Alert name
            severity: Alert severity
            message: Alert message
            context: Additional context
        """
        self.name = name
        self.severity = severity
        self.message = message
        self.context = context or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary.

        Returns:
            Alert as dictionary
        """
        return {
            "name": self.name,
            "severity": self.severity.value,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }


class AlertManager:
    """Manage alerts and notifications."""

    def __init__(self):
        """Initialize alert manager."""
        self.alerts = []
        self.alert_handlers = []

    def register_handler(self, handler: Callable[[Alert], None]):
        """Register an alert handler.

        Args:
            handler: Callable that handles alerts
        """
        self.alert_handlers.append(handler)
        logger.info(f"Registered alert handler: {handler.__name__}")

    def fire_alert(
        self,
        name: str,
        severity: AlertSeverity,
        message: str,
        context: Dict[str, Any] = None
    ):
        """Fire an alert.

        Args:
            name: Alert name
            severity: Alert severity
            message: Alert message
            context: Additional context
        """
        alert = Alert(name, severity, message, context)
        self.alerts.append(alert)

        # Log alert
        log_func = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.CRITICAL: logger.critical
        }[severity]

        log_func(f"ALERT [{severity.value.upper()}] {name}: {message}")

        # Call handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler {handler.__name__}: {e}")

    def get_active_alerts(self, min_severity: AlertSeverity = None) -> List[Alert]:
        """Get active alerts.

        Args:
            min_severity: Minimum severity to include

        Returns:
            List of active alerts
        """
        if min_severity is None:
            return self.alerts

        severity_order = [
            AlertSeverity.INFO,
            AlertSeverity.WARNING,
            AlertSeverity.ERROR,
            AlertSeverity.CRITICAL
        ]

        min_level = severity_order.index(min_severity)

        return [
            alert for alert in self.alerts
            if severity_order.index(alert.severity) >= min_level
        ]

    def clear_alerts(self):
        """Clear all alerts."""
        self.alerts = []
        logger.info("All alerts cleared")

    def save_alerts(self, output_path: Path):
        """Save alerts to file.

        Args:
            output_path: Path to save alerts
        """
        alerts_data = {
            "timestamp": datetime.now().isoformat(),
            "count": len(self.alerts),
            "alerts": [alert.to_dict() for alert in self.alerts]
        }

        with open(output_path, 'w') as f:
            json.dump(alerts_data, f, indent=2)

        logger.info(f"Alerts saved to {output_path}")


# Default alert handlers

def log_alert_handler(alert: Alert):
    """Log alert to standard logger."""
    pass  # Already logged in fire_alert


def file_alert_handler(output_dir: Path):
    """Create file-based alert handler.

    Args:
        output_dir: Directory to write alert files

    Returns:
        Alert handler function
    """
    def handler(alert: Alert):
        """Write alert to file."""
        alert_file = output_dir / f"alert_{alert.timestamp.strftime('%Y%m%d_%H%M%S')}_{alert.name}.json"

        with open(alert_file, 'w') as f:
            json.dump(alert.to_dict(), f, indent=2)

    return handler


# Global alert manager instance
_alert_manager = AlertManager()


def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance.

    Returns:
        AlertManager instance
    """
    return _alert_manager


# Alert rule definitions

class AlertRules:
    """Predefined alert rules for common conditions."""

    @staticmethod
    def check_data_quality(quality_score: float, alert_manager: AlertManager):
        """Check data quality and fire alerts if needed.

        Args:
            quality_score: Quality score (0-100)
            alert_manager: AlertManager instance
        """
        if quality_score < 60:
            alert_manager.fire_alert(
                "data_quality_critical",
                AlertSeverity.CRITICAL,
                f"Data quality critically low: {quality_score:.1f}/100",
                {"quality_score": quality_score}
            )
        elif quality_score < 75:
            alert_manager.fire_alert(
                "data_quality_degraded",
                AlertSeverity.WARNING,
                f"Data quality degraded: {quality_score:.1f}/100",
                {"quality_score": quality_score}
            )

    @staticmethod
    def check_ipa_coverage(coverage_rate: float, alert_manager: AlertManager):
        """Check IPA coverage and fire alerts if needed.

        Args:
            coverage_rate: IPA coverage rate (0.0-1.0)
            alert_manager: AlertManager instance
        """
        if coverage_rate < 0.5:
            alert_manager.fire_alert(
                "ipa_coverage_critical",
                AlertSeverity.CRITICAL,
                f"Hebrew IPA coverage critically low: {coverage_rate:.1%}",
                {"coverage_rate": coverage_rate}
            )
        elif coverage_rate < 0.8:
            alert_manager.fire_alert(
                "ipa_coverage_low",
                AlertSeverity.WARNING,
                f"Hebrew IPA coverage below target: {coverage_rate:.1%}",
                {"coverage_rate": coverage_rate}
            )

    @staticmethod
    def check_duplicates(duplicate_count: int, total_count: int, alert_manager: AlertManager):
        """Check for duplicate alignments.

        Args:
            duplicate_count: Number of duplicates
            total_count: Total number of entries
            alert_manager: AlertManager instance
        """
        if duplicate_count > 0:
            dup_rate = duplicate_count / total_count if total_count > 0 else 0

            if dup_rate > 0.05:  # More than 5%
                alert_manager.fire_alert(
                    "high_duplicate_rate",
                    AlertSeverity.ERROR,
                    f"High duplicate rate: {duplicate_count} ({dup_rate:.1%})",
                    {"duplicate_count": duplicate_count, "duplicate_rate": dup_rate}
                )
            else:
                alert_manager.fire_alert(
                    "duplicates_found",
                    AlertSeverity.WARNING,
                    f"Duplicates found: {duplicate_count} ({dup_rate:.1%})",
                    {"duplicate_count": duplicate_count, "duplicate_rate": dup_rate}
                )

    @staticmethod
    def check_pipeline_performance(duration_seconds: float, alert_manager: AlertManager):
        """Check pipeline performance.

        Args:
            duration_seconds: Pipeline execution duration
            alert_manager: AlertManager instance
        """
        # Alert if pipeline takes longer than 30 minutes
        if duration_seconds > 1800:
            alert_manager.fire_alert(
                "slow_pipeline_execution",
                AlertSeverity.WARNING,
                f"Pipeline execution slow: {duration_seconds/60:.1f} minutes",
                {"duration_seconds": duration_seconds}
            )
