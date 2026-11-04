import asyncio
import logging
import os
import subprocess
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import google.auth.transport.requests
import google.oauth2.id_token
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from google.api_core.exceptions import NotFound
from google.cloud import bigquery
from pydantic import BaseModel, Field

from hotel_rules import HOTEL_RULES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hotel-rag-orchestrator")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "gcp-lab-513613")
REGION = os.getenv("GOOGLE_CLOUD_REGION", "europe-west1")
BQ_DATASET = os.getenv("BQ_DATASET", "hotel_rag")
BQ_TABLE = os.getenv("BQ_TABLE", "hotel_policies")
BQ_LOCATION = os.getenv("BQ_LOCATION", "europe-west1")

EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "").rstrip("/")
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "").rstrip("/")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "embeddinggemma-2:270m")
LLM_MODEL = os.getenv("LLM_MODEL", "SpeakLeash/bielik-4.5b-v3.0-instruct:Q8_0")

STATIC_DIR = Path(__file__).parent / "static"

TABLE_SCHEMA = [
    bigquery.SchemaField("rule_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("category", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("language", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("title", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("content", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
]

_token_cache: Dict[str, Dict[str, Any]] = {}
_seed_lock = asyncio.Lock()
_is_seeded = False


def get_bq_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)


def get_full_table_id() -> str:
    return f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"


def get_id_token_headers(target_url: str) -> Dict[str, str]:
    """Fetches a Google-signed OIDC ID token for private Cloud Run service-to-service calls."""
    if not target_url or target_url.startswith("http://localhost") or target_url.startswith("http://127.0.0.1"):
        return {}

    now = time.time()
    cached = _token_cache.get(target_url)
    if cached and cached["expires_at"] > now:
        return {"Authorization": f"Bearer {cached['token']}"}

    try:
        auth_req = google.auth.transport.requests.Request()
        token = google.oauth2.id_token.fetch_id_token(auth_req, target_url)
        _token_cache[target_url] = {"token": token, "expires_at": now + 1800}
        return {"Authorization": f"Bearer {token}"}
    except Exception as exc:
        logger.warning("Metadata ID token fetch failed for %s (%s); trying gcloud fallback.", target_url, exc)
        try:
            token = subprocess.check_output(
                ["gcloud", "auth", "print-identity-token"], text=True, timeout=5
            ).strip()
            if token:
                _token_cache[target_url] = {"token": token, "expires_at": now + 1800}
                return {"Authorization": f"Bearer {token}"}
        except Exception as sub_exc:
            logger.warning("gcloud identity token fallback failed: %s", sub_exc)
    return {}


async def generate_embedding(text: str) -> List[float]:
    """Generates a vector embedding for `text` using the Cloud Run Ollama Embedding Service."""
    if not EMBEDDING_SERVICE_URL:
        raise HTTPException(status_code=500, detail="EMBEDDING_SERVICE_URL is not configured.")

    headers = get_id_token_headers(EMBEDDING_SERVICE_URL)
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{EMBEDDING_SERVICE_URL}/api/embed",
            headers=headers,
            json={"model": EMBEDDING_MODEL, "input": text},
        )
        if resp.status_code == 404:
            # Fallback to legacy /api/embeddings endpoint if needed
            resp = await client.post(
                f"{EMBEDDING_SERVICE_URL}/api/embeddings",
                headers=headers,
                json={"model": EMBEDDING_MODEL, "prompt": text},
            )
        resp.raise_for_status()
        data = resp.json()
        if "embeddings" in data and data["embeddings"]:
            return [float(x) for x in data["embeddings"][0]]
        if "embedding" in data and data["embedding"]:
            return [float(x) for x in data["embedding"]]
        raise ValueError(f"Unexpected embedding payload from Ollama: {data}")


async def generate_llm_response(system_prompt: str, user_prompt: str) -> str:
    """Calls the Bielik LLM service on Cloud Run via Ollama /api/chat."""
    if not LLM_SERVICE_URL:
        raise HTTPException(status_code=500, detail="LLM_SERVICE_URL is not configured.")

    headers = get_id_token_headers(LLM_SERVICE_URL)
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": 0.15,
            "num_predict": 450,
        },
    }
    async with httpx.AsyncClient(timeout=240.0) as client:
        resp = await client.post(
            f"{LLM_SERVICE_URL}/api/chat",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        message = data.get("message", {})
        return message.get("content", "").strip()


def ensure_bq_dataset_and_table_sync() -> int:
    """Ensures the BigQuery dataset and table exist in BQ_LOCATION and returns current row count."""
    client = get_bq_client()
    dataset_ref = bigquery.Dataset(f"{PROJECT_ID}.{BQ_DATASET}")
    dataset_ref.location = BQ_LOCATION
    try:
        client.get_dataset(dataset_ref)
    except NotFound:
        logger.info("Creating BigQuery dataset %s in %s", BQ_DATASET, BQ_LOCATION)
        client.create_dataset(dataset_ref, exists_ok=True)

    table_id = get_full_table_id()
    table_ref = bigquery.Table(table_id, schema=TABLE_SCHEMA)
    try:
        table = client.get_table(table_ref)
    except NotFound:
        logger.info("Creating BigQuery table %s", table_id)
        table = client.create_table(table_ref, exists_ok=True)

    count_query = f"SELECT COUNT(*) AS total FROM `{table_id}` WHERE ARRAY_LENGTH(embedding) > 0"
    rows = list(client.query(count_query).result())
    return int(rows[0].total) if rows else 0


async def seed_hotel_rules(force: bool = False) -> Dict[str, Any]:
    """Generates embeddings for HOTEL_RULES and loads them into BigQuery."""
    global _is_seeded
    async with _seed_lock:
        existing_count = await asyncio.to_thread(ensure_bq_dataset_and_table_sync)
        if existing_count >= len(HOTEL_RULES) and not force:
            _is_seeded = True
            return {
                "status": "already_seeded",
                "rules_count": existing_count,
                "table": get_full_table_id(),
            }

        logger.info("Seeding %d hotel rules into BigQuery (%s)...", len(HOTEL_RULES), get_full_table_id())
        rows_to_load = []
        for rule in HOTEL_RULES:
            embed_input = f"{rule['category']} | {rule['title']}: {rule['content']}"
            vector = await generate_embedding(embed_input)
            rows_to_load.append(
                {
                    "rule_id": rule["rule_id"],
                    "category": rule["category"],
                    "language": rule["language"],
                    "title": rule["title"],
                    "content": rule["content"],
                    "embedding": vector,
                }
            )

        def _load_sync() -> None:
            client = get_bq_client()
            job_config = bigquery.LoadJobConfig(
                schema=TABLE_SCHEMA,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            )
            load_job = client.load_table_from_json(
                rows_to_load,
                get_full_table_id(),
                job_config=job_config,
            )
            load_job.result()

        await asyncio.to_thread(_load_sync)
        _is_seeded = True
        logger.info("Successfully seeded %d rules into %s", len(rows_to_load), get_full_table_id())
        return {
            "status": "seeded",
            "rules_count": len(rows_to_load),
            "embedding_dimension": len(rows_to_load[0]["embedding"]) if rows_to_load else 0,
            "table": get_full_table_id(),
        }


def run_vector_search_sync(
    query_embedding: List[float], top_k: int = 3, language: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Executes BigQuery VECTOR_SEARCH against the hotel_policies table, optionally filtered by language."""
    client = get_bq_client()
    table_id = get_full_table_id()
    if language in ("en", "pl"):
        base_source = f"(SELECT * FROM `{table_id}` WHERE language = @language)"
    else:
        base_source = f"TABLE `{table_id}`"

    sql = f"""
    SELECT
      base.rule_id AS rule_id,
      base.category AS category,
      base.language AS language,
      base.title AS title,
      base.content AS content,
      ROUND(1.0 - distance, 4) AS similarity,
      ROUND(distance, 4) AS distance
    FROM
      VECTOR_SEARCH(
        {base_source},
        'embedding',
        (SELECT @query_embedding AS embedding),
        top_k => @top_k,
        distance_type => 'COSINE'
      )
    ORDER BY distance ASC
    """
    params: List[Any] = [
        bigquery.ArrayQueryParameter("query_embedding", "FLOAT64", query_embedding),
        bigquery.ScalarQueryParameter("top_k", "INT64", top_k),
    ]
    if language in ("en", "pl"):
        params.append(bigquery.ScalarQueryParameter("language", "STRING", language))
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    results = client.query(sql, job_config=job_config).result()
    retrieved = []
    for row in results:
        retrieved.append(
            {
                "rule_id": row.rule_id,
                "category": row.category,
                "language": row.language,
                "title": row.title,
                "content": row.content,
                "similarity": float(row.similarity) if row.similarity is not None else 0.0,
                "distance": float(row.distance) if row.distance is not None else 1.0,
            }
        )
    return retrieved


def list_rules_from_bq_sync(language: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists stored hotel rules from BigQuery."""
    client = get_bq_client()
    table_id = get_full_table_id()
    if language and language in ("en", "pl"):
        sql = f"""
        SELECT rule_id, category, language, title, content, ARRAY_LENGTH(embedding) AS embedding_dim
        FROM `{table_id}`
        WHERE language = @language
        ORDER BY rule_id ASC
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("language", "STRING", language)]
        )
    else:
        sql = f"""
        SELECT rule_id, category, language, title, content, ARRAY_LENGTH(embedding) AS embedding_dim
        FROM `{table_id}`
        ORDER BY rule_id ASC
        """
        job_config = bigquery.QueryJobConfig()

    rows = client.query(sql, job_config=job_config).result()
    return [
        {
            "rule_id": r.rule_id,
            "category": r.category,
            "language": r.language,
            "title": r.title,
            "content": r.content,
            "embedding_dim": int(r.embedding_dim) if r.embedding_dim is not None else 0,
        }
        for r in rows
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        if EMBEDDING_SERVICE_URL:
            await seed_hotel_rules(force=False)
    except Exception as exc:
        logger.warning("Initial startup seeding deferred: %s", exc)
    yield


app = FastAPI(
    title="Hotel Employee Policy Assistant (Sovereign RAG)",
    description="Serverless Sovereign RAG on Google Cloud Run + BigQuery VECTOR_SEARCH + Bielik 4.5B v3.0 + EmbeddingGemma",
    version="1.0.0",
    lifespan=lifespan,
)


class AskRequest(BaseModel):
    prompt: str = Field(..., min_length=2, max_length=1500)
    language: str = Field(default="en", pattern="^(en|pl)$")
    top_k: int = Field(default=3, ge=1, le=8)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "project": PROJECT_ID,
        "region": REGION,
        "bigquery_table": get_full_table_id(),
        "embedding_model": EMBEDDING_MODEL,
        "llm_model": LLM_MODEL,
        "embedding_service_configured": bool(EMBEDDING_SERVICE_URL),
        "llm_service_configured": bool(LLM_SERVICE_URL),
    }


@app.get("/api/rules")
async def get_rules(language: Optional[str] = Query(default=None)):
    try:
        if not _is_seeded and EMBEDDING_SERVICE_URL:
            await seed_hotel_rules(force=False)
        rules = await asyncio.to_thread(list_rules_from_bq_sync, language)
        if not rules:
            # Fallback to static definitions if BigQuery table is currently empty
            filtered = [
                {**r, "embedding_dim": 0}
                for r in HOTEL_RULES
                if not language or r["language"] == language
            ]
            return {"rules": filtered, "source": "static_fallback", "table": get_full_table_id()}
        return {"rules": rules, "source": "bigquery", "table": get_full_table_id()}
    except Exception as exc:
        logger.exception("Failed to fetch rules from BigQuery")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/seed")
async def trigger_seed(force: bool = Query(default=False)):
    try:
        result = await seed_hotel_rules(force=force)
        return JSONResponse(status_code=200, content=result)
    except Exception as exc:
        logger.exception("Seeding failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/ask")
async def ask_policy_assistant(req: AskRequest):
    t0 = time.perf_counter()
    try:
        if not _is_seeded:
            await seed_hotel_rules(force=False)

        # 1. Embed user query
        t_embed_start = time.perf_counter()
        query_vector = await generate_embedding(req.prompt)
        embed_ms = round((time.perf_counter() - t_embed_start) * 1000)

        # 2. Retrieve relevant hotel rules via BigQuery VECTOR_SEARCH
        t_bq_start = time.perf_counter()
        retrieved_rules = await asyncio.to_thread(
            run_vector_search_sync, query_vector, req.top_k, req.language
        )
        bq_ms = round((time.perf_counter() - t_bq_start) * 1000)

        context_lines = []
        for idx, r in enumerate(retrieved_rules, start=1):
            context_lines.append(
                f"[{idx}] Rule ID: {r['rule_id']} ({r['category']} | lang={r['language']} | similarity={r['similarity']})\n"
                f"Title: {r['title']}\n"
                f"Policy: {r['content']}"
            )
        context_block = "\n\n".join(context_lines)

        if req.language == "pl":
            direct_system = (
                "Jesteś pomocnym asystentem hotelowym. Odpowiedz zwięźle po polsku (w 2-4 zdaniach) na pytanie pracownika. "
                "Nie posiadasz dostępu do wewnętrznych dokumentów ani tajnych kodów Hotelu Bałtycki Suweren – jeśli pytanie dotyczy "
                "wewnętrznych kodów VIP, kodów POS lub specyficznych stawek tego hotelu, poinformuj wprost, że nie znasz wewnętrznego regulaminu."
            )
            grounded_system = (
                "Jesteś oficjalnym Asystentem Regulaminu Pracowniczego Hotelu Bałtycki Suweren (Grand Baltic Sovereign Hotel). "
                "Odpowiedz na pytanie pracownika precyzyjnie i zwięźle po polsku, opierając się WYŁĄCZNIE na poniższych zasadach pobranych z bazy BigQuery VECTOR_SEARCH. "
                "Zawsze podawaj dokładne kody (np. VIP, POS, numery wewnętrzne), kwoty opłat (PLN/EUR) oraz identyfikator zasady (Rule ID).\n\n"
                f"POBRANE ZASADY HOTELOWE:\n{context_block}"
            )
        else:
            direct_system = (
                "You are a helpful hotel assistant. Answer the employee's question concisely in English (2-4 sentences). "
                "You do NOT have access to internal documents or confidential codes of Grand Baltic Sovereign Hotel—if the question asks for "
                "specific internal VIP codes, POS override codes, or exact hotel fee schedules, state clearly that you do not have access to those internal policies."
            )
            grounded_system = (
                "You are the official Employee Policy Assistant for Grand Baltic Sovereign Hotel (Hotel Bałtycki Suweren). "
                "Answer the employee's question accurately and concisely in English using ONLY the official hotel policies retrieved from BigQuery VECTOR_SEARCH below. "
                "Always cite the exact codes (VIP codes, POS override codes, extensions), exact fee amounts (PLN/EUR), and the corresponding Rule ID.\n\n"
                f"RETRIEVED HOTEL POLICIES:\n{context_block}"
            )

        # 3. Call Bielik LLM for both Direct (No RAG) and Grounded (With RAG)
        t_llm_start = time.perf_counter()
        direct_answer, grounded_answer = await asyncio.gather(
            generate_llm_response(direct_system, req.prompt),
            generate_llm_response(grounded_system, req.prompt),
        )
        llm_ms = round((time.perf_counter() - t_llm_start) * 1000)
        total_ms = round((time.perf_counter() - t0) * 1000)

        return {
            "prompt": req.prompt,
            "language": req.language,
            "direct_answer": direct_answer,
            "grounded_answer": grounded_answer,
            "retrieved_rules": retrieved_rules,
            "models": {
                "embedding": EMBEDDING_MODEL,
                "llm": LLM_MODEL,
            },
            "timings_ms": {
                "embedding": embed_ms,
                "bigquery_vector_search": bq_ms,
                "llm_generation": llm_ms,
                "total": total_ms,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error processing /api/ask")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/")
async def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
