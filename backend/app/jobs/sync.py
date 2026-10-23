"""CLI de sincronização: `uv run python -m app.jobs.sync [--etapas macro,cvm]`."""

import asyncio
import logging

import typer
from sqlalchemy import select

from app.core.errors import BusinessRuleError
from app.db.migrate import upgrade_db
from app.db.models import SyncRun
from app.db.session import SessionLocal
from app.services.sync import STEPS, parse_steps, run_full_sync

cli = typer.Typer(add_completion=False)


@cli.command()
def main(etapas: str = typer.Option("", help=f"{','.join(STEPS)} (vazio = todas)")) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        only = parse_steps(etapas)
    except BusinessRuleError as e:
        raise typer.BadParameter(str(e)) from e
    upgrade_db()
    with SessionLocal() as db:
        last_id = db.scalar(select(SyncRun.id).order_by(SyncRun.id.desc()).limit(1)) or 0
        if not asyncio.run(run_full_sync(db, only)):
            typer.echo("Já existe uma atualização em andamento.")
            raise typer.Exit(1)
        for r in db.scalars(select(SyncRun).where(SyncRun.id > last_id).order_by(SyncRun.id)):
            typer.echo(f"{r.source:<12} {r.status:<6} {r.rows:>7} linhas  {r.error or ''}")


if __name__ == "__main__":
    cli()
