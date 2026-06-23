import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Gemini configuration
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# CPCB Compliance Standards
# General standards for industrial wastewater effluent discharge and ambient/stack air quality.
CPCB_LIMITS = {
    "water": {
        "ph_min": 6.5,
        "ph_max": 8.5,
        "bod_max": 30.0,          # mg/L (Biochemical Oxygen Demand)
        "cod_max": 250.0,         # mg/L (Chemical Oxygen Demand)
        "heavy_metals_max": 0.1   # mg/L (Total toxic heavy metals)
    },
    "air": {
        "so2_max": 80.0,          # µg/m³ (Sulfur Dioxide)
        "nox_max": 80.0,          # µg/m³ (Nitrogen Oxides)
        "pm25_max": 60.0,         # µg/m³ (PM2.5)
        "co2_max": 1000.0         # ppm (Carbon Dioxide)
    }
}

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("EcoGuardAI")
