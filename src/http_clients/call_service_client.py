import asyncio

from src.config import Config
from src.custom_dataclasses.api_request import ApiRequest
from src.http_clients.base_client import BaseClient


class CallServiceClient(BaseClient):
    def __init__(self, config: Config, host: str, port: int):
        super().__init__(log_object_id=f'{self.__class__.__name__}@{host}:{port}',
                         headers={'x-app-client': config.app_name})
        self.host = host
        self.port = port
        self.log.info(f'http_info: {self.dump().__str__()}')
        asyncio.create_task(self.check_diag())

    @property
    def address(self):
        """IP and colon and PORT"""
        return f'{self.host}:{self.port}'

    @property
    def http_address(self):
        return f'http://{self.host}:{self.port}'

    async def check_diag(self):
        url = f'{self.http_address}/diag'
        method = 'GET'
        debug_log = True

        api_result = await self.send(api_request=ApiRequest(url=url, method=method, debug_log=debug_log))
        return api_result.success

    def send_analise(self):
        pass
