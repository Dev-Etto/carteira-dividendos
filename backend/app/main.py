import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routers import aporte, ativos, carteira, painel, perfil, renda_fixa, sistema
from app.core.config import get_settings
from app.core.errors import DomainError
from app.db.migrate import upgrade_db
from app.db.session import SessionLocal
from app.jobs.scheduler import start_scheduler
from app.services.sync import load_sector_metrics, seed_universe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    upgrade_db()
    with SessionLocal() as db:
        seed_universe(db)
        load_sector_metrics(db)
    scheduler = start_scheduler() if get_settings().enable_scheduler else None
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="Carteira de Dividendos",
    version="0.1.0",
    description="Assistente local de investimentos em dividendos (método Barsi). Não é recomendação de investimento.",
    lifespan=lifespan,
    separate_input_output_schemas=False,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
for module in (painel, ativos, carteira, aporte, renda_fixa, perfil, sistema):
    app.include_router(module.router)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})
