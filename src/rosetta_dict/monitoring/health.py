"""Health check system for monitoring pipeline status."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class HealthCheck:
    """Health check system for production monitoring."""

    def __init__(self, project_root: Path = None):
        """Initialize health checker.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root or Path.cwd()
        self.data_dir = self.project_root / "data"

    def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check.

        Returns:
            Health status dictionary
        """
        logger.info("Running health checks...")

        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "version": "0.1.0"
        }

        # Check data directories
        health["checks"]["data_directories"] = self._check_data_directories()

        # Check pipeline outputs
        health["checks"]["pipeline_outputs"] = self._check_pipeline_outputs()

        # Check data quality
        health["checks"]["data_quality"] = self._check_data_quality()

        # Determine overall status
        failed_checks = [
            name for name, check in health["checks"].items()
            if check["status"] != "healthy"
        ]

        if failed_checks:
            health["status"] = "unhealthy"
            health["failed_checks"] = failed_checks
            logger.warning(f"Health check FAILED: {failed_checks}")
        else:
            logger.info("Health check PASSED")

        return health

    def _check_data_directories(self) -> Dict[str, Any]:
        """Check that required data directories exist."""
        required_dirs = [
            "data/01_raw",
            "data/02_intermediate",
            "data/03_primary",
            "data/06_metrics",
            "data/08_reporting"
        ]

        missing_dirs = []
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)

        if missing_dirs:
            return {
                "status": "unhealthy",
                "message": f"Missing directories: {missing_dirs}"
            }

        return {
            "status": "healthy",
            "message": "All required directories exist"
        }

    def _check_pipeline_outputs(self) -> Dict[str, Any]:
        """Check that pipeline has generated expected outputs."""
        expected_files = {
            "enriched_entries": "data/03_primary/enriched_entries.parquet",
            "final_dictionary": "data/08_reporting/dictionary_v1.json"
        }

        missing_files = {}
        file_ages = {}

        for name, file_path in expected_files.items():
            full_path = self.project_root / file_path

            if not full_path.exists():
                missing_files[name] = file_path
            else:
                # Check file age
                mtime = full_path.stat().st_mtime
                age_hours = (datetime.now().timestamp() - mtime) / 3600
                file_ages[name] = age_hours

        if missing_files:
            return {
                "status": "unhealthy",
                "message": f"Missing output files: {list(missing_files.keys())}"
            }

        # Warn if files are very old (> 7 days)
        stale_files = {
            name: age for name, age in file_ages.items()
            if age > 168  # 7 days
        }

        if stale_files:
            return {
                "status": "degraded",
                "message": f"Stale files (>7 days old): {list(stale_files.keys())}",
                "file_ages_hours": file_ages
            }

        return {
            "status": "healthy",
            "message": "All pipeline outputs present and fresh",
            "file_ages_hours": file_ages
        }

    def _check_data_quality(self) -> Dict[str, Any]:
        """Check data quality metrics."""
        quality_report_path = self.data_dir / "06_metrics" / "data_quality_report.json"

        if not quality_report_path.exists():
            return {
                "status": "unknown",
                "message": "Data quality report not found"
            }

        try:
            with open(quality_report_path, 'r') as f:
                quality_report = json.load(f)

            # Check quality score
            quality_score = quality_report.get("overall_quality_score", 0)

            if quality_score >= 75:
                status = "healthy"
            elif quality_score >= 60:
                status = "degraded"
            else:
                status = "unhealthy"

            return {
                "status": status,
                "quality_score": quality_score,
                "verdict": quality_report.get("verdict", "UNKNOWN"),
                "issues": len(quality_report.get("issues", []))
            }

        except Exception as e:
            logger.error(f"Error reading quality report: {e}")
            return {
                "status": "unknown",
                "message": f"Error reading quality report: {e}"
            }

    def healthz(self) -> bool:
        """Simple health check endpoint for load balancers.

        Returns:
            True if healthy, False otherwise
        """
        health = self.check_health()
        return health["status"] == "healthy"
