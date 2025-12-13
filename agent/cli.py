# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：cli
# @Date   ：2025/6/18 15:00
# @Author ：leemysw
# 2025/6/18 15:00   Create
# =====================================================

import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)

import signal
import sys
from typing import Annotated

import typer

from agent.core.config import settings
from agent.utils import utils
from agent.utils.logger import logger

client = typer.Typer(rich_markup_mode="rich")


async def run_server(**uvicorn_kwargs) -> None:
    from agent.shared.server.launcher import serve_http

    # workaround to avoid footguns where uvicorn drops requests with too
    # many concurrent requests active
    if settings.ENABLE_VLLM:
        from vllm.utils.system_utils import set_ulimit
        set_ulimit()

    def signal_handler(*_) -> None:
        # Interrupt server on sigterm while initializing
        raise KeyboardInterrupt("terminated")

    signal.signal(signal.SIGTERM, signal_handler)

    signal.signal(signal.SIGTERM, signal_handler)
    shutdown_task = await serve_http(**uvicorn_kwargs)

    # NB: Await server shutdown only after the backend context is exited
    await shutdown_task


@client.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def run(
        server_type: Annotated[
            str,
            typer.Option(
                "--server-type",
                "-t",
                help="The server type to run the app. Options [gunicorn] or [uvicorn]. Default is [uvicorn]."
            )
        ] = "uvicorn",
):
    """
    Agent-Kit CLI - The [bold]Agent-Kit[/bold] command line app. 😎

    Run a [bold]FastAPI[/bold] app in [green]production[/green] mode. 🚀
    """

    # Print config info
    utils.print_info(settings, logger)

    if settings.SERVER_TYPE is not None:
        server_type = settings.SERVER_TYPE
        typer.echo(f"Using server type from config: {server_type}")

    if server_type not in ["uvicorn", "gunicorn"]:
        typer.echo(f"Invalid server type: {server_type}. Options are [uvicorn] or [gunicorn].")
        return

    if server_type == "uvicorn":
        from agent.app import app
        kwargs = {
            "app": app,
            "host": settings.HOST,
            "port": settings.PORT,
            "reload": False if settings.WORKERS != 1 else settings.DEBUG,
            "workers": settings.WORKERS,
            "lifespan": 'on',
            "ws": "websockets-sansio",
            "log_config": utils.set_uvicorn_logger(settings.LOGGER_FORMAT)
        }
        import uvloop
        uvloop.run(run_server(**kwargs))
    elif server_type == "gunicorn":
        from gunicorn.app.wsgiapp import WSGIApplication

        sys.argv = [
            'gunicorn',  # 程序名
            'agent.app:app',  # 应用模块
            '-c',  # 配置文件参数
            utils.abspath('core/config_gunicorn.py')  # 配置文件路径
        ]

        WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]", prog=None).run()


def main() -> None:
    client()
