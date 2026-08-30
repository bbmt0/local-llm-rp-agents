from fastapi import FastAPI, status, APIRouter, HTTPException, Depends
from pydantic import BaseModel
import uvicorn

router = APIRouter()

class HealthCheck(BaseModel):
    status: str = "OK"

@router.get("/health", response_model=HealthCheck)
def health_check() -> HealthCheck: 
    return HealthCheck(status="OK") 