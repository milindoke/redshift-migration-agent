#!/usr/bin/env python3
"""
FastAPI server for Redshift Migration Agent

Provides a REST API interface to the agent for remote access.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from redshift_agent import create_agent
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Redshift Migration Agent API",
    description="AI-powered assistant for migrating AWS Redshift Provisioned to Serverless",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent (done once at startup)
logger.info("Initializing Redshift Migration Agent...")
agent = create_agent()
logger.info("Agent initialized successfully")


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    session_id: Optional[str] = None
    

class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    session_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    agent_ready: bool


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Redshift Migration Agent API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/chat",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        agent_ready=agent is not None
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the Redshift Migration Agent.
    
    The agent can help with:
    - Listing Redshift clusters and namespaces
    - Extracting cluster configurations
    - Planning migrations
    - Executing full migrations
    - Troubleshooting issues
    
    Example request:
    ```json
    {
        "message": "List all my Redshift clusters in us-east-2",
        "session_id": "user-123"
    }
    ```
    """
    try:
        logger.info(f"Received message: {request.message[:100]}...")
        
        # Get response from agent
        response = agent(request.message)
        
        logger.info(f"Generated response: {response[:100]}...")
        
        return ChatResponse(
            response=response,
            session_id=request.session_id
        )
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )


@app.post("/reset")
async def reset_conversation():
    """
    Reset the agent's conversation history.
    
    This creates a fresh agent instance with no prior context.
    """
    global agent
    try:
        logger.info("Resetting agent conversation...")
        agent = create_agent()
        logger.info("Agent reset successfully")
        return {"status": "success", "message": "Conversation reset"}
    except Exception as e:
        logger.error(f"Error resetting agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error resetting agent: {str(e)}"
        )


if __name__ == "__main__":
    import sys
    
    # Get port from command line or use default
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    
    logger.info(f"Starting Redshift Migration Agent API on port {port}")
    logger.info(f"API docs available at http://localhost:{port}/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
