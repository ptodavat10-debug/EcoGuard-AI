# EcoGuard AI - Google x Kaggle AI Agents Capstone

## Track: Agents for Good

---

## 1. Project Overview & Inspiration
Industrial wastewater discharge and gaseous stack emissions pose severe ecological and human health hazards if left unchecked. The Central Pollution Control Board (CPCB) regulates these boundaries, but enforcement agencies suffer from slow manual audits, missing logs, and delayed operator alerts. 

**EcoGuard AI** is a secure, multi-agent AI system designed to solve this by providing real-time compliance checking, automated incident dispatching, and secure markdown audit logging. By bringing code-first agentic orchestration (via Google ADK) together with standard protocol tooling (via MCP) and strict local safety checks, EcoGuard AI demonstrates how AI can be deployed safely for public good.

---

## 2. Multi-Agent System (Google ADK)
The system models the compliance checking workflow as a hierarchical delegation tree:
* **EcoGuard Master (Orchestrator)**: Parses the user directive, loads the sensor metrics from the data layer, and delegates to specialized sub-agents.
* **WaterMonitor Agent**: Focuses on wastewater parameters (pH, BOD, COD, Heavy Metals). Calls the `get_water_quality` tool, interprets correlations, and suggests bio-chemical neutralization steps.
* **AirMonitor Agent**: Focuses on stack emissions (SO₂, NOₓ, PM2.5, CO₂). Calls the `get_air_emissions` tool, analyzes health index boundaries, and suggests scrubbers/filter adjustments.
* **AlertDispatch Agent**: Generates structured, emergency SMS alerts (limited to 160 characters) and professional email warnings to operators if CPCB thresholds are exceeded.
* **ReportGen Agent**: Compiles assessments, violations, and action plans into a publication-ready Markdown compliance audit report.

---

## 3. MCP Server & Compliance Engine
The compliance checks are decoupled from the agent logic and centralized inside a **FastMCP Server**:
* **Tools Exposed**:
  1. `get_water_quality()`: Reads the current wastewater readings in JSON.
  2. `get_air_emissions()`: Reads the current stack emission readings in JSON.
  3. `check_cpcb_compliance()`: Compares current metrics against standard limits, returning compliant state, violations, and parameter-level status.
* **Data Integration**: Sliders in the Gradio dashboard write to `cpcb_sensor_readings.json`, which acts as the shared sensor registry. The MCP tools query this registry, enabling complete sync between the UI and the agents.

---

## 4. Safety & Security Safeguards
Deploying LLM agents in industrial workflows requires strict security boundaries. EcoGuard AI integrates three core safety modules:
1. **Input Sanitization & Validation**: The validator rejects impossible parameters (e.g. negative concentrations, pH < 0 or > 14) before they are passed to the compliance engine, preventing sensor spoofing.
2. **Pre-flight Prompt Injection Shield**: Scans custom queries for override phrases (e.g., `"ignore previous instructions"`, `"override safety Limits"`) and blocks execution, returning a warning to the dashboard.
3. **Immutable Audit Logging**: Records all events, agent actions, alert triggers, and validation errors in `logs/audit.log` with ISO timestamps, ensuring complete audit transparency.

---

## 5. Kaggle Capstone Concepts Demonstrated
* **Multi-Agent Collaboration**: Hierarchical delegation pattern using the Google ADK `Agent` and `Runner` API.
* **Model Context Protocol (MCP)**: Custom FastMCP server exposing tools consumed directly by the agents.
* **Security & Safe Execution**: Input constraints, prompt injection filtering, and logging.
* **Deployability**: Standalone Python project runnable locally using Gradio, with clean packaging and comprehensive integration tests.
