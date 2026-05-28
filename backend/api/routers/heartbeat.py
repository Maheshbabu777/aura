from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.heartbeat.morning_brief import MorningBriefGenerator

router = APIRouter(prefix="/api/brief", tags=["Heartbeat"])

class BriefResponse(BaseModel):
    brief: str
    status: str

@router.get("/generate", response_model=BriefResponse)
async def generate_morning_brief(use_cloud: bool = False):
    """
    Generate the daily morning brief.
    This is an on-demand endpoint for testing/manual triggering before the background scheduler is built.
    """
    try:
        generator = MorningBriefGenerator(use_cloud=use_cloud)
        brief = generator.generate()
        
        return BriefResponse(
            brief=brief,
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
