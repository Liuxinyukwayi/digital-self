from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.api.v1 import api_router
from app.models.models import User

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup() -> None:
    Base.metadata.create_all(bind=engine)

    from sqlalchemy import text, inspect
    with engine.connect() as conn:
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("memories")]
        if "evidence_count" not in columns:
            conn.execute(text("ALTER TABLE memories ADD COLUMN evidence_count INTEGER DEFAULT 1"))
            conn.commit()
        if "confidence" not in columns:
            conn.execute(text("ALTER TABLE memories ADD COLUMN confidence FLOAT DEFAULT 0.5"))
            conn.commit()
        if "last_evidence_at" not in columns:
            conn.execute(text("ALTER TABLE memories ADD COLUMN last_evidence_at DATETIME"))
            conn.commit()

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == settings.DEFAULT_USER_ID).first()
        if not user:
            db.add(
                User(
                    id=settings.DEFAULT_USER_ID,
                    username=settings.DEFAULT_USER_NAME,
                    display_name="用户",
                    persona_data={},
                )
            )
            db.commit()
    finally:
        db.close()

    from app.services.queue.task_queue import get_task_queue
    tq = get_task_queue()
    await tq.start()

    from app.services.embedding.embedding_service import check_and_init_embedding
    await check_and_init_embedding()


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
