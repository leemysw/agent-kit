# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：server
# @Date   ：2024/2/23 09:55
# @Author ：leemysw

# 2024/2/23 09:55   Create
# =====================================================

import gc
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agent.api.router import api_router
from agent.core.config import settings
from agent.shared.server.register import register_exception, register_hook, register_middleware
from agent.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        try:
            from agent.shared.database.get_db import get_db
            get_db(db_type=settings.MAIN_DB)
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")

        gc.collect()
        gc.freeze()

        yield

    finally:
        logger.info("Model shutdown complete.")



def create_app() -> FastAPI:
    # 统一处理mcp_apps参数，确保是列表形式

    app = FastAPI(
        debug=settings.DEBUG,
        title=settings.PROJECT_NAME,
        lifespan=lifespan,
        openapi_url=f"/openapi.json" if settings.ENABLE_SWAGGER_DOC else None,
        docs_url=f"/docs" if settings.ENABLE_SWAGGER_DOC else None,
        redoc_url=f"/redoc" if settings.ENABLE_SWAGGER_DOC else None,
        routes=api_router.routes,

    )

    # 注册中间件
    register_middleware(app)

    # 注册捕获全局异常
    register_exception(app)

    # 请求拦截
    register_hook(app)

    return app


app = create_app()
