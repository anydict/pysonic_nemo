import asyncio
import socket
from datetime import datetime
from json import JSONDecodeError

from aiohttp import client, BasicAuth, TCPConnector
from loguru import logger

from src.custom_dataclasses.api_request import ApiRequest
from src.custom_dataclasses.api_response import ApiResponse


class BaseClient(object):

    def __init__(self, log_object_id: str | None = None, auth: BasicAuth | None = None, headers: dict | None = None):
        self.count_request = 0
        self.count_exception = 0
        self.count_http_error = 0
        self.count_response_error = 0
        self.sum_execute_time = 0.0
        self.log = logger.bind(object_id=log_object_id or self.__class__.__name__)
        self.client_session = client.ClientSession(auth=auth, connector=TCPConnector(limit=999), headers=headers)

    @property
    def address(self) -> str:
        print('WARNING: the inherited class must have its own implementation')
        return ''

    @property
    def avg_execute_time(self) -> float:
        if self.count_request > 0:
            return self.sum_execute_time / self.count_request
        else:
            return self.sum_execute_time

    def dump(self) -> dict:
        return {
            "address": self.address,
            "dns_name": self.get_domain_name(address=self.address),
            "client_session": str(self.client_session),
            "count_request": self.count_request,
            "count_exception": self.count_exception,
            "count_http_error": self.count_http_error,
            "count_response_error": self.count_response_error,
            "sum_execute_time": self.sum_execute_time,
            "avg_execute_time": self.avg_execute_time,
        }

    @staticmethod
    def get_domain_name(address: str):
        try:
            ip_address = address.split(':')[0]
            return socket.gethostbyaddr(ip_address)[0]
        except (ValueError, IndexError, socket.herror):
            return 'Domain was not found'

    async def close_session(self):
        if self.client_session.closed is False:
            self.log.info('find client_session for close')
            await self.client_session.close()

    async def send(self, api_request: ApiRequest) -> ApiResponse:
        self.count_request += 1
        start_time = datetime.now()
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
                    api_response.execute_time = (datetime.now() - start_time).total_seconds()
                    api_response.end_time = datetime.now().isoformat()
                    api_response.message = f'http_code {response.status}'
                    try:
                        api_response.result = await response.json(content_type=None) or {"msg": "body is empty"}

                        if isinstance(api_response.result, str):
                            api_response.message = api_response.result
                            api_response.result = {"msg": api_response.result}
                        elif isinstance(api_response.result, dict) is False:
                            pass
                        elif 'message' in api_response.result:
                            api_response.message = api_response.result.get('message')
                        elif 'msg' in api_response.result:
                            api_response.message = api_response.result.get('msg')
                        elif 'error' in api_response.result:
                            api_response.message = f"error: {api_response.result.get('error')}"
                    except JSONDecodeError:
                        api_response.result = {"status": "ERROR"}
                        msg = await response.text() or "body is empty"
                        if msg and len(msg) > 0:
                            api_response.message = msg
                            api_response.result['msg'] = msg

                    if response.status in api_request.correct_http_code:
                        api_response.net_status = True

                        if isinstance(api_response.result, list):
                            api_response.success = True
                        elif 'error' in api_response.message.lower():
                            api_response.success = False
                            self.count_response_error += 1
                        elif str(api_response.result.get('res')).upper() in ('ERROR', 'FALSE'):
                            api_response.success = False
                            self.count_response_error += 1
                        elif str(api_response.result.get('status')).upper() in ('ERROR', 'FALSE'):
                            api_response.success = False
                            self.count_response_error += 1
                        else:
                            api_response.success = True

                        if attempt > 0 or api_request.debug_log:
                            self.log.info(f"AFTER api_request={api_request} api_response={api_response}")
                        break  # do not try again if the network is OK
                    else:
                        self.count_http_error += 1
                        if attempt == 0:
                            self.log.warning(f"AFTER api_request={api_request} api_response={api_response}")
                        else:
                            self.log.error(f"AFTER api_request={api_request} api_response={api_response}")
                        await asyncio.sleep(attempt)
            except Exception as e:
                self.count_exception += 1
                if attempt == 0 or self.client_session.closed:
                    self.log.warning(f"AFTER api_request={api_request} api_response={api_response}, e: {type(e)} {e}")
                else:
                    self.log.error(f"AFTER api_request={api_request} api_response={api_response}, e: {type(e)} {e}")
                    self.log.exception(e)
                await asyncio.sleep(attempt)

        if api_response.execute_time > api_request.duration_warning:
            self.log.warning(f"Huge time={api_response.execute_time} request:{api_request} response:{api_response}")

        self.sum_execute_time += api_response.execute_time

        return api_response
