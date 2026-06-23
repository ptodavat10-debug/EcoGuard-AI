import pytest
import json
import os
from mcp_server import check_cpcb_compliance

def test_full_cpcb_compliance_engine():
    """Verify that the central compliance checking engine outputs valid JSON."""
    res_str = check_cpcb_compliance()
    data = json.loads(res_str)
    
    assert "status" in data
    assert "compliant" in data
    assert "violations" in data
    assert "water_assessment" in data
    assert "air_assessment" in data

def test_cpcb_limits_compliance():
    """Verify standard PASS case outputs compliant=True and empty violations."""
    clean_water = json.dumps({"pH": 7.0, "BOD": 5.0, "COD": 50.0, "Heavy Metals": 0.01})
    clean_air = json.dumps({"SO2": 20.0, "NOx": 20.0, "PM2.5": 10.0, "CO2": 380.0})
    
    res_str = check_cpcb_compliance(water_json=clean_water, air_json=clean_air)
    data = json.loads(res_str)
    
    assert data["compliant"] is True
    assert data["status"] == "COMPLIANT"
    assert len(data["violations"]) == 0

def test_cpcb_limits_non_compliance():
    """Verify non-compliant case lists correct violating parameters."""
    bad_water = json.dumps({"pH": 4.5, "BOD": 45.0})  # pH acid, BOD high
    bad_air = json.dumps({"PM2.5": 90.0})             # PM2.5 high
    
    res_str = check_cpcb_compliance(water_json=bad_water, air_json=bad_air)
    data = json.loads(res_str)
    
    assert data["compliant"] is False
    assert data["status"] == "NON-COMPLIANT"
    assert len(data["violations"]) == 3  # pH, BOD, PM2.5
    
    # Audit log check
    assert os.path.exists("logs/audit.log")
