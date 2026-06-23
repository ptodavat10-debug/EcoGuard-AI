import os
import json
import logging
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

from config import CPCB_LIMITS
from security.input_validator import validate_metrics
from security.audit_logger import log_agent_action, log_compliance_check, log_alert_dispatched, log_security_violation

# Setup logger for MCP
logger = logging.getLogger("EcoGuardAI.MCP")

# Initialize FastMCP Server
mcp = FastMCP("EcoGuardAI_MCP_Server")

# Path to the shared sensor readings file
READINGS_FILE = "cpcb_sensor_readings.json"

DEFAULT_READINGS = {
    "pH": 7.2,
    "BOD": 15.0,
    "COD": 120.0,
    "Heavy Metals": 0.05,
    "SO2": 35.0,
    "NOx": 40.0,
    "PM2.5": 28.0,
    "CO2": 420.0
}

def load_sensor_readings() -> Dict[str, float]:
    """
    Helper function to load the current sensor readings from the shared JSON file.
    Creates default readings if the file does not exist.
    """
    if not os.path.exists(READINGS_FILE):
        with open(READINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_READINGS, f, indent=4)
        return DEFAULT_READINGS
    try:
        with open(READINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Populate defaults for any missing keys
            for k, v in DEFAULT_READINGS.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        logger.error(f"Error loading sensor readings file: {e}")
        return DEFAULT_READINGS

def save_sensor_readings(readings: Dict[str, float]) -> None:
    """
    Helper function to save updated sensor readings to the shared JSON file.
    This is called by the UI when sliders are moved.
    """
    try:
        with open(READINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(readings, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving sensor readings: {e}")

@mcp.tool()
def get_water_quality() -> str:
    """
    Fetches the current industrial wastewater quality sensor readings.
    
    Returns:
        str: JSON-formatted string of water quality parameters:
            - pH
            - BOD (Biochemical Oxygen Demand) in mg/L
            - COD (Chemical Oxygen Demand) in mg/L
            - Heavy Metals in mg/L
    """
    log_agent_action("MCPServer", "get_water_quality", "Reading sensor file")
    readings = load_sensor_readings()
    water_data = {
        "pH": readings.get("pH"),
        "BOD": readings.get("BOD"),
        "COD": readings.get("COD"),
        "Heavy Metals": readings.get("Heavy Metals")
    }
    return json.dumps(water_data, indent=4)

@mcp.tool()
def get_air_emissions() -> str:
    """
    Fetches the current industrial stack and ambient air emissions sensor readings.
    
    Returns:
        str: JSON-formatted string of air emissions parameters:
            - SO2 (Sulfur Dioxide) in µg/m³
            - NOx (Nitrogen Oxides) in µg/m³
            - PM2.5 (Particulate Matter 2.5) in µg/m³
            - CO2 (Carbon Dioxide) in ppm
    """
    log_agent_action("MCPServer", "get_air_emissions", "Reading sensor file")
    readings = load_sensor_readings()
    air_data = {
        "SO2": readings.get("SO2"),
        "NOx": readings.get("NOx"),
        "PM2.5": readings.get("PM2.5"),
        "CO2": readings.get("CO2")
    }
    return json.dumps(air_data, indent=4)

@mcp.tool()
def check_cpcb_compliance(water_json: Optional[str] = None, air_json: Optional[str] = None) -> str:
    """
    Evaluates sensor readings against official CPCB limits. Uses input validation to reject invalid numbers.
    
    Args:
        water_json (str, optional): JSON string containing water parameters to override.
        air_json (str, optional): JSON string containing air parameters to override.
        
    Returns:
        str: JSON compliance evaluation report.
    """
    log_agent_action("MCPServer", "check_cpcb_compliance", "Starting compliance checks")
    
    # Load current sensor metrics
    current_readings = load_sensor_readings()
    eval_metrics = current_readings.copy()
    
    # Apply wastewater overrides if provided
    if water_json:
        try:
            w_override = json.loads(water_json)
            eval_metrics.update({k: w_override[k] for k in ["pH", "BOD", "COD", "Heavy Metals"] if k in w_override})
        except Exception as e:
            msg = f"Failed to parse water override JSON: {e}"
            log_security_violation("JSON_PARSE_ERROR", msg)
            return json.dumps({"error": msg, "compliant": False})
            
    # Apply air emissions overrides if provided
    if air_json:
        try:
            a_override = json.loads(air_json)
            eval_metrics.update({k: a_override[k] for k in ["SO2", "NOx", "PM2.5", "CO2"] if k in a_override})
        except Exception as e:
            msg = f"Failed to parse air override JSON: {e}"
            log_security_violation("JSON_PARSE_ERROR", msg)
            return json.dumps({"error": msg, "compliant": False})

    # Perform security input validation check
    is_valid, error_msg = validate_metrics(eval_metrics)
    if not is_valid:
        log_security_violation("METRICS_VALIDATION_FAILED", error_msg)
        return json.dumps({"error": f"Security validation rejected: {error_msg}", "compliant": False})

    # Evaluate compliance boundaries
    water_limits = CPCB_LIMITS["water"]
    air_limits = CPCB_LIMITS["air"]
    
    violations = []
    water_status = {}
    air_status = {}
    
    # Wastewater limits evaluation
    ph = eval_metrics["pH"]
    ph_ok = water_limits["ph_min"] <= ph <= water_limits["ph_max"]
    water_status["pH"] = {
        "value": ph,
        "limit": f"{water_limits['ph_min']}-{water_limits['ph_max']}",
        "status": "PASS" if ph_ok else "FAIL"
    }
    if not ph_ok:
        violations.append(f"pH out of range ({ph})")
        
    for k, limit_key in [("BOD", "bod_max"), ("COD", "cod_max"), ("Heavy Metals", "heavy_metals_max")]:
        val = eval_metrics[k]
        limit_val = water_limits[limit_key]
        ok = val <= limit_val
        water_status[k] = {
            "value": val,
            "limit": f"<= {limit_val}",
            "status": "PASS" if ok else "FAIL"
        }
        if not ok:
            violations.append(f"{k} exceeds standard ({val} > {limit_val} mg/L)")
            
    # Air emissions limits evaluation
    for k, limit_key in [("SO2", "so2_max"), ("NOx", "nox_max"), ("PM2.5", "pm25_max"), ("CO2", "co2_max")]:
        val = eval_metrics[k]
        limit_val = air_limits[limit_key]
        ok = val <= limit_val
        air_status[k] = {
            "value": val,
            "limit": f"<= {limit_val}",
            "status": "PASS" if ok else "FAIL"
        }
        if not ok:
            violations.append(f"{k} exceeds standard ({val} > {limit_val})")

    compliant = len(violations) == 0
    status_str = "COMPLIANT" if compliant else "NON-COMPLIANT"
    
    # Audit logging execution
    log_compliance_check("mcp-server-session", status_str, eval_metrics)
    if not compliant:
        log_alert_dispatched("WARNING", [v.split()[0] for v in violations], f"Violating parameters detected: {violations}")

    # Formulate CPCB compliance payload
    report = {
        "status": status_str,
        "compliant": compliant,
        "violations": violations,
        "water_assessment": water_status,
        "air_assessment": air_status
    }
    return json.dumps(report, indent=4)

if __name__ == "__main__":
    # Launch stdio server mode (used for standard MCP client discovery)
    mcp.run()
