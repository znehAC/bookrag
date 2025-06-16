import logging
import pathlib
from contextlib import asynccontextmanager

from fastapi import APIRouter, BackgroundTasks, FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.core import ChatSession
from agent.tools import registry
from config import settings
from rag.chunk import chunk_text
from rag.db import PgVectorStore, init_db
from rag.embed import embed

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

BOOK_FILE = pathlib.Path("data/origin.txt")
store = PgVectorStore(settings.POSTGRES_URL)
_sessions: dict[str, ChatSession] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug("initializing db")
    init_db()
    _maybe_ingest()
    yield


def _session(chat_id: str) -> ChatSession:
    if chat_id not in _sessions:
        logger.info(f"creating session {chat_id}")
        _sessions[chat_id] = ChatSession(chat_id, registry)
    return _sessions[chat_id]


class ChatRequest(BaseModel):
    chat_id: str
    prompt: str


def _maybe_ingest():
    with store.conn.cursor() as cur:
        cur.execute("select 1 from chunks limit 1;")
        already = cur.fetchone() is not None
    if already:
        logger.info("vector story already populated")
        return
    logger.info("building vector store")
    with open(BOOK_FILE, "r") as file:
        text = file.read()
    chunks = chunk_text(text, max_tokens=500)
    vecs = embed(chunks)
    store.add(chunks, vecs)
    logger.info("ingested %s chunks ✔", len(chunks))


app = FastAPI(lifespan=lifespan)
router = APIRouter()


@router.post("/completion")
async def completion(req: ChatRequest, bg: BackgroundTasks):
    session = _session(req.chat_id)

    async def token_stream():
        try:
            async for chunk in session.run(req.prompt):
                yield chunk
        except Exception:
            logger.error("chat loop crashed", exc_info=True)
            yield "\nAlgum erro ocorreu, tente novamente"

    return StreamingResponse(token_stream(), media_type="text/plain")


@router.get("/{chat_id}/history")
async def history(chat_id: str):
    session = _sessions.get(chat_id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "chat_id sem sessão ativa")
    return session.memory.get()


app.include_router(router, prefix="/chat")
