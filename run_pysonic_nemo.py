import asyncio
import os
import platform
import sys
import uuid
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
from multiprocessing import Queue, Event

import uvicorn
from fastapi import FastAPI, Request, Depends
from fastapi.exceptions import RequestValidationError
from loguru import logger
from fastapi.middleware.cors import CORSMiddleware
from starlette import status
from starlette.responses import JSONResponse

from src.api.routes import Routers
from src.config import Config, filter_error_log
from src.manager import Manager
from src.unicast_server import UnicastServer


async def app_startup():
    """Run our application"""

    mp_queue = Queue()
    finish_event = Event()
    unicast_server = UnicastServer(config=config, mp_queue=mp_queue, finish_event=finish_event)
    unicast_server.start()

    ppe = ProcessPoolExecutor(max_workers=os.cpu_count())
    tpe = ThreadPoolExecutor()
    ppe.map(sorted, [0] * os.cpu_count())  # warmup

    app.manager = Manager(config=config, mp_queue=mp_queue, ppe=ppe, tpe=tpe, finish_event=finish_event)
    routers = Routers(config=config, manager=app.manager)
    app.include_router(routers.router, dependencies=[Depends(logging_dependency)])

    asyncio.create_task(app.manager.start_manager())


async def app_shutdown():
    """Run when application wait_shutdown"""

    if hasattr(app, 'manager') and isinstance(app.manager, Manager):
        await app.manager.close_session()


async def logging_dependency(request: Request):
    api_id = str(uuid.uuid4())
    logger.debug(f"api_id={api_id} {request.method} {request.url} body: {await request.body()}")
    logger.debug(f"api_id={api_id} Params: {request.path_params.items()}")
    logger.debug(f"api_id={api_id} Headers: {request.headers.items()}")


async def custom_validation_exception_handler(request: Request,
                                              exc: RequestValidationError):
    """
    logging validation error

    @param request: API request
    @param exc: Error information
    """
    errors = ['ValidationError']
    for error in exc.errors():
        errors.append({
            'loc': error['loc'],
            'msg': error['msg'],
            'type': error['type']
        })
    logger.error(f"ValidationError in path: {request.url.path} request_body: {await request.body()}")
    logger.error(f"ValidationError detail: {errors}")
    logger.error(f"ValidationError client_info: {request.client}")
    logger.error(request.headers)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"status": "error", "msg": " ### ".join(errors)}
    )


if __name__ == "__main__":
    try:
        config_path = os.path.join('config', 'config.json')
        config = Config(config_path=config_path)

        logger.configure(extra={"object_id": "None"})  # Default values if not bind extra variable
        logger.remove()  # this removes duplicates in the console if we use custom log format

        # for console
        if config.console_log:
            logger.add(sink=sys.stdout,
                       format=config.log_format,
                       colorize=True)
        # different files for different message types
        logger.add(sink="logs/error.log",
                   filter=filter_error_log,
                   rotation="500 MB",
                   compression='gz',
                   format=config.log_format)
        logger.add(sink=f"logs/{config.app}.log",
                   rotation="500 MB",
                   compression='gz',
                   retention=10,
                   format=config.log_format)

        logger = logger.bind(object_id=os.path.basename(__file__))

        app = FastAPI(exception_handlers={RequestValidationError: custom_validation_exception_handler},
                      version=config.app_version)


        @app.middleware("http")
        async def add_process_time_header(request: Request, call_next):
            start_time = datetime.now()
            response = await call_next(request)
            process_time = (datetime.now() - start_time).total_seconds()
            if process_time > 1:
                logger.warning(f'Huge process time: {process_time}, {request.method} {request.url} {request.headers}')
            response.headers['X-Current-Time'] = datetime.now().isoformat()
            response.headers['X-Process-Time'] = str(process_time)
            response.headers['Cache-Control'] = 'no-cache, no-store'
            return response


        @app.exception_handler(404)
        async def custom_404_handler(request: Request, __):
            msg = f"{request.method} API handler for {request.url} not found"
            logger.warning(msg)
            response = {
                "status": "error",
                "msg": msg
            }
            return JSONResponse(content=response, status_code=404)


        app.add_middleware(CORSMiddleware,  # noqa
                           allow_origins=[f"http://{config.app_api_host}:{config.app_api_port}"],
                           allow_credentials=True,
                           allow_methods=["*"],
                           allow_headers=["*"])

        logger.info("=" * 40, "System Information", "=" * 40)
        uname = platform.uname()
        logger.info(f"System: {uname.system}")
        logger.info(f"Node Name: {uname.node}")
        logger.info(f"Release: {uname.release}")
        logger.info(f"Machine: {uname.machine}")
        logger.info(f"Parent pid: {os.getppid()}")
        logger.info(f"Current pid: {os.getpid()}")
        logger.info(f"API bind address: http://{config.app_api_host}:{config.app_api_port}")
        logger.info(f"Docs Swagger API address: http://{config.app_api_host}:{config.app_api_port}/docs")
        logger.info(f"RTP SERVER bind address: http://{config.app_unicast_host}:{config.app_unicast_port}")
        logger.info(f"App Version: {config.app_version}")
        logger.info(f"Python Version: {config.python_version}")

        uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
        del uvicorn_log_config["loggers"]

        # Start FastAPI and our application in app_startup
        app.add_event_handler('startup', app_startup)
        app.add_event_handler('shutdown', app_shutdown)
        uvicorn.run(app=f'__main__:app',
                    host=config.app_api_host,
                    port=config.app_api_port,
                    log_level="info",
                    log_config=uvicorn_log_config,
                    reload=False)

        logger.info(f"Shutting down")
    except KeyboardInterrupt:
        logger.debug(f"User aborted through keyboard")
    except Exception as e:
        logger.exception(e)
