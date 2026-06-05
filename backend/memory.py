import uuid
import logging
import datetime
import hashlib
from sqlalchemy.orm import Session
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import UnexpectedResponse

try:
    from backend.config import settings
    from backend import models
except ImportError:
    from config import settings
    import models

logger = logging.getLogger(__name__)

# Try connecting to Qdrant
qdrant_client = None
try:
    qdrant_client = QdrantClient(url=settings.QDRANT_URL, timeout=5)
    # Check health
    qdrant_client.get_collections()
    logger.info("Connected to Qdrant successfully.")
except Exception as e:
    logger.warning(f"Failed to connect to Qdrant at {settings.QDRANT_URL}. Falling back to DB-only memory: {e}")
    qdrant_client = None

COLLECTION_NAME = "incident_memories"
VECTOR_SIZE = 1536  # Default dimension for text-embedding-3-small / our mock embeddings

def init_qdrant_collection():
    """Initializes the Qdrant collection if it does not exist."""
    global qdrant_client
    if not qdrant_client:
        return
    try:
        collections = qdrant_client.get_collections().collections
        exists = any(c.name == COLLECTION_NAME for c in collections)
        if not exists:
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=qmodels.VectorParams(
                    size=VECTOR_SIZE,
                    distance=qmodels.Distance.COSINE
                )
            )
            logger.info(f"Created Qdrant collection: {COLLECTION_NAME}")
    except Exception as e:
        logger.error(f"Error initializing Qdrant collection: {e}")
        qdrant_client = None

# Initialize collection if qdrant is online
init_qdrant_collection()

def get_deterministic_mock_embedding(text: str, dimensions: int = VECTOR_SIZE) -> list:
    """Generates a deterministic 1536-dimensional mock embedding based on SHA256 of text words.
    Enables similarity search in Qdrant without requiring external LLM API keys.
    """
    vector = [0.0] * dimensions
    words = text.lower().split()
    if not words:
        words = ["empty"]
        
    for i, word in enumerate(words):
        # Generate hash for the word
        h = hashlib.sha256(word.encode()).hexdigest()
        val = int(h[:8], 16) / 4294967295.0  # Normalize to [0, 1]
        
        # Determine the index (deterministic mapping)
        index = int(h[8:16], 16) % dimensions
        # Distribute based on word position
        weight = 1.0 / (i + 1)
        vector[index] += val * weight
        
        # Add side weights to adjacent elements for smoothness
        vector[(index - 1) % dimensions] += val * weight * 0.1
        vector[(index + 1) % dimensions] += val * weight * 0.1

    # Normalize vector to unit length (for Cosine Distance consistency)
    magnitude = sum(x*x for x in vector) ** 0.5
    if magnitude > 0:
        vector = [x / magnitude for x in vector]
    else:
        vector[0] = 1.0
        
    return vector

def get_text_embedding(text: str) -> list:
    """Generates embeddings using OpenAI, Gemini, or our deterministic mock generator."""
    if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.embeddings.create(
                input=[text],
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"OpenAI embedding generation failed: {e}. Falling back to mock.")
            
    elif settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        try:
            # Import gemini client / langchain
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=settings.GEMINI_API_KEY)
            # Embedding size is 768 for models/embedding-001, we pad/truncate to VECTOR_SIZE if needed,
            # or we adjust collection if we know it. Let's make it robust by padding to 1536 if needed.
            vec = embeddings.embed_query(text)
            if len(vec) < VECTOR_SIZE:
                return vec + [0.0] * (VECTOR_SIZE - len(vec))
            return vec[:VECTOR_SIZE]
        except Exception as e:
            logger.warning(f"Gemini embedding generation failed: {e}. Falling back to mock.")

    # Fallback to local high-fidelity mock vector
    return get_deterministic_mock_embedding(text)

def store_memory(db: Session, title: str, symptoms: str, affected_services: str, root_cause: str, resolution: str, actions_executed: list, success_rate: float = 1.0) -> models.MemoryEntry:
    """Stores incident resolution memory both in PostgreSQL and Qdrant vector database."""
    global qdrant_client
    
    # Check if duplicate memory exists in SQL to avoid cluttering
    existing = db.query(models.MemoryEntry).filter_by(title=title).first()
    if existing:
        # Update success rate or actions
        existing.success_rate = (existing.success_rate + success_rate) / 2
        existing.timestamp = datetime.datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
        
    vector_id = str(uuid.uuid4())
    actions_str = ",".join(actions_executed) if isinstance(actions_executed, list) else actions_executed
    
    # 1. Store in PostgreSQL
    db_entry = models.MemoryEntry(
        title=title,
        symptoms=symptoms,
        affected_services=affected_services,
        root_cause=root_cause,
        resolution=resolution,
        actions_executed=actions_str,
        success_rate=success_rate,
        vector_id=vector_id,
        timestamp=datetime.datetime.utcnow()
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    
    # 2. Store in Qdrant
    if qdrant_client:
        try:
            # Combine content for indexing
            text_to_embed = f"Title: {title}\nSymptoms: {symptoms}\nAffected Services: {affected_services}\nRoot Cause: {root_cause}\nResolution: {resolution}"
            vector = get_text_embedding(text_to_embed)
            
            qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    qmodels.PointStruct(
                        id=vector_id,
                        vector=vector,
                        payload={
                            "title": title,
                            "symptoms": symptoms,
                            "affected_services": affected_services,
                            "root_cause": root_cause,
                            "resolution": resolution,
                            "actions_executed": actions_str,
                            "success_rate": success_rate,
                            "sql_id": db_entry.id
                        }
                    )
                ]
            )
            logger.info(f"Upserted memory to Qdrant with vector_id: {vector_id}")
        except Exception as e:
            logger.error(f"Failed to upsert memory to Qdrant: {e}")
            
    return db_entry

def search_memories(db: Session, title: str, symptoms: str, limit: int = 5) -> list:
    """Retrieves top matches from Qdrant vector store. Falls back to SQL text search if Qdrant is down."""
    global qdrant_client
    
    text_to_search = f"Title: {title}\nSymptoms: {symptoms}"
    
    # Option A: Vector Search via Qdrant
    if qdrant_client:
        try:
            # Recheck collection exists (handles Qdrant restart)
            init_qdrant_collection()
            query_vector = get_text_embedding(text_to_search)
            
            results = qdrant_client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vector,
                limit=limit
            )
            
            hits = []
            for hit in results:
                payload = hit.payload
                actions = payload.get("actions_executed", "").split(",") if payload.get("actions_executed") else []
                hits.append({
                    "id": payload.get("sql_id"),
                    "title": payload.get("title"),
                    "symptoms": payload.get("symptoms"),
                    "affected_services": payload.get("affected_services"),
                    "root_cause": payload.get("root_cause"),
                    "resolution": payload.get("resolution"),
                    "actions_executed": actions,
                    "success_rate": payload.get("success_rate", 1.0),
                    "score": hit.score
                })
            return hits
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}. Falling back to DB search.")
            
    # Option B: Fallback DB keyword overlap similarity
    # Simple word overlap similarity calculation
    db_memories = db.query(models.MemoryEntry).all()
    hits = []
    
    query_words = set(text_to_search.lower().replace("\n", " ").replace(":", "").split())
    for mem in db_memories:
        mem_text = f"{mem.title} {mem.symptoms} {mem.affected_services}".lower()
        mem_words = set(mem_text.split())
        
        # Calculate overlap
        intersection = query_words.intersection(mem_words)
        union = query_words.union(mem_words)
        score = len(intersection) / len(union) if union else 0.0
        
        actions = mem.actions_executed.split(",") if mem.actions_executed else []
        hits.append({
            "id": mem.id,
            "title": mem.title,
            "symptoms": mem.symptoms,
            "affected_services": mem.affected_services,
            "root_cause": mem.root_cause,
            "resolution": mem.resolution,
            "actions_executed": actions,
            "success_rate": mem.success_rate,
            "score": score
        })
        
    # Sort by score descending and return limit
    hits.sort(key=lambda x: x["score"], reverse=True)
    return hits[:limit]
