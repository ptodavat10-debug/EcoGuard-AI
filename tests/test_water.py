import pytest
import json
from mcp_server import get_water_quality, check_cpcb_compliance
from agents.water_monitor_agent import water_monitor_agent

def test_water_sensor_fetching():
    """Verify that water quality metrics can be fetched in JSON format."""
    res_str = get_water_quality()
    data = json.loads(res_str)
    assert "pH" in data
    assert "BOD" in data
    assert "COD" in data
    assert "Heavy Metals" in data

def test_water_compliance_pass():
    """Verify that compliant water metrics result in a PASS status."""
    normal_water = json.dumps({
        "pH": 7.2,
        "BOD": 15.0,
        "COD": 120.0,
        "Heavy Metals": 0.05
    })
    res_str = check_cpcb_compliance(water_json=normal_water)
    data = json.loads(res_str)
    assert data["compliant"] is True
    assert data["water_assessment"]["pH"]["status"] == "PASS"
    assert data["water_assessment"]["BOD"]["status"] == "PASS"

def test_water_compliance_fail():
    """Verify that non-compliant water metrics result in a FAIL status."""
    violated_water = json.dumps({
        "pH": 11.0,  # exceeds 8.5
        "BOD": 45.0,  # exceeds 30.0
        "COD": 300.0, # exceeds 250.0
        "Heavy Metals": 0.5 # exceeds 0.1
    })
    res_str = check_cpcb_compliance(water_json=violated_water)
    data = json.loads(res_str)
    assert data["compliant"] is False
    assert data["status"] == "NON-COMPLIANT"
    assert len(data["violations"]) >= 4
    assert data["water_assessment"]["pH"]["status"] == "FAIL"

def test_agent_config():
    """Verify that the WaterMonitor Agent is configured correctly with tools."""
    assert water_monitor_agent.name == "WaterMonitor"
    assert len(water_monitor_agent.tools) == 2
