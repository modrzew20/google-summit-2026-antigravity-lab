# Hotel Employee Policy Assistant — Serverless Sovereign RAG

A serverless, sovereign Retrieval-Augmented Generation (RAG) system on Google Cloud (`europe-west1`) for hotel staff policy queries in English and Polish.

## Architecture & Live Services (`gcp-lab-513613` / `europe-west1`)

1. **Embedding Service (`bielik-embed` — Cloud Run, CPU-only)**:
   - URL: `https://bielik-embed-780527536391.europe-west1.run.app` (private OIDC)
   - Model: `embeddinggemma-2:270m` baked into an Ollama container (`embedding-service/Dockerfile`).
   - Resources: `--cpu=8 --memory=16Gi --max-instances=1 --no-allow-unauthenticated`.
2. **LLM Service (`bielik-llm` — Cloud Run, NVIDIA L4 GPU)**:
   - URL: `https://bielik-llm-780527536391.europe-west1.run.app` (private OIDC)
   - Model: `SpeakLeash/bielik-4.5b-v3.0-instruct:Q8_0` baked into an Ollama container (`llm-service/Dockerfile`).
   - Resources: `--gpu=1 --gpu-type=nvidia-l4 --no-gpu-zonal-redundancy --cpu=4 --memory=16Gi --max-instances=1 --no-allow-unauthenticated` (with `--cpu=8 --memory=16Gi` CPU fallback if GPU quota is unavailable).
3. **Vector Database (BigQuery `VECTOR_SEARCH`)**:
   - Dataset & Table: `gcp-lab-513613.hotel_rag.hotel_policies` in `europe-west1`.
   - Stores parallel English (`en`) and Polish (`pl`) fictional hotel rules (VIP codes `AMBER-77`, `SAPPHIRE-12`, `CORAL-05`, pet fees, late checkout POS codes, and security protocols) alongside their 768-dimensional `embeddinggemma-2:270m` vector embeddings.
4. **Web UI & Orchestrator (`hotel-rag-ui` — Cloud Run, CPU-only)**:
   - URL: `https://hotel-rag-ui-780527536391.europe-west1.run.app` (public Web UI)
   - FastAPI application (`orchestrator/main.py`) serving a bilingual (`EN`/`PL`) single-page UI (`orchestrator/static/index.html`).
   - Compares **Direct Model (No RAG)** vs. **Grounded Model (With RAG)** side by side and provides a **Hotel Rules** browser tab.
