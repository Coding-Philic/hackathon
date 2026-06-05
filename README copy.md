# MediOps AI: Autonomous Hospital IT Operations Agent

MediOps AI is an Agentic AI SRE (Site Reliability Engineering) platform designed to simulate a real-world hospital IT infrastructure environment. Instead of just highlighting issues, it implements a **LangGraph-driven agent** that actively investigates incidents, queries a **Qdrant Vector Database** memory bank to retrieve historical resolutions, executes recovery procedures, and verifies microservice health scores.

## Project Vision
Modern hospital environments depend on numerous interconnected software modules (EHR, LIS, Pharmacy, Billing, Auth, Database, API Gateways). A service failure directly halts patient care. 
MediOps AI demonstrates how hospitals can use autonomous agents with persistent vector memory to:
1. **Reduce MTTR (Mean Time to Resolution)** from hours to seconds.
2. **Preserve institutional knowledge** by capturing human engineering resolutions.
3. **Minimize diagnostic mistakes** by cross-referencing telemetry with vector indexes.

---

## System Architecture

```
                 React Dark-Mode Dashboard (Vite)
                              │
                              ▼
                       FastAPI Backend
                              │
                              ▼
                     Agent Orchestrator
                        (LangGraph)
                              │
                ┌─────────────┼──────────────┐
                ▼             ▼              ▼
           Vector Memory     LLM     Service Controller
             (Qdrant)                    Simulation Engine
                │                            │
                └─────────────┬──────────────┘
                              ▼
                 Simulated Hospital Services
```

- **React Dashboard**: Frost-glass analytics overview, manual controller override grids, SRE decision logs, and demo triggers.
- **FastAPI Backend**: Real-time REST endpoints, data validations, and CORS configurations.
- **Service Controller Simulation**: Background loops managing service states, updating uptimes, tracking errors, and feeding logging buffers.
- **Qdrant Vector memory**: Holds semantic embedding representations of incidents (Title, Symptoms, Root Causes, Solutions).
- **LangGraph Agent Loop**: Runs an active feedback loop: *Analyze Details* ➔ *Search Vector Memory* ➔ *Select Plan* ➔ *Execute Recovery Commands* ➔ *Verify Status* (Retry / Escalate) ➔ *Persist Resolution*.

---

## Quick Start (Docker)

To build and run all services in containerized mode (Postgres, Redis, Qdrant, Backend, Frontend):

1. **Configure environment:** (Optional) Edit `.env` to include OpenAI or Gemini keys if you wish to run full LLM evaluations. Otherwise, the local SRE rule engine handles diagnostics.
2. **Launch Compose:**
   ```bash
   docker-compose up --build -d
   ```
3. **Access Application:**
   - **Interactive UI Dashboard:** [http://localhost:3000](http://localhost:3000)
   - **FastAPI Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Qdrant Web UI Dashboard:** [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

---

## Quick Start (Local / No-Docker Developer Run)

To run the backend and frontend separately on your host system:

### 1. Start Backend (SQLite & Local Memory Mode)
The backend automatically falls back to SQLite and local semantic indexing if Postgres/Qdrant are not running.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Start Frontend
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## API Endpoints Reference

### Microservice Telemetry
- `GET /api/services`: Get real-time status of all 6 services.
- `POST /api/services/{name}/start`: Power on a service.
- `POST /api/services/{name}/stop`: Simulate server crash.
- `POST /api/services/{name}/degrade`: Inject latency/error load (takes `health_score` & `reason`).
- `GET /api/services/{name}/logs`: View logs for a service.

### Incident desk
- `GET /api/incidents`: Fetch the incidents queue.
- `POST /api/incidents`: Inject/report a new incident.
- `POST /api/incidents/{id}/resolve-manual`: Commit an engineer resolution, write to Qdrant memory, and clear the outage.

### Vector Memory
- `GET /api/memories`: View all memories timeline.
- `DELETE /api/memories/clear`: Flush all databases and vectors.

### Hackathon Demo Controller
- `POST /api/demo/1`: Cold Start scenario (Agent escalates).
- `POST /api/demo/2`: Autonomous Recall scenario (Agent self-heals).
- `POST /api/demo/3`: Scales logs/graphs and triggers active Pharmacy outage.
