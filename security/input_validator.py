import logging
from typing import Dict, Any, Tuple

# Setup local logger
logger = logging.getLogger("EcoGuardAI.Security.InputValidator")

def validate_metrics(metrics: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validates input sensor readings for water and air pollution parameters against physical boundaries.
    Rejects impossible values (e.g. negative concentrations, pH outside 0-14).
    
    Args:
        metrics (Dict[str, Any]): Dictionary containing sensor readings.
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    required_keys = ["pH", "BOD", "COD", "Heavy Metals", "SO2", "NOx", "PM2.5", "CO2"]
    
    # Check for missing parameters
    for key in required_keys:
        if key not in metrics:
            msg = f"Missing required parameter: '{key}'"
            logger.error(msg)
            return False, msg
        
        # Validate that the values are numeric
        try:
            metrics[key] = float(metrics[key])
        except (ValueError, TypeError):
            msg = f"Parameter '{key}' must be a numeric value, got '{metrics[key]}'."
            logger.error(msg)
            return False, msg

    # Validate Wastewater Parameters
    ph = metrics["pH"]
    if not (0.0 <= ph <= 14.0):
        msg = f"Impossible water pH value: {ph}. Value must be between 0.0 and 14.0."
        logger.error(msg)
        return False, msg
        
    for water_param in ["BOD", "COD", "Heavy Metals"]:
        val = metrics[water_param]
        if val < 0.0:
            msg = f"Impossible wastewater parameter value: {water_param}={val} mg/L. Value cannot be negative."
            logger.error(msg)
            return False, msg
            
    # Validate Air Emissions Parameters
    for air_param in ["SO2", "NOx", "PM2.5", "CO2"]:
        val = metrics[air_param]
        if val < 0.0:
            msg = f"Impossible air emissions parameter value: {air_param}={val}. Value cannot be negative."
            logger.error(msg)
            return False, msg

    logger.info("All input metrics successfully validated.")
    return True, ""
