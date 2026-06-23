import os
import logging
from typing import Dict, Any, List

# Ensure target logs directory exists in the workspace
os.makedirs("logs", exist_ok=True)

# Define audit logger instances
audit_logger = logging.getLogger("EcoGuardAI_Audit")
audit_logger.setLevel(logging.INFO)

# Setup a clean file handler for the immutable audit trace log if not already added
if not audit_logger.handlers:
    file_handler = logging.FileHandler("logs/audit.log", encoding="utf-8")
    # Prefix logs with [AUDIT] tag for easy log parser extraction
    formatter = logging.Formatter("[AUDIT] %(asctime)s - %(message)s")
    file_handler.setFormatter(formatter)
    audit_logger.addHandler(file_handler)

def log_agent_action(agent_name: str, action: str, details: str = "") -> None:
    """
    Records operations performed by specific agents during system execution.
    Helps monitor agent-to-agent delegation traces.
    """
    msg = f"Agent='{agent_name}' | Action='{action}' | Details='{details}'"
    audit_logger.info(msg)

def log_compliance_check(session_id: str, status: str, metrics: Dict[str, float]) -> None:
    """
    Logs the starting of a CPCB compliance evaluation and its result status.
    """
    msg = f"SessionID='{session_id}' | ComplianceCheckStatus='{status}' | Metrics={metrics}"
    audit_logger.info(msg)

def log_alert_dispatched(severity: str, params: List[str], details: str) -> None:
    """
    Logs emergency alarm dispatch records for CPCB violations.
    """
    msg = f"AlertState='DISPATCHED' | Severity='{severity}' | ViolatingParameters={params} | Details='{details}'"
    audit_logger.info(msg)

def log_security_violation(violation_type: str, details: str) -> None:
    """
    Logs pre-flight input validation errors and prompt injection detections.
    Uses WARNING priority to highlight potential safety threats.
    """
    msg = f"SecurityViolation='{violation_type}' | Details='{details}'"
    audit_logger.warning(msg)
