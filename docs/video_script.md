# EcoGuard AI - Video Walkthrough Script (5-Minute Limit)

This script outlines the video walkthrough for the Google x Kaggle AI Agents Capstone submission.

---

## 🎬 Section 1: Intro & Problem Statement (0:00 - 0:45)
* **Visual**: Presenter on screen or slide displaying: *"EcoGuard AI: Agents for Good - CPCB Industrial Pollution Compliance Monitor"*.
* **Audio**:
  > "Hello everyone! Welcome to EcoGuard AI, our submission for the Google x Kaggle AI Agents Capstone in the 'Agents for Good' track.
  > 
  > Industrial wastewater discharge and gaseous stack emissions present severe environmental hazards if they violate regulations. In India, the Central Pollution Control Board, or CPCB, sets strict limits. However, enforcement faces delays, manual errors, and a lack of audit logs.
  > 
  > EcoGuard AI solves this by introducing a secure, multi-agent AI system that automates CPCB compliance auditing, alerts operators instantly of violations, and maintains secure logs."

---

## 🎬 Section 2: Architecture & Agents (0:45 - 1:45)
* **Visual**: Show the Mermaid architecture diagram (or slides detailing the agents and MCP server).
* **Audio**:
  > "Let's review the architecture. Our system is built on two core frameworks: Google's Agent Development Kit (ADK) for multi-agent coordination, and the Model Context Protocol (MCP) for tool integration.
  > 
  > At the center is the **EcoGuard Master Orchestrator**. When it receives sensor metrics, it delegates to specialized agents:
  > - The **WaterMonitor Agent** inspects pH, BOD, COD, and Heavy Metals.
  > - The **AirMonitor Agent** inspects SO₂, NOₓ, PM2.5, and CO₂.
  > - If violations are found, the **AlertDispatch Agent** drafts emergency SMS and email notices.
  > - Finally, the **ReportGen Agent** compiles these findings into a detailed audit report."

---

## 🎬 Section 3: Interactive Dashboard Demo (1:45 - 3:00)
* **Visual**: Screen recording of the Gradio dashboard running on `http://localhost:7860`.
* **Audio**:
  > "Let's see it in action. Here is our Gradio dashboard running locally. On the left, we have pollution sliders for water and air. On the right, we have compliance indicators, outbox, and diagnostics.
  > 
  > If we leave all parameters at normal compliant levels and click **Run Compliance Check**, the status card turns green, indicating a **PASS**. The outbox remains clean, and a complete markdown audit report is generated.
  > 
  > Now, let's simulate a violation. I'll slide the wastewater pH to `11.0` (which is highly alkaline) and the stack SO₂ emissions to `150.0` µg/m³. Clicking the button immediately flags a red **FAIL**. In the outbox, we see an emergency SMS drafted for the plant operator and a warning email for the environmental manager."

---

## 🎬 Section 4: Security Shield & Logging (3:00 - 4:00)
* **Visual**: Toggle to the 'Security Audit Log' tab in the UI, then show the code inside `security/` and `logs/audit.log`.
* **Audio**:
  > "Safety and security are critical for industrial systems. EcoGuard AI integrates a three-layer security shield.
  > 
  > First, **Input Validation** rejects physically impossible metrics, preventing corrupted inputs.
  > 
  > Second, our **Prompt Protection Shield** performs pre-flight scans on user queries. If I type a bypass phrase like *'ignore previous instructions'* and run the check, the shield immediately blocks the query, shows a red warning, and halts execution.
  > 
  > Third, every event—including agent decisions, tool calls, and blocked injection attempts—is recorded in `logs/audit.log` with secure ISO-timestamps."

---

## 🎬 Section 5: Code Walkthrough & Conclusion (4:00 - 5:00)
* **Visual**: Quick look at the python files: `mcp_server.py`, `config.py`, and the agent scripts under `agents/`.
* **Audio**:
  > "Under the hood, our Central Compliance Engine is exposed as a FastMCP Server, declaring standard tools like `check_cpcb_compliance`. Google ADK agents consume these tools locally as Python functions, keeping our code clean and modular.
  > 
  > We have verified the entire system with 16 integration tests checking metrics, safety boundaries, and agent bindings.
  > 
  > EcoGuard AI demonstrates how multi-agent teams and MCP servers can collaborate to enforce environmental standards securely and efficiently. Thank you for watching!"
