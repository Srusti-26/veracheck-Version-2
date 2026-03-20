"""Facts CRUD API routes."""
from fastapi import APIRouter, Request, HTTPException
from models.schemas import FactCreateRequest

router = APIRouter()


@router.get("/")
async def list_facts(request: Request):
    fact_store = request.app.state.fact_store
    return {"facts": fact_store.get_all_facts(), "total": fact_store.count}


@router.post("/")
async def create_fact(request: Request, body: FactCreateRequest):
    fact_store = request.app.state.fact_store
    fact_id = fact_store.add_fact(body.model_dump())
    pipeline = request.app.state.pipeline
    await fact_store.build_index(pipeline.embedding_service)
    return {"id": fact_id, "status": "created"}


@router.delete("/{fact_id}")
async def delete_fact(request: Request, fact_id: str):
    fact_store = request.app.state.fact_store
    if not fact_store.delete_fact(fact_id):
        raise HTTPException(status_code=404, detail="Fact not found")
    return {"status": "deleted"}
