import logging
from typing import AsyncGenerator, Any
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.genai import types

from config import GEMINI_MODEL
from agents.water_monitor_agent import water_monitor_agent
from agents.air_monitor_agent import air_monitor_agent
from agents.alert_dispatch_agent import alert_dispatch_agent
from agents.report_gen_agent import report_gen_agent

# Setup logger for the agent
logger = logging.getLogger("EcoGuardAI.Master")

# Define system instruction for the Master agent
MASTER_INSTRUCTION = """
You are the EcoGuard Master Agent. You act as the Orchestrator for the CPCB compliance inspection.
Your team consists of the following specialized sub-agents:
1. WaterMonitor: Analyzes pH, BOD, COD, and Heavy Metals.
2. AirMonitor: Analyzes SO2, NOx, PM2.5, and CO2.
3. AlertDispatch: Drafts mock SMS and Email alerts if any parameter is out of bounds.
4. ReportGen: Compiles the final Markdown audit report.

When you are asked to check compliance for a set of industrial readings:
1. Route the water metrics (pH, BOD, COD, Heavy Metals) to WaterMonitor. Ask for compliance evaluation.
2. Route the air metrics (SO2, NOx, PM2.5, CO2) to AirMonitor. Ask for compliance evaluation.
3. Review their findings. If there are violations of CPCB standards, route the violation details to AlertDispatch.
4. Delegate the compiled analyses and draft alerts to ReportGen to formulate the final CPCB Compliance Audit Report.
5. Provide a summary of which agents were routed, compliance status, and the final report.

Keep your reasoning clear and show how you transition between agents.
"""

# Instantiate the Master Agent using Google ADK
eco_guard_master_agent = Agent(
    name="EcoGuardMaster",
    model=GEMINI_MODEL,
    instruction=MASTER_INSTRUCTION,
    description="The main orchestrator agent that delegates compliance tasks to specialized sub-agents.",
    sub_agents=[
        water_monitor_agent,
        air_monitor_agent,
        alert_dispatch_agent,
        report_gen_agent
    ]
)

# Helper function to run a compliance check programmatically
async def run_compliance_check(metrics: dict[str, float]) -> AsyncGenerator[Any, None]:
    """
    Programmatically runs the compliance check workflow using Google ADK.
    
    Args:
        metrics (dict): Dictionary containing pollution readings:
            - pH, BOD, COD, Heavy Metals
            - SO2, NOx, PM2.5, CO2
            
    Yields:
        Event: Execution events from the runner (live agent reasoning and traces).
    """
    logger.info("Initializing Google ADK Runner for compliance check.")
    
    # Formulate query text with all readings
    query_text = (
        f"Please run a CPCB compliance check on the following industrial sensor readings:\n"
        f"- Wastewater parameters: pH={metrics.get('pH')}, BOD={metrics.get('BOD')} mg/L, COD={metrics.get('COD')} mg/L, Heavy Metals={metrics.get('Heavy Metals')} mg/L\n"
        f"- Air emissions parameters: SO2={metrics.get('SO2')} µg/m³, NOx={metrics.get('NOx')} µg/m³, PM2.5={metrics.get('PM2.5')} µg/m³, CO2={metrics.get('CO2')} ppm"
    )
    
    # Create required services (in-memory for local dashboard)
    session_service = InMemorySessionService()
    # Create default InMemoryArtifactService
    artifact_service = InMemoryArtifactService()
    
    # Create the runner
    runner = Runner(
        app_name="EcoGuardAI_ComplianceCheck",
        agent=eco_guard_master_agent,
        session_service=session_service,
        artifact_service=artifact_service
    )
    
    # Create a new session
    session = session_service.create_session(user_id="operator_local")
    
    # Construct Google GenAI content object
    new_message = types.Content(
        role='user',
        parts=[types.Part(text=query_text)]
    )
    
    logger.info(f"Running compliance check for Session ID: {session.id}")
    
    # Execute the agent workflow and stream events
    async for event in runner.run_async(user_id="operator_local", session_id=session.id, new_message=new_message):
        yield event
