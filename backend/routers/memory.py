from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

try:
    from backend.database import get_db
    from backend import models, schemas, memory
except ImportError:
    from database import get_db
    import models, schemas, memory

router = APIRouter(prefix="/memories", tags=["Memory Timeline"])

@router.get("/", response_model=List[schemas.MemoryEntryInDB])
def list_memories(db: Session = Depends(get_db)):
    return db.query(models.MemoryEntry).order_by(models.MemoryEntry.timestamp.desc()).all()

@router.get("/search")
def search_vector_memories(
    title: str = Query(..., description="Incident title to search"),
    symptoms: str = Query(..., description="Symptoms to search"),
    db: Session = Depends(get_db)
):
    matches = memory.search_memories(db, title, symptoms, limit=5)
    return matches

@router.delete("/clear")
def clear_memories(db: Session = Depends(get_db)):
    # 1. Clear PostgreSQL memory entries
    db.query(models.MemoryEntry).delete()
    # Also delete active incidents to clean the board
    db.query(models.IncidentAction).delete()
    db.query(models.AgentDecision).delete()
    db.query(models.Incident).delete()
    db.query(models.ServiceLog).delete()
    
    # 2. Reset service states to Running 100%
    services = db.query(models.Service).all()
    for s in services:
        s.status = "Running"
        s.health_score = 100
        s.error_count = 0
        
    db.commit()
    
    # 3. Clear Qdrant Collection
    global qdrant_client
    if memory.qdrant_client:
        try:
            memory.qdrant_client.delete_collection(collection_name=memory.COLLECTION_NAME)
            memory.init_qdrant_collection()
        except Exception as e:
            print(f"Failed to clear Qdrant collection: {e}")
            
    return {"message": "All database tables, vector collections, and incident logs cleared successfully."}
