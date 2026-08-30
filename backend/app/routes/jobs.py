from fastapi import APIRouter, HTTPException, Path
from backend.app.schemas.models import JobStatusResponse, PredictionResponse
from backend.app.jobs.manager import JobManager

router = APIRouter()

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str = Path(..., description="Unique background job ID")):
    """
    Returns the real-time status, progress percentage, and results of a training job.
    """
    job_info = JobManager.get_job(job_id)
    if not job_info:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    pred_res = None
    if job_info.get("result"):
        pred_res = PredictionResponse(**job_info["result"])

    return JobStatusResponse(
        job_id=job_info["job_id"],
        ticker=job_info["ticker"],
        status=job_info["status"],
        progress=job_info.get("progress", 0),
        stage=job_info.get("stage", ""),
        error=job_info.get("error"),
        created_at=job_info.get("created_at", ""),
        updated_at=job_info.get("updated_at", ""),
        prediction_result=pred_res
    )
