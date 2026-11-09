from fastapi import APIRouter

router = APIRouter(prefix="/api/dialogs", tags=["dialogs"])

@router.get("/")
async def list_dialogs():
    return {"message": "List of dialogs will be here"}
