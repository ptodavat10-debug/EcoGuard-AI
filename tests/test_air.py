import pytest
import json
from mcp_server import get_air_emissions, check_cpcb_compliance
from agents.air_monitor_agent import air_monitor_agent

def test_air_sensor_fetching():
    """Verify that air emissions metrics can be fetched in JSON format."""
    res_str = get_air_emissions()
    data = json.loads(res_str)
    assert "SO2" in data
    assert "NOx" in data
    assert "PM2.5" in data
    assert "CO2" in data

def test_air_compliance_pass():
    """Verify that compliant air metrics result in a PASS status."""
    normal_air = json.dumps({
        "SO2": 35.0,
        "NOx": 45.0,
        "PM2.5": 28.0,
        "CO2": 420.0
    })
    res_str = check_cpcb_compliance(air_json=normal_air)
    data = json.loads(res_str)
    assert data["compliant"] is True
    assert data["air_assessment"]["SO2"]["status"] == "PASS"
    assert data["air_assessment"]["PM2.5"]["status"] == "PASS"

def test_air_compliance_fail():
    """Verify that non-compliant air metrics result in a FAIL status."""
    violated_air = json.dumps({
        "SO2": 150.0, # exceeds 80.0
        "NOx": 95.0,  # exceeds 80.0
        "PM2.5": 90.0, # exceeds 60.0
        "CO2": 1200.0 # exceeds 1000.0
    })
    res_str = check_cpcb_compliance(air_json=violated_air)
    data = json.loads(res_str)
    assert data["compliant"] is False
    assert data["status"] == "NON-COMPLIANT"
    assert len(data["violations"]) >= 4
    assert data["air_assessment"]["SO2"]["status"] == "FAIL"

def test_agent_config():
    """Verify that the AirMonitor Agent is configured correctly with tools."""
    assert air_monitor_agent.name == "AirMonitor"
    assert len(air_monitor_agent.tools) == 2
