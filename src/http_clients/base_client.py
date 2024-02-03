import asyncio
import time
from json import JSONDecodeError
from typing import Optional

from aiohttp import client, BasicAuth
from loguru import logger

from src.custom_dataclasses.api_request import ApiRequest
from src.custom_dataclasses.api_response import ApiResponse


class BaseClient(object):

    def __init__(self, auth: Optional[BasicAuth] = None):
        self.client_session = client.ClientSession(auth=auth)
        self.log = logger.bind(object_id=self.__class__.__name__)
        self.count_request = 0

    async def close_session(self):
        if self.client_session.closed is False:
            self.log.info('find client_session for close')
            await self.client_session.close()

    async def send(self, api_request: ApiRequest) -> ApiResponse:
        self.count_request += 1
        start_time = time.time()
        api_response: ApiResponse = ApiResponse(http_code=0,
                                                execute_time=0,
                                                net_status=False,
                                                success=False,
                                                message='',
                                                result=None)

        for attempt in range(0, api_request.attempts):
            api_response.used_attempts = attempt
            if attempt > 0 or api_request.debug_log:
                self.log.info(f"BEFORE api_request={api_request}")
            try:
                async with self.client_session.request(method=api_request.method,
                                                       url=api_request.url,
                                                       json=api_request.request,
                                                       headers=api_request.headers,
                                                       timeout=api_request.timeout) as response:
                    api_response.http_code = response.status
                    api_response.content_type = response.content_type
                    api_response.execute_time = time.time() - start_time
                    api_response.message = f'http_code {response.status}'
                    try:
                        api_response.result = await response.json(content_type=None)

                        if api_response.result is None:
                            api_response.result = {"res": "OK", "msg": "response is None"}
                        if isinstance(api_response.result, dict) is False:
                            pass
                        if 'message' in api_response.result:
                            api_response.message = api_response.result.get('message')
                        elif 'msg' in api_response.result:
                            api_response.message = api_response.result.get('msg')
                        elif 'error' in api_response.result:
                            api_response.message = f"error: {api_response.result.get('error')}"
                    except JSONDecodeError:
                        msg = await response.text() or "body is empty"
                        if msg and len(msg) > 0:
                            api_response.message = msg
                        api_response.result = {"msg": msg}

                    if response.status in api_request.correct_http_code:
                        api_response.net_status = True

                        if isinstance(api_response.result, list):
                            api_response.success = True
                        elif str(api_response.result.get('res')).upper() == 'ERROR':
                            api_response.success = False
                        elif str(api_response.result.get('status')).upper() == 'ERROR':
                            api_response.success = False
                        elif 'error' in api_response.message:
                            api_response.success = False
                        else:
                            api_response.success = True

                        if attempt > 0 or api_request.debug_log:
                            self.log.info(f"AFTER api_request={api_request} api_response={api_response}")
                        break
                    else:
                        if attempt == 0:
                            self.log.warning(f"AFTER api_request={api_request} api_response={api_response}")
                        else:
                            self.log.error(f"AFTER api_request={api_request} api_response={api_response}")
                        await asyncio.sleep(attempt)
            except Exception as e:
                if attempt == 0 or self.client_session.closed:
                    self.log.warning(f"AFTER api_request={api_request} api_response={api_response}")
                else:
                    self.log.error(f"AFTER api_request={api_request} api_response={api_response}")
                    self.log.exception(e)
                await asyncio.sleep(attempt)

        if api_response.execute_time > api_request.duration_warning:
            self.log.warning(f"Huge time={api_response.execute_time} request:{api_request} response:{api_response}")

        return api_response
