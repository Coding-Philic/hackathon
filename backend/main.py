from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

try:
    from backend.database import engine, Base, SessionLocal
    from backend import models, simulator
    from backend.routers import services, incidents, memory, analytics, demo
except ImportError:
    from database import engine, Base, SessionLocal
    import models, simulator
    from routers import services, incidents, memory, analytics, demo

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Create SQL database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created successfully.")
except Exception as e:
    logger.error(f"Error creating database tables: {e}")

app = FastAPI(
    title="MediOps AI Autonomous Incident Response Agent",
    description="Backend simulating hospital IT infrastructure and SRE Agent workflow",
    version="1.0.0"
)

# Enable CORS for Vite Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup & Shutdown hooks
@app.on_event("startup")
def startup_event():
    # Initialize service states in DB
    db = SessionLocal()
    try:
        simulator.init_services(db)
    finally:
        db.close()
    
    # Start the simulator background thread
    simulator.start_simulator()
    logger.info("Background SRE simulator started.")

@app.on_event("shutdown")
def shutdown_event():
    # Stop the background thread
    simulator.stop_simulator_flag = True
    logger.info("Background SRE simulator flagged for shutdown.")

# Register routers
app.include_router(services.router, prefix="/api")
app.include_router(incidents.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(demo.router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "MediOps AI Backend Engine",
        "engine": "LangGraph SRE Agent",
        "vector_store": "Qdrant"
    }
