from datetime import datetime

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from loguru import logger
from starlette import status

accumulate_requests: list = []
last_logs_api_time: datetime = datetime.now()
last_huge_alarm_time: datetime = datetime.now()


async def add_process_time_header(request: Request, call_next):
    global accumulate_requests
    global last_huge_alarm_time
    global last_logs_api_time

    start_time = datetime.now()
    response = await call_next(request)
    duration_warning = 1
    if str(request.headers.get('x-duration-warning')).isdigit():
        duration_warning = int(request.headers.get('x-duration-warning'))

    process_time = (datetime.now() - start_time).total_seconds()
    response.headers['X-Current-Time'] = datetime.now().isoformat()
    response.headers['X-Process-Time'] = str(process_time)
    response.headers['Cache-Control'] = 'no-cache, no-store'

    request_info = {
        "method": request.method,
        "url": request.url,
        "headers": request.headers,
        "client": request.client,
        "response_code": response.status_code,
        "response_headers": response.headers
    }

    if process_time > duration_warning and (datetime.now() - last_huge_alarm_time).total_seconds() > 1:
        last_huge_alarm_time = datetime.now()
        logger.warning(f'Huge process time in request: {request_info}')

    accumulate_requests.append(request_info)
    if (datetime.now() - last_logs_api_time).total_seconds() > 3:
        last_logs_api_time = datetime.now()
        logger.info(accumulate_requests)
        accumulate_requests.clear()

    return response


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

    return ORJSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"status": "error", "msg": " ### ".join(errors)}
    )


async def custom_404_handler(request: Request, __):
    msg = f"{request.method} API handler for {request.url} not found"
    logger.warning(msg)
    response = {
        "status": "error",
        "msg": msg
    }
    return ORJSONResponse(content=response, status_code=404)
