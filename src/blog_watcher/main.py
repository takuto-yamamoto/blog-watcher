from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import httpx
import typer

from blog_watcher.config import ConfigError, load_config
from blog_watcher.core import BlogWatcher, WatcherScheduler
from blog_watcher.detection.change_detector import ChangeDetector
from blog_watcher.detection.http_fetcher import HttpFetcher
from blog_watcher.notification import SlackNotifier
from blog_watcher.observability import configure_logging, get_logger
from blog_watcher.storage import BlogStateRepository, CheckHistoryRepository, Database

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = get_logger(__name__)

app = typer.Typer(add_completion=False)


@dataclass(frozen=True, slots=True)
class ApplicationComponents:
    config_path: Path
    db: Database
    client: httpx.AsyncClient
    watcher: BlogWatcher
    scheduler: WatcherScheduler


@asynccontextmanager
async def create_application(config_path: Path, db_path: Path) -> AsyncIterator[ApplicationComponents]:
    config = load_config(config_path)

    db = Database(db_path)
    db.initialize()

    state_repo = BlogStateRepository(db)
    history_repo = CheckHistoryRepository(db)

    client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    fetcher = HttpFetcher(client)
    detector = ChangeDetector(fetcher=fetcher, state_repo=state_repo)
    notifier = SlackNotifier(client=client, config=config.slack)
    watcher = BlogWatcher(
        config=config,
        detector=detector,
        notifier=notifier,
        state_repo=state_repo,
        history_repo=history_repo,
    )
    scheduler = WatcherScheduler(interval_seconds=60, watcher=watcher)

    try:
        yield ApplicationComponents(
            config_path=config_path,
            db=db,
            client=client,
            watcher=watcher,
            scheduler=scheduler,
        )
    finally:
        await client.aclose()
        db.close()


@app.command()
def run(
    config: Annotated[Path, typer.Option("-c", "--config")],
    once: Annotated[bool, typer.Option("--once", is_flag=True)],
    db_path: Annotated[Path, typer.Option("--db-path")] = Path("blog_states.sqlite"),
) -> None:
    configure_logging()
    try:
        if once:
            asyncio.run(_run_once(config, db_path))
        else:
            asyncio.run(_run_scheduler(config, db_path))
    except ConfigError as exc:
        raise typer.Exit(code=1) from exc


async def _run_once(config_path: Path, db_path: Path) -> None:
    async with create_application(config_path, db_path) as app_state:
        await app_state.watcher.check_all()


async def _run_scheduler(config_path: Path, db_path: Path) -> None:
    async with create_application(config_path, db_path) as app_state:
        await app_state.scheduler.start()
        logger.info("scheduler_started", interval_seconds=60)
        try:
            await asyncio.Event().wait()
        finally:
            await app_state.scheduler.shutdown()


if __name__ == "__main__":
    app()
