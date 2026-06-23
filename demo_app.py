import os
import json
import asyncio
import time
import logging
from typing import Dict, Any, List, Tuple, Generator
import gradio as gr

# Import configuration and modules
from config import CPCB_LIMITS
from security.input_validator import validate_metrics
from security.prompt_protection import scan_for_injection
from security.audit_logger import (
    log_agent_action, 
    log_compliance_check, 
    log_alert_dispatched, 
    log_security_violation
)
from mcp_server import save_sensor_readings, check_cpcb_compliance
from agents.eco_guard_master import run_compliance_check, eco_guard_master_agent

# Setup logging
logger = logging.getLogger("EcoGuardAI.Gradio")

# Default UI sensor readings
DEFAULT_SLIDERS = {
    "pH": 7.2,
    "BOD": 15.0,
    "COD": 120.0,
    "Heavy Metals": 0.05,
    "SO2": 35.0,
    "NOx": 40.0,
    "PM2.5": 28.0,
    "CO2": 420.0
}

def get_compliance_html(status: str) -> str:
    """Returns a styled HTML card indicating CPCB compliance status."""
    if status == "COMPLIANT":
        return """
        <div style="background-color: #10B981; color: white; padding: 20px; border-radius: 12px; text-align: center; font-weight: bold; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
            <p style="font-size: 1.2rem; margin: 0; text-transform: uppercase; letter-spacing: 0.1em;">CPCB Compliance Status</p>
            <p style="font-size: 2.5rem; margin: 5px 0 0 0;">✔ PASS</p>
            <p style="font-size: 0.9rem; margin: 5px 0 0 0; opacity: 0.9;">All monitored parameters are within safe limits.</p>
        </div>
        """
    elif status == "NON-COMPLIANT":
        return """
        <div style="background-color: #EF4444; color: white; padding: 20px; border-radius: 12px; text-align: center; font-weight: bold; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
            <p style="font-size: 1.2rem; margin: 0; text-transform: uppercase; letter-spacing: 0.1em;">CPCB Compliance Status</p>
            <p style="font-size: 2.5rem; margin: 5px 0 0 0;">✘ FAIL</p>
            <p style="font-size: 0.9rem; margin: 5px 0 0 0; opacity: 0.9;">CPCB pollution limit violation detected! Check alerts panel.</p>
        </div>
        """
    else:
        return """
        <div style="background-color: #6B7280; color: white; padding: 20px; border-radius: 12px; text-align: center; font-weight: bold; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
            <p style="font-size: 1.2rem; margin: 0; text-transform: uppercase; letter-spacing: 0.1em;">CPCB Compliance Status</p>
            <p style="font-size: 2.5rem; margin: 5px 0 0 0;">⌛ IDLE</p>
            <p style="font-size: 0.9rem; margin: 5px 0 0 0; opacity: 0.9;">Awaiting sensor reading compliance validation trigger.</p>
        </div>
        """

def get_alerts_html(violations: List[str], alert_json: Dict[str, Any] = None) -> str:
    """Returns styled HTML for the active alerts outbox panel."""
    if not violations:
        return """
        <div style="padding: 15px; background-color: #F3F4F6; border-radius: 8px; border-left: 5px solid #10B981; color: #1F2937;">
            <p style="margin: 0; font-weight: bold;">✔ Outbox Clean</p>
            <p style="margin: 5px 0 0 0; font-size: 0.9rem;">No emergency notifications queued. Facility status is normal.</p>
        </div>
        """
    
    violations_li = "".join([f"<li style='margin-bottom: 5px;'>🚨 {v}</li>" for v in violations])
    
    outbox_section = ""
    if alert_json and alert_json.get("alerts_generated"):
        outbox_section = f"""
        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #FCA5A5;">
            <p style="margin: 0; font-weight: bold; color: #991B1B;">📤 SIMULATED DISPATCH QUEUE</p>
            <div style="background-color: #FEF2F2; padding: 10px; border-radius: 6px; margin-top: 5px; font-family: monospace; font-size: 0.85rem;">
                <p style="margin: 0; color: #B91C1C;"><b>[SMS Outbox - Site Operator]</b><br>{alert_json.get('sms_text')}</p>
                <p style="margin: 10px 0 0 0; color: #B91C1C;"><b>[Email Outbox - Manager & CPCB Regional Officer]</b><br>
                <b>Subject:</b> {alert_json.get('email_subject')}<br>
                {alert_json.get('email_body').replace('\n', '<br>')}</p>
            </div>
        </div>
        """
    
    return f"""
    <div style="padding: 15px; background-color: #FEF2F2; border-radius: 8px; border-left: 5px solid #EF4444; color: #1F2937; box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.06);">
        <p style="margin: 0; font-weight: bold; color: #991B1B; font-size: 1.1rem;">⚠️ CPCB Violations Detected!</p>
        <ul style="margin: 8px 0 0 0; padding-left: 20px; color: #B91C1C; font-size: 0.95rem;">
            {violations_li}
        </ul>
        {outbox_section}
    </div>
    """

def read_audit_logs() -> str:
    """Reads and returns the last 30 lines of the security audit log."""
    log_path = "logs/audit.log"
    if not os.path.exists(log_path):
        return "No audit logs recorded yet."
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Return last 30 logs reversed (newest first)
            recent_logs = lines[-30:]
            return "".join(recent_logs)
    except Exception as e:
        return f"Error reading audit logs: {e}"

def generate_mock_report(metrics: Dict[str, float], compliance_res: Dict[str, Any], alert_res: Dict[str, Any]) -> str:
    """Generates a structured CPCB Compliance Audit Report in Markdown format."""
    is_compliant = compliance_res.get("compliant", False)
    status_badge = "🟢 PASS (COMPLIANT)" if is_compliant else "🔴 FAIL (NON-COMPLIANT)"
    
    report = f"""# CPCB Industrial Compliance Audit Report

## 1. Executive Summary
- **Compliance Status**: {status_badge}
- **Audit Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **Facility Reference**: EcoGuard AI Compliance Inspector

## 2. Wastewater Quality Assessment
| Parameter | Measured Value | CPCB Limit | Status |
| :--- | :--- | :--- | :--- |
| **pH** | {metrics['pH']:.2f} | 6.5 - 8.5 | {"✅ PASS" if compliance_res['water_assessment']['pH']['status'] == 'PASS' else "❌ FAIL"} |
| **BOD (mg/L)** | {metrics['BOD']:.2f} | <= 30.0 | {"✅ PASS" if compliance_res['water_assessment']['BOD']['status'] == 'PASS' else "❌ FAIL"} |
| **COD (mg/L)** | {metrics['COD']:.2f} | <= 250.0 | {"✅ PASS" if compliance_res['water_assessment']['COD']['status'] == 'PASS' else "❌ FAIL"} |
| **Heavy Metals (mg/L)** | {metrics['Heavy Metals']:.2f} | <= 0.1 | {"✅ PASS" if compliance_res['water_assessment']['Heavy Metals']['status'] == 'PASS' else "❌ FAIL"} |

*Remarks*: 
- High organic loads (elevated BOD/COD) deplete dissolved oxygen in receiving rivers.
- Acidic or basic effluent discharges corrode facility sewage pipelines and damage biological treatment processes.

## 3. Stack & Ambient Air Quality Assessment
| Pollutant | Measured Value | CPCB Limit | Status |
| :--- | :--- | :--- | :--- |
| **SO₂ (µg/m³)** | {metrics['SO2']:.2f} | <= 80.0 | {"✅ PASS" if compliance_res['air_assessment']['SO2']['status'] == 'PASS' else "❌ FAIL"} |
| **NOₓ (µg/m³)** | {metrics['NOx']:.2f} | <= 80.0 | {"✅ PASS" if compliance_res['air_assessment']['NOx']['status'] == 'PASS' else "❌ FAIL"} |
| **PM2.5 (µg/m³)** | {metrics['PM2.5']:.2f} | <= 60.0 | {"✅ PASS" if compliance_res['air_assessment']['PM2.5']['status'] == 'PASS' else "❌ FAIL"} |
| **CO₂ (ppm)** | {metrics['CO2']:.2f} | <= 1000.0 | {"✅ PASS" if compliance_res['air_assessment']['CO2']['status'] == 'PASS' else "❌ FAIL"} |

*Remarks*:
- Excess PM2.5 causes acute respiratory distress and is heavily penalized by SPCBs.
- Excess SO₂ and NOₓ emissions signify faulty scrubbers or inefficient catalytic reduction units.

"""
    if not is_compliant:
        report += f"""## 4. Dispatched Alerts Outbox Summary
- **Alert Status**: Alert Triggered & Queued
- **Dispatched SMS Alert**: "{alert_res.get('sms_text', 'N/A')}"
- **Dispatched Email Subject**: "{alert_res.get('email_subject', 'N/A')}"

## 5. Required Action and Remediation Plan
"""
        # Formulate customized remediation suggestions based on violations
        rem_plan = []
        if compliance_res['water_assessment']['pH']['status'] == 'FAIL':
            rem_plan.append("- **pH Remediation**: Initiate immediate dosing of chemical neutralizers (lime for acidic, sulfuric acid/CO2 for alkaline) in the primary chemical treatment reactor.")
        if compliance_res['water_assessment']['BOD']['status'] == 'FAIL' or compliance_res['water_assessment']['COD']['status'] == 'FAIL':
            rem_plan.append("- **BOD/COD Remediation**: Boost aeration rate in the biological tank and check sludge volume index. Check activated sludge microorganism activity.")
        if compliance_res['water_assessment']['Heavy Metals']['status'] == 'FAIL':
            rem_plan.append("- **Heavy Metals Remediation**: Inspect precipitation tank flocculant levels. Add precipitating agents (e.g., sodium hydroxide or sulfide) to filter out heavy metal hydroxides.")
        if compliance_res['air_assessment']['SO2']['status'] == 'FAIL':
            rem_plan.append("- **SO₂ Remediation**: Audit wet flue-gas desulfurization (FGD) scrubber system. Adjust limestone slurry flow rates.")
        if compliance_res['air_assessment']['NOx']['status'] == 'FAIL':
            rem_plan.append("- **NOₓ Remediation**: Optimize Selective Catalytic Reduction (SCR) ammonia injection rate and check furnace temperature profiles.")
        if compliance_res['air_assessment']['PM2.5']['status'] == 'FAIL':
            rem_plan.append("- **PM2.5 Remediation**: Check fabric filter baghouse pressure drop or inspect Electrostatic Precipitator (ESP) electrode voltages for fouling.")
        if compliance_res['air_assessment']['CO2']['status'] == 'FAIL':
            rem_plan.append("- **CO₂ Remediation**: Adjust fuel-to-air combustion ratio and clean gas burners to increase thermal efficiency.")

        report += "\n".join(rem_plan)
    else:
        report += """## 4. System Status Check
- **Compliance Status**: All measurements conform to statutory standards.
- **Action Required**: None. Maintain routine monitoring logs and follow periodic cleaning schedules.
"""
    
    report += "\n---\n*Report compiled securely by EcoGuard AI ReportGen Agent.*"
    return report

async def handle_compliance_check(
    ph: float, bod: float, cod: float, metals: float, 
    so2: float, nox: float, pm25: float, co2: float,
    directive: str, api_key: str
) -> Generator[Tuple[str, str, str, str, str, str], None, None]:
    """
    Handles the execution of the compliance check workflow.
    Supports:
    - Pre-flight prompt injection checks
    - Metric boundary validation
    - In-memory runner executions using Google ADK (when API Key is provided)
    - Realistic simulation of agent routing & tracing (when API Key is empty)
    
    Yields UI updates incrementally for a responsive, live look.
    """
    # 1. Update API Key in environment if provided
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key
    
    # Check if we should run in live ADK mode
    is_live = "GEMINI_API_KEY" in os.environ and os.environ["GEMINI_API_KEY"].strip() != ""
    
    metrics = {
        "pH": ph,
        "BOD": bod,
        "COD": cod,
        "Heavy Metals": metals,
        "SO2": so2,
        "NOx": nox,
        "PM2.5": pm25,
        "CO2": co2
    }
    
    # 2. Check Prompt Injection
    is_safe, flagged_phrase = scan_for_injection(directive)
    if not is_safe:
        log_security_violation("PROMPT_INJECTION_DETECTED", f"Input text contained: '{flagged_phrase}'")
        error_html = f"<div style='color: white; background-color: #DC2626; padding: 15px; border-radius: 8px;'><b>❌ Security Warning:</b> Prompt injection attempt detected. Blocked query containing: '{flagged_phrase}'</div>"
        yield (
            error_html,                              # Status
            f"Blocked query containing: '{flagged_phrase}'", # Active Alerts
            "[Security Shield] Scanning user query... BLOCKED prompt injection.", # Reasoning
            "User -> SecurityShield (Scanned and Rejected)", # Communication Trace
            "",                                      # Report
            read_audit_logs()                        # Audit log
        )
        return

    # 3. Validate Boundaries
    is_valid, error_msg = validate_metrics(metrics.copy())
    if not is_valid:
        log_security_violation("VALUE_VALIDATION_REJECTED", error_msg)
        error_html = f"<div style='color: white; background-color: #DC2626; padding: 15px; border-radius: 8px;'><b>❌ Input Validation Error:</b> {error_msg}</div>"
        yield (
            error_html,
            error_msg,
            f"[Input Validator] Security validation rejected input values: {error_msg}",
            "User -> InputValidator (Rejected values)",
            "",
            read_audit_logs()
        )
        return

    # Write metrics to sensor json file
    save_sensor_readings(metrics)
    
    # Execute MCP Compliance check tool
    mcp_result_str = check_cpcb_compliance()
    compliance_json = json.loads(mcp_result_str)
    
    # Formulate mock alerts
    violations = compliance_json.get("violations", [])
    alert_dispatch = {"alerts_generated": False, "sms_text": "", "email_subject": "", "email_body": "", "severity": "INFO"}
    
    if violations:
        alert_dispatch["alerts_generated"] = True
        alert_dispatch["severity"] = "CRITICAL"
        alert_dispatch["sms_text"] = f"CRITICAL CPCB Violation! Parameters exceeded: {', '.join(violations[:2])}. Take immediate corrective actions."
        alert_dispatch["email_subject"] = "URGENT: CPCB Emission and Discharge Compliance Violation Detected"
        alert_dispatch["email_body"] = (
            f"Dear Facility Environmental Manager,\n\n"
            f"This is an automated safety alert from EcoGuard AI. "
            f"Our compliance monitor has detected that the following parameters have exceeded statutory standards:\n"
            + "\n".join([f"- {v}" for v in violations]) +
            f"\n\nPlease initiate standard operating procedures and remediation protocols immediately. "
            f"This compliance record has been written to the secure facility audit logs.\n\n"
            f"Regards,\nEcoGuard Safety System"
        )
        # Log alert to audit log
        log_alert_dispatched("CRITICAL", [v.split()[0] for v in violations], f"Alert dispatched: {violations}")

    # Generate markdown report
    md_report = generate_mock_report(metrics, compliance_json, alert_dispatch)

    if not is_live:
        # --- SIMULATION MODE ---
        logger.info("Running in SIMULATION mode (No API Key set).")
        
        # 1. Master Agent starts
        reasoning = f"[EcoGuardMaster] Received compliance check request.\nUser Query: '{directive}'\nParameters:\n  Water: pH={ph}, BOD={bod}, COD={cod}, Metals={metals}\n  Air: SO2={so2}, NOx={nox}, PM2.5={pm25}, CO2={co2}\nDelegating parameter sets to specialized monitor agents..."
        trace = "User ➔ EcoGuardMaster (Query received)"
        yield (get_compliance_html("IDLE"), get_alerts_html([]), reasoning, trace, "", read_audit_logs())
        await asyncio.sleep(1.0)
        
        # 2. WaterMonitor Agent runs
        reasoning += f"\n\n[WaterMonitor] Invoking get_water_quality() tool...\n[WaterMonitor] Analyzing water parameters against CPCB limits:\n"
        for k, v in compliance_json["water_assessment"].items():
            reasoning += f"  - {k}: {v['value']} (Limit {v['limit']}) ➔ {v['status']}\n"
        if compliance_json["water_assessment"]["pH"]["status"] == "FAIL" or compliance_json["water_assessment"]["BOD"]["status"] == "FAIL":
            reasoning += "[WaterMonitor] VIOLATION flagged. Wastewater pollutants exceed guidelines. Biological loading or pH imbalance detected."
        else:
            reasoning += "[WaterMonitor] All wastewater metrics conform to CPCB limits."
            
        trace += "\nEcoGuardMaster ➔ WaterMonitor (Water metrics delegation)\nWaterMonitor ➔ EcoGuardMaster (Assessment complete)"
        yield (get_compliance_html("IDLE"), get_alerts_html([]), reasoning, trace, "", read_audit_logs())
        await asyncio.sleep(1.2)
        
        # 3. AirMonitor Agent runs
        reasoning += f"\n\n[AirMonitor] Invoking get_air_emissions() tool...\n[AirMonitor] Analyzing air emissions against CPCB standards:\n"
        for k, v in compliance_json["air_assessment"].items():
            reasoning += f"  - {k}: {v['value']} (Limit {v['limit']}) ➔ {v['status']}\n"
        if compliance_json["air_assessment"]["PM2.5"]["status"] == "FAIL" or compliance_json["air_assessment"]["SO2"]["status"] == "FAIL":
            reasoning += "[AirMonitor] VIOLATION flagged. Stack emissions exceed ambient air boundaries."
        else:
            reasoning += "[AirMonitor] All gaseous and particulate emissions are within safe limits."
            
        trace += "\nEcoGuardMaster ➔ AirMonitor (Air metrics delegation)\nAirMonitor ➔ EcoGuardMaster (Assessment complete)"
        yield (get_compliance_html("IDLE"), get_alerts_html([]), reasoning, trace, "", read_audit_logs())
        await asyncio.sleep(1.2)
        
        # 4. AlertDispatch Agent runs
        if violations:
            reasoning += f"\n\n[EcoGuardMaster] Reviewing reports. Violations found: {violations}. Triggering AlertDispatch Agent to queue operator alerts..."
            trace += "\nEcoGuardMaster ➔ AlertDispatch (Violations reported)"
            yield (get_compliance_html("IDLE"), get_alerts_html(violations), reasoning, trace, "", read_audit_logs())
            await asyncio.sleep(0.8)
            
            reasoning += f"\n\n[AlertDispatch] Structuring emergency notices.\nSMS Alert queued for Facility Operator.\nEmail notice drafted for Manager & CPCB Regional Officer."
            trace += "\nAlertDispatch ➔ EcoGuardMaster (Alerts queued in outbox)"
            yield (get_compliance_html("IDLE"), get_alerts_html(violations, alert_dispatch), reasoning, trace, "", read_audit_logs())
            await asyncio.sleep(1.0)
        else:
            reasoning += f"\n\n[EcoGuardMaster] Reviewing reports. All parameters COMPLIANT. Skipping AlertDispatch Agent."
            await asyncio.sleep(0.5)

        # 5. ReportGen Agent runs
        reasoning += f"\n\n[EcoGuardMaster] Initiating ReportGen Agent to compile final compliance report..."
        trace += "\nEcoGuardMaster ➔ ReportGen (Compile final audit report)"
        yield (get_compliance_html("IDLE"), get_alerts_html(violations, alert_dispatch), reasoning, trace, "", read_audit_logs())
        await asyncio.sleep(0.8)
        
        reasoning += f"\n\n[ReportGen] Compiling compliance data and remediation suggestions into Markdown report."
        trace += "\nReportGen ➔ EcoGuardMaster (Markdown report delivered)\nEcoGuardMaster ➔ User (Audit completed)"
        
        status_code = "COMPLIANT" if compliance_json["compliant"] else "NON-COMPLIANT"
        yield (
            get_compliance_html(status_code), 
            get_alerts_html(violations, alert_dispatch), 
            reasoning, 
            trace, 
            md_report, 
            read_audit_logs()
        )
        
    else:
        # --- LIVE ADK AGENT MODE ---
        logger.info("Running in LIVE agent mode using Google ADK.")
        
        # Log starting execution
        log_agent_action("EcoGuardMaster", "run_compliance_check", "Triggered ADK workflow execution")
        
        # Accumulators
        live_reasoning = "[Live ADK Execution Started]\n"
        live_trace = "User ➔ EcoGuardMaster (Query received)\n"
        
        yield (get_compliance_html("IDLE"), get_alerts_html([]), live_reasoning, live_trace, "", read_audit_logs())
        
        try:
            # Execute ADK agents using the master orchestrator async runner
            async for event in run_compliance_check(metrics):
                # Update reasoning logs based on text parts from the event
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            live_reasoning += f"\n[{event.author}] {part.text}"
                            
                            # Deduce agent transitions from the author text to show trace
                            if "WaterMonitor" in live_reasoning and "WaterMonitor" not in live_trace:
                                live_trace += "EcoGuardMaster ➔ WaterMonitor (Water metrics delegation)\n"
                            if "AirMonitor" in live_reasoning and "AirMonitor" not in live_trace:
                                live_trace += "EcoGuardMaster ➔ AirMonitor (Air metrics delegation)\n"
                            if "AlertDispatch" in live_reasoning and "AlertDispatch" not in live_trace:
                                live_trace += "EcoGuardMaster ➔ AlertDispatch (Violations reported)\n"
                            if "ReportGen" in live_reasoning and "ReportGen" not in live_trace:
                                live_trace += "EcoGuardMaster ➔ ReportGen (Compile report)\n"
                                
                yield (
                    get_compliance_html("IDLE"), 
                    get_alerts_html(violations), 
                    live_reasoning, 
                    live_trace, 
                    "", 
                    read_audit_logs()
                )
                await asyncio.sleep(0.2)
                
            live_trace += "ReportGen ➔ EcoGuardMaster (Report compiled)\nEcoGuardMaster ➔ User (Audit completed)"
            log_agent_action("EcoGuardMaster", "run_compliance_check", "Execution complete")
            
            status_code = "COMPLIANT" if compliance_json["compliant"] else "NON-COMPLIANT"
            yield (
                get_compliance_html(status_code), 
                get_alerts_html(violations, alert_dispatch), 
                live_reasoning, 
                live_trace, 
                md_report, 
                read_audit_logs()
            )
            
        except Exception as e:
            logger.error(f"Live ADK execution failed: {e}")
            log_security_violation("ADK_WORKFLOW_FAILED", str(e))
            error_html = f"<div style='color: white; background-color: #DC2626; padding: 15px; border-radius: 8px;'><b>❌ ADK Execution Failed:</b> {str(e)}<br><i>Ensure your GEMINI_API_KEY is valid. Fall back to simulation mode by clearing the API Key box.</i></div>"
            yield (
                error_html,
                str(e),
                live_reasoning + f"\n\n[ERROR] ADK run failed: {e}",
                live_trace + "\nSystem ➔ Failure state",
                "",
                read_audit_logs()
            )

# Create Gradio App Interface
with gr.Blocks(theme=gr.themes.Soft(), css="""
    .container { max-width: 1200px; margin: auto; }
    .header-text { text-align: center; margin-bottom: 20px; }
""") as demo:
    
    with gr.Row():
        gr.HTML("""
        <div style="text-align: center; margin-bottom: 25px;">
            <h1 style="color: #1E3A8A; font-size: 2.25rem; margin-bottom: 5px;">EcoGuard AI</h1>
            <p style="color: #4B5563; font-size: 1.1rem; margin: 0;">Industrial Pollution Compliance Monitor (CPCB Standards)</p>
            <div style="width: 80px; height: 4px; background-color: #3B82F6; margin: 15px auto; border-radius: 2px;"></div>
        </div>
        """)
        
    with gr.Row():
        # --- LEFT COLUMN: Input Sliders ---
        with gr.Column(scale=1):
            
            with gr.Group():
                gr.Markdown("### 🚰 Wastewater Parameters")
                ph_slider = gr.Slider(minimum=0.0, maximum=14.0, value=7.2, step=0.1, label="pH Level (CPCB limit: 6.5 - 8.5)")
                bod_slider = gr.Slider(minimum=0.0, maximum=100.0, value=15.0, step=0.5, label="BOD (Biochemical Oxygen Demand) mg/L (limit: <= 30)")
                cod_slider = gr.Slider(minimum=0.0, maximum=500.0, value=120.0, step=1.0, label="COD (Chemical Oxygen Demand) mg/L (limit: <= 250)")
                metals_slider = gr.Slider(minimum=0.0, maximum=5.0, value=0.05, step=0.01, label="Heavy Metals mg/L (limit: <= 0.1)")
                
            with gr.Group():
                gr.Markdown("### 💨 Air Emissions Parameters")
                so2_slider = gr.Slider(minimum=0.0, maximum=300.0, value=35.0, step=1.0, label="SO₂ (Sulfur Dioxide) µg/m³ (limit: <= 80)")
                nox_slider = gr.Slider(minimum=0.0, maximum=300.0, value=40.0, step=1.0, label="NOₓ (Nitrogen Oxides) µg/m³ (limit: <= 80)")
                pm25_slider = gr.Slider(minimum=0.0, maximum=200.0, value=28.0, step=1.0, label="PM2.5 (Particulate Matter 2.5) µg/m³ (limit: <= 60)")
                co2_slider = gr.Slider(minimum=300.0, maximum=3000.0, value=420.0, step=10.0, label="CO₂ (Carbon Dioxide) ppm (limit: <= 1000)")
                
            with gr.Group():
                gr.Markdown("### 🛠 Operator Directive & API Key")
                directive_input = gr.Textbox(value="Run CPCB compliance inspection.", label="Operator Directive (Scanned for Prompt Injection)")
                api_key_input = gr.Textbox(type="password", label="GEMINI_API_KEY (Leave blank to run in SIMULATION mode)", placeholder="AIzaSy...")
                
            with gr.Row():
                run_btn = gr.Button("Run Compliance Check", variant="primary")
                reset_btn = gr.Button("Reset Defaults", variant="secondary")

        # --- RIGHT COLUMN: Display Outputs ---
        with gr.Column(scale=1):
            
            # CPCB Compliance Visual Indicator Card
            compliance_status_panel = gr.HTML(value=get_compliance_html("IDLE"))
            
            # Active Alerts (SMS/Email) Outbox Card
            gr.Markdown("### 📬 Incident Response Queue")
            active_alerts_panel = gr.HTML(value=get_alerts_html([]))
            
            # Tabbed Diagnostics display
            with gr.Tabs():
                
                with gr.TabItem("🧠 Live Agent Reasoning"):
                    reasoning_log = gr.Textbox(lines=14, label="Internal Agent System Thoughts", interactive=False)
                    
                with gr.TabItem("⛓ Agent Communication Trace"):
                    communication_trace = gr.Textbox(lines=10, label="Agent-to-Agent Delegation Flow", interactive=False)
                    
                with gr.TabItem("📋 Compliance Report"):
                    report_markdown = gr.Markdown(value="Audit Report will be compiled here.")
                    
                with gr.TabItem("🛡 Security Audit Log"):
                    audit_log_viewer = gr.Textbox(lines=14, label="Recent security logs (logs/audit.log)", interactive=False, value=read_audit_logs())

    # --- CALLBACKS & UI INTERACTION ---
    
    # Run Button triggers compliance check workflow
    run_btn.click(
        fn=handle_compliance_check,
        inputs=[
            ph_slider, bod_slider, cod_slider, metals_slider,
            so2_slider, nox_slider, pm25_slider, co2_slider,
            directive_input, api_key_input
        ],
        outputs=[
            compliance_status_panel,
            active_alerts_panel,
            reasoning_log,
            communication_trace,
            report_markdown,
            audit_log_viewer
        ]
    )
    
    # Reset Button restores initial clean settings
    def reset_sliders():
        return (
            DEFAULT_SLIDERS["pH"], DEFAULT_SLIDERS["BOD"], DEFAULT_SLIDERS["COD"], DEFAULT_SLIDERS["Heavy Metals"],
            DEFAULT_SLIDERS["SO2"], DEFAULT_SLIDERS["NOx"], DEFAULT_SLIDERS["PM2.5"], DEFAULT_SLIDERS["CO2"],
            "Run CPCB compliance inspection.",
            get_compliance_html("IDLE"),
            get_alerts_html([]),
            "", "", "Audit Report will be compiled here.",
            read_audit_logs()
        )
        
    reset_btn.click(
        fn=reset_sliders,
        inputs=[],
        outputs=[
            ph_slider, bod_slider, cod_slider, metals_slider,
            so2_slider, nox_slider, pm25_slider, co2_slider,
            directive_input,
            compliance_status_panel,
            active_alerts_panel,
            reasoning_log,
            communication_trace,
            report_markdown,
            audit_log_viewer
        ]
    )

if __name__ == "__main__":
    # Launch Gradio dashboard locally
    demo.launch(server_name="127.0.0.1", server_port=7860)
