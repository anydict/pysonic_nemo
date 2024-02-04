import asyncio

import aiohttp
from loguru import logger

from src.custom_dataclasses.api_request import ApiRequest
from src.http_clients.base_client import BaseClient


class CallPyClient(BaseClient):
    def __init__(self, host: str, port: int):
        super().__init__()
        self.host = host
        self.port = port
        self.session = aiohttp.ClientSession()
        self.log = logger.bind(object_id=f'{self.__class__.__name__}@{host}:{port}')
        asyncio.create_task(self.check_diag())

    @property
    def url_api(self):
        return f'http://{self.host}:{self.port}'

    async def check_diag(self):
        url = f'{self.url_api}/diag'
        method = 'GET'
        debug_log = True

        api_result = await self.send(api_request=ApiRequest(url=url, method=method, debug_log=debug_log))
        return api_result.success

    def send_analise(self):
        pass
