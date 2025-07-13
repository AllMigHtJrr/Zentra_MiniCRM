from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import aiofiles
from datetime import datetime
from typing import List, Dict, Any
import logging
from PIL import Image
import io
import re
from contextlib import asynccontextmanager
import httpx
import asyncio
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from models import (
    LeadCreate, LeadResponse, LeadStatusUpdate, LeadInteraction, 
    InteractionResponse, WorkflowRequest, WorkflowResponse, 
    DocumentExtractionResponse, LeadStatus, LeadSource, ErrorResponse, SuccessResponse
)
from utils import (
    validate_email, extract_email_from_text, extract_name_from_text,
    save_uploaded_file, cleanup_temp_file, tesseract_ocr,
    validate_workflow_structure, get_workflow_action_description,
    sanitize_text, generate_unique_id, OLM_OCR_AVAILABLE
)
from email_service import email_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for leads and workflows
leads_data = []
workflows_data = {"workflows": [], "last_updated": datetime.now().isoformat()}
next_id = 1

# Load initial data from JSON files
async def load_data_from_files():
    global leads_data, workflows_data, next_id
    
    # Load leads
    try:
        async with aiofiles.open("leads.json", "r") as file:
            content = await file.read()
            leads_data = json.loads(content)
            if leads_data:
                next_id = max(lead["id"] for lead in leads_data) + 1
    except FileNotFoundError:
        logger.info("leads.json not found, starting with empty leads")
        leads_data = []
        next_id = 1
    
    # Load workflows
    try:
        async with aiofiles.open("workflow.json", "r") as file:
            content = await file.read()
            workflows_data = json.loads(content)
    except FileNotFoundError:
        logger.info("workflow.json not found, starting with empty workflows")
        workflows_data = {"workflows": [], "last_updated": datetime.now().isoformat()}

# Save data to JSON files
async def save_leads_to_file():
    async with aiofiles.open("leads.json", "w") as file:
        await file.write(json.dumps(leads_data, indent=2, default=str))

async def save_workflows_to_file():
    workflows_data["last_updated"] = datetime.now().isoformat()
    async with aiofiles.open("workflow.json", "w") as file:
        await file.write(json.dumps(workflows_data, indent=2, default=str))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await load_data_from_files()
    logger.info("Mini CRM API started successfully")
    yield
    # Shutdown
    logger.info("Mini CRM API shutting down...")

app = FastAPI(
    title="Mini CRM API - Agentic AI Edition",
    description="A FastAPI backend for Mini CRM application with agentic AI features",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:4028", "http://127.0.0.1:4028"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Test endpoint for CORS debugging
@app.get("/test-cors")
async def test_cors():
    """Test endpoint to verify CORS is working"""
    return {"message": "CORS is working!", "timestamp": datetime.now().isoformat()}

# Enhanced Lead Management Endpoints

@app.post("/leads/manual", response_model=LeadResponse)
async def create_lead_manual(lead: LeadCreate):
    """Create a new lead manually with enhanced validation"""
    global next_id
    
    # Additional validation
    if not validate_email(lead.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    new_lead = {
        "id": next_id,
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "status": LeadStatus.NEW,
        "source": LeadSource.MANUAL,
        "created_at": datetime.now().isoformat()
    }
    
    leads_data.append(new_lead)
    next_id += 1
    
    await save_leads_to_file()
    logger.info(f"Created new lead with agentic validation: {new_lead['name']}")
    
    # Trigger workflows for new lead
    try:
        await trigger_lead_created_workflow(new_lead)
    except Exception as e:
        logger.error(f"Failed to trigger workflows for new lead: {e}")
    
    return LeadResponse(**new_lead)

@app.post("/leads/document", response_model=DocumentExtractionResponse)
async def create_lead_from_document(file: UploadFile = File(...)):
    """Extract lead information from uploaded document using Tesseract OCR"""
    # Validate file type
    allowed_extensions = ('.pdf', '.png', '.jpg', '.jpeg')
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=400, 
            detail=f"Only {', '.join(allowed_extensions)} files are supported"
        )
    temp_file_path = None
    try:
        # Read file content
        content = await file.read()
        # Save file temporarily
        temp_file_path = await save_uploaded_file(content, file.filename)
        # Use Tesseract OCR for extraction
        extracted_data = tesseract_ocr(content, file.filename)
        if "error" in extracted_data:
            raise HTTPException(status_code=500, detail=f"Tesseract OCR failed: {extracted_data['error']}")
        
        # Create lead from extracted data
        global next_id
        new_lead = {
            "id": next_id,
            "name": extracted_data["name"],
            "email": extracted_data["email"],
            "phone": extracted_data["phone"],
            "status": extracted_data.get("status", "New"),
            "source": extracted_data["source"],
            "created_at": datetime.now().isoformat()
        }
        
        leads_data.append(new_lead)
        next_id += 1
        await save_leads_to_file()
        
        # Trigger workflows for new lead
        try:
            await trigger_lead_created_workflow(new_lead)
        except Exception as e:
            logger.error(f"Failed to trigger workflows for new lead: {e}")
        
        return DocumentExtractionResponse(**extracted_data)
    finally:
        if temp_file_path:
            await cleanup_temp_file(temp_file_path)

@app.get("/leads", response_model=List[LeadResponse])
async def get_leads():
    """Get all leads"""
    return [LeadResponse(**lead) for lead in leads_data]

@app.delete("/leads/{lead_id}")
async def delete_lead(lead_id: int):
    """Delete a lead by ID"""
    global leads_data
    
    lead_index = None
    for i, lead in enumerate(leads_data):
        if lead["id"] == lead_id:
            lead_index = i
            break
    
    if lead_index is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    deleted_lead = leads_data.pop(lead_index)
    await save_leads_to_file()
    
    logger.info(f"Deleted lead: {deleted_lead['name']}")
    return SuccessResponse(message=f"Lead {lead_id} deleted successfully")

@app.put("/leads/{lead_id}/status")
async def update_lead_status(lead_id: int, status_update: LeadStatusUpdate):
    """Update lead status"""
    lead = None
    for l in leads_data:
        if l["id"] == lead_id:
            lead = l
            break
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead["status"] = status_update.status
    await save_leads_to_file()
    
    logger.info(f"Updated lead {lead_id} status to: {status_update.status}")
    return LeadResponse(**lead)

# Enhanced Lead Interaction with LLM

@app.post("/interact", response_model=InteractionResponse)
async def interact_with_lead(interaction: LeadInteraction):
    """Enhanced interaction with a lead using LLM as a CRM assistant"""
    # Find the lead
    lead = None
    for l in leads_data:
        if l["id"] == interaction.id:
            lead = l
            break
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    try:
        # Compose the prompt for the LLM as a CRM assistant
        user_prompt = interaction.prompt
        lead_context = f"Lead info: Name: {lead['name']}, Email: {lead['email']}, Phone: {lead['phone']}, Status: {lead['status']}, Source: {lead['source']}"
        
        # Create a system prompt that makes the LLM act as a CRM assistant
        system_prompt = """You are a helpful CRM assistant for sales teams. Provide concise, actionable advice for managing leads, following up, and next steps. Avoid long lists. Respond in 1-2 clear, professional sentences. Do not mention being an AI or any backend system."""
        
        full_prompt = f"{system_prompt}\n\nLead Context: {lead_context}\n\nUser Question: {user_prompt}\n\nAssistant Response:"
        
        # --- LLM call removed for now, always return fallback ---
        raise Exception("LLM call disabled for now")
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         "http://localhost:11434/api/generate",
        #         json={
        #             "model": "llama2",
        #             "prompt": full_prompt,
        #             "stream": False
        #         },
        #         timeout=60
        #     )
        #     if response.status_code == 200:
        #         data = response.json()
        #         llm_reply = data.get("response") or data.get("message") or "[No response from LLM]"
        #     else:
        #         raise httpx.HTTPStatusError(f"LLM returned status {response.status_code}", request=response.request, response=response)
        # return {
        #     "reply": llm_reply,
        #     "lead_context": {
        #         "id": lead["id"],
        #         "name": lead["name"],
        #         "status": lead["status"],
        #         "source": lead["source"]
        #     }
        # }
    except Exception as e:
        # Return a concise, actionable response
        concise_response = f"For {lead['name']} ({lead['status']}): Consider a quick follow-up email or call. Next, update their status after the interaction."
        return {
            "reply": concise_response,
            "lead_context": {
                "id": lead["id"],
                "name": lead["name"],
                "status": lead["status"],
                "source": lead["source"]
            }
        }

# Enhanced Workflow Designer with React Flow Support

@app.post("/workflow", response_model=WorkflowResponse)
async def execute_workflow(workflow: WorkflowRequest):
    """Execute a workflow with React Flow nodes and edges"""
    
    logger.info("Executing enhanced workflow...")
    
    # Validate workflow structure
    is_valid, validation_message = validate_workflow_structure(
        [node.model_dump() for node in workflow.nodes],
        [edge.model_dump() for edge in workflow.edges]
    )
    
    if not is_valid:
        raise HTTPException(status_code=400, detail=validation_message)
    
    execution_log = []
    workflow_id = f"workflow-{generate_unique_id()}"
    
    # Simulate workflow execution by logging node actions and performing real actions
    for node in workflow.nodes:
        node_type = node.type
        node_data = node.data
        
        if node_type == "trigger":
            action_desc = f"Trigger node: {node_data.get('label', 'Unknown trigger')}"
            logger.info(action_desc)
            execution_log.append(f"[{datetime.now().isoformat()}] {action_desc}")
            
        elif node_type == "sendEmail":
            # Send real email using SendGrid
            email_subject = node_data.get('emailSubject', 'Welcome to our CRM')
            email_template = node_data.get('emailTemplate', 'Thank you for your interest!')
            sender_name = node_data.get('senderName', 'CRM System')
            
            # For workflow execution, we need lead data - use test data
            test_lead_data = {
                "name": "Test Lead",
                "email": "test@example.com"
            }
            
            email_config = {
                "emailSubject": email_subject,
                "emailTemplate": email_template,
                "senderName": sender_name
            }
            
            # Send the email
            email_result = email_service.send_welcome_email(test_lead_data, email_config)
            
            if email_result["success"]:
                action_desc = f"Send Email: {email_subject} from {sender_name} - SUCCESS"
                logger.info(action_desc)
                execution_log.append(f"[{datetime.now().isoformat()}] {action_desc}")
                execution_log.append(f"[{datetime.now().isoformat()}] Email sent to: {test_lead_data['email']}")
            else:
                action_desc = f"Send Email: {email_subject} from {sender_name} - FAILED"
                logger.error(action_desc)
                execution_log.append(f"[{datetime.now().isoformat()}] {action_desc}")
                execution_log.append(f"[{datetime.now().isoformat()}] Error: {email_result['message']}")
            
        elif node_type == "updateStatus":
            # Simulate updating lead status
            new_status = node_data.get('status', 'Contacted')
            update_reason = node_data.get('updateReason', 'Workflow automation')
            
            action_desc = f"Update Status: {new_status} - {update_reason}"
            logger.info(action_desc)
            execution_log.append(f"[{datetime.now().isoformat()}] {action_desc}")
            
        else:
            action_desc = f"Unknown node type: {node_type}"
            logger.info(action_desc)
            execution_log.append(f"[{datetime.now().isoformat()}] {action_desc}")
    
    # Log connections
    for edge in workflow.edges:
        connection_desc = f"Connection: {edge.source} -> {edge.target}"
        logger.info(connection_desc)
        execution_log.append(f"[{datetime.now().isoformat()}] {connection_desc}")
    
    # Save workflow to storage
    workflow_data = {
        "id": workflow_id,
        "name": workflow.name,
        "description": workflow.description,
        "nodes": [node.model_dump() for node in workflow.nodes],
        "edges": [edge.model_dump() for edge in workflow.edges],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    workflows_data["workflows"].append(workflow_data)
    await save_workflows_to_file()
    
    return WorkflowResponse(
        message="Workflow executed successfully",
        workflow_id=workflow_id,
        execution_log=execution_log
    )

@app.post("/workflow/trigger-lead-created")
async def trigger_lead_created_workflow(lead_data: dict):
    """Trigger workflow when a new lead is created"""
    logger.info(f"Triggering workflow for new lead: {lead_data.get('name', 'Unknown')}")
    
    # Find workflows that start with "Lead Created" trigger
    triggered_workflows = []
    
    for workflow in workflows_data["workflows"]:
        # Check if workflow has a trigger node
        trigger_nodes = [node for node in workflow["nodes"] if node.get("data", {}).get("type") == "trigger"]
        
        if trigger_nodes:
            # Execute the workflow with lead data
            execution_log = []
            workflow_id = workflow["id"]
            
            logger.info(f"Executing workflow {workflow_id} for new lead")
            execution_log.append(f"[{datetime.now().isoformat()}] Triggered workflow: {workflow['name']}")
            execution_log.append(f"[{datetime.now().isoformat()}] Lead: {lead_data.get('name')} ({lead_data.get('email')})")
            
            # Process workflow nodes
            for node in workflow["nodes"]:
                node_type = node.get("data", {}).get("type")
                node_data = node.get("data", {})
                
                if node_type == "sendEmail":
                    # Send real welcome email using SendGrid
                    email_subject = node_data.get('emailSubject', 'Welcome to our CRM')
                    email_template = node_data.get('emailTemplate', 'Thank you for your interest!')
                    sender_name = node_data.get('senderName', 'CRM System')
                    
                    email_config = {
                        "emailSubject": email_subject,
                        "emailTemplate": email_template,
                        "senderName": sender_name
                    }
                    
                    # Send the email using real lead data
                    email_result = email_service.send_welcome_email(lead_data, email_config)
                    
                    if email_result["success"]:
                        action_desc = f"Send Welcome Email: {email_subject} to {lead_data.get('email')} - SUCCESS"
                        logger.info(action_desc)
                        execution_log.append(f"[{datetime.now().isoformat()}] {action_desc}")
                        execution_log.append(f"[{datetime.now().isoformat()}] Email sent successfully")
                    else:
                        action_desc = f"Send Welcome Email: {email_subject} to {lead_data.get('email')} - FAILED"
                        logger.error(action_desc)
                        execution_log.append(f"[{datetime.now().isoformat()}] {action_desc}")
                        execution_log.append(f"[{datetime.now().isoformat()}] Error: {email_result['message']}")
                    
                elif node_type == "updateStatus":
                    # Update lead status
                    new_status = node_data.get('status', 'Contacted')
                    update_reason = node_data.get('updateReason', 'Workflow automation')
                    
                    # Find and update the lead
                    for lead in leads_data:
                        if lead["id"] == lead_data.get("id"):
                            lead["status"] = new_status
                            await save_leads_to_file()
                            break
                    
                    action_desc = f"Updated lead status to: {new_status} - {update_reason}"
                    logger.info(action_desc)
                    execution_log.append(f"[{datetime.now().isoformat()}] {action_desc}")
            
            triggered_workflows.append({
                "workflow_id": workflow_id,
                "workflow_name": workflow["name"],
                "execution_log": execution_log
            })
    
    return {
        "message": f"Triggered {len(triggered_workflows)} workflows for new lead",
        "triggered_workflows": triggered_workflows,
        "lead_data": lead_data
    }

@app.post("/test-workflow")
async def test_workflow_trigger():
    """Test endpoint to manually trigger workflows"""
    test_lead = {
        "id": 999,
        "name": "Test Lead",
        "email": "test@example.com",
        "phone": "123-456-7890",
        "status": "New",
        "source": "Manual",
        "created_at": datetime.now().isoformat()
    }
    
    result = await trigger_lead_created_workflow(test_lead)
    return {
        "message": "Test workflow triggered",
        "result": result
    }

@app.get("/workflows")
async def get_workflows():
    """Get all saved workflows"""
    return workflows_data

@app.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a workflow by ID"""
    global workflows_data
    
    workflow_index = None
    for i, workflow in enumerate(workflows_data["workflows"]):
        if workflow["id"] == workflow_id:
            workflow_index = i
            break
    
    if workflow_index is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    deleted_workflow = workflows_data["workflows"].pop(workflow_index)
    await save_workflows_to_file()
    
    logger.info(f"Deleted workflow: {deleted_workflow['name']}")
    return SuccessResponse(message=f"Workflow {workflow_id} deleted successfully")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "leads_count": len(leads_data),
        "workflows_count": len(workflows_data["workflows"]),
        "olm_ocr_available": OLM_OCR_AVAILABLE
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Mini CRM API - Agentic AI Edition",
        "version": "2.0.0",
        "features": [
            "Enhanced Lead Management with Validation",
            "Tesseract OCR Document Processing",
            "Agentic LLM Interactions",
            "React Flow Workflow Designer",
            "Workflow Persistence and Execution"
        ],
        "olm_ocr_status": "Available" if OLM_OCR_AVAILABLE else "Not Available",
        "endpoints": {
            "leads": "/leads",
            "create_manual": "/leads/manual",
            "create_document": "/leads/document",
            "interact": "/interact",
            "workflow": "/workflow",
            "workflows": "/workflows"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 