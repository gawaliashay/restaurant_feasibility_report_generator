# app\main.py

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
import os
from datetime import datetime

from src.workflow.research_orchestrator import RestaurantResearchSystem
from graph_states.workflow_states import WorkflowState

app = FastAPI(
    title="Restaurant Market Research API",
    description="AI-powered market research for restaurant investments",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for research jobs (use Redis in production)
research_jobs = {}

# Pydantic models
class ResearchRequest(BaseModel):
    restaurant_concept: str
    target_location: str
    investment: str
    target_demographic: str
    max_analysts: int = 4
    special_note: str = ""

class ResearchResponse(BaseModel):
    report_id: str
    status: str
    message: str
    created_at: str
    estimated_completion: str

class ResearchStatus(BaseModel):
    report_id: str
    status: str
    progress: str
    current_stage: str
    created_at: str
    updated_at: str

class DownloadResponse(BaseModel):
    report_id: str
    format: str
    download_url: str
    file_size: int

# Health check
@app.get("/")
async def root():
    return {
        "message": "Restaurant Market Research API", 
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Research endpoints
@app.post("/research/start", response_model=ResearchResponse)
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """Start a new restaurant market research analysis"""
    
    report_id = str(uuid.uuid4())
    
    research_jobs[report_id] = {
        "status": "queued",
        "progress": "0%",
        "current_stage": "Initializing",
        "request": request.dict(),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "result": None,
        "error": None
    }
    
    # Start research in background
    background_tasks.add_task(execute_research, report_id, request)
    
    return ResearchResponse(
        report_id=report_id,
        status="queued",
        message="Research analysis started successfully",
        created_at=research_jobs[report_id]["created_at"],
        estimated_completion="5-10 minutes"
    )

@app.get("/research/status/{report_id}", response_model=ResearchStatus)
async def get_research_status(report_id: str):
    """Check status of research analysis"""
    
    if report_id not in research_jobs:
        raise HTTPException(status_code=404, detail="Research job not found")
    
    job = research_jobs[report_id]
    
    return ResearchStatus(
        report_id=report_id,
        status=job["status"],
        progress=job["progress"],
        current_stage=job["current_stage"],
        created_at=job["created_at"],
        updated_at=job["updated_at"]
    )

@app.get("/reports/{report_id}/download")
async def download_report(report_id: str, format: str = "md"):
    """Download generated research report"""
    
    if report_id not in research_jobs:
        raise HTTPException(status_code=404, detail="Research job not found")
    
    job = research_jobs[report_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Research not completed yet")
    
    if not job["result"] or "export_paths" not in job["result"]:
        raise HTTPException(status_code=404, detail="Report files not found")
    
    export_paths = job["result"].get("export_paths", {})
    
    if format not in export_paths:
        raise HTTPException(status_code=400, detail=f"Format {format} not available")
    
    file_path = export_paths[format]
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    file_size = os.path.getsize(file_path)
    
    return FileResponse(
        path=file_path,
        filename=f"restaurant_research_report_{report_id}.{format}",
        media_type="application/octet-stream"
    )

@app.get("/reports/{report_id}/formats")
async def get_available_formats(report_id: str):
    """Get available download formats for a report"""
    
    if report_id not in research_jobs:
        raise HTTPException(status_code=404, detail="Research job not found")
    
    job = research_jobs[report_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Research not completed yet")
    
    export_paths = job["result"].get("export_paths", {})
    
    return {
        "report_id": report_id,
        "available_formats": list(export_paths.keys()),
        "download_urls": {
            format: f"/reports/{report_id}/download?format={format}" 
            for format in export_paths.keys()
        }
    }

# Background task function
async def execute_research(report_id: str, request: ResearchRequest):
    """Execute research in background"""
    
    try:
        # Update status
        research_jobs[report_id].update({
            "status": "in_progress",
            "progress": "10%",
            "current_stage": "Creating analyst team",
            "updated_at": datetime.now().isoformat()
        })
        
        # Initialize research system
        system = RestaurantResearchSystem()
        
        # Create research state
        research_state = WorkflowState(
            restaurant_concept=request.restaurant_concept,
            target_location=request.target_location,
            investment=request.investment,
            target_demographic=request.target_demographic,
            max_analysts=request.max_analysts,
            special_note=request.special_note,
            # Initialize other required fields
            dynamic_analysts=[],
            analysts_team=[],
            research_tasks=[],
            research_results={},
            research_summary={},
            executive_summary="",
            market_analysis="",
            financial_recommendations="",
            risk_assessment="",
            final_report={},
            export_paths={},
            accept=False,
            extra_instructions="",
            retry_count=0,
            current_task=None,
            current_analyst=None
        )
        
        # Update progress
        research_jobs[report_id].update({
            "progress": "30%",
            "current_stage": "Conducting market research",
            "updated_at": datetime.now().isoformat()
        })
        
        # Execute research
        result = system.run_research(research_state)
        
        # Update with results
        research_jobs[report_id].update({
            "status": "completed",
            "progress": "100%",
            "current_stage": "Report generation completed",
            "result": result,
            "updated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        # Update with error
        research_jobs[report_id].update({
            "status": "failed",
            "progress": "0%",
            "current_stage": "Error occurred",
            "error": str(e),
            "updated_at": datetime.now().isoformat()
        })

# List all research jobs (admin endpoint)
@app.get("/admin/research-jobs")
async def list_research_jobs(limit: int = 10):
    """List all research jobs (admin only)"""
    
    jobs = list(research_jobs.items())[-limit:]
    
    return {
        "total_jobs": len(research_jobs),
        "jobs": [
            {
                "report_id": report_id,
                "status": job["status"],
                "concept": job["request"]["restaurant_concept"],
                "created_at": job["created_at"]
            }
            for report_id, job in jobs
        ]
    }