import asyncio
import json

import aiohttp
from aiohttp import ClientConnectorError
from loguru import logger
from fastapi import status


class CallPyClient():
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.session = aiohttp.ClientSession()
        self.log = logger.bind(object_id=f'{host}:{port}')
        asyncio.create_task(self.check_diag())

    async def close_session(self):
        if self.session:
            await self.session.close()

    async def make_get_request(self, path: str, params=None, description=''):
        """
        This is an asynchronous function that makes a GET request to a specified URL with optional parameters.

        @param self - the instance of the class
        @param path - path after URL address
        @param params - optional parameters to include in the GET request
        @param description - this will be added in header
        @return a tuple containing the status code and data from the response
        """
        if path.startswith('/'):
            self.log.warning('path should not start with a slash')
            path = path[1:]

        try:
            headers = {'description': description}
            url = f'http://{self.host}:{self.port}/{path}'
            async with self.session.get(url, params=params, headers=headers) as response:
                self.log.info(f'fetch_json url={url} params={params}')
                status = response.status
                body = await response.text()
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    self.log.error(f'JSONDecodeError with body={body}')
                    data = None
                return status, data
        except ClientConnectorError:
            return 503, {"msg": "ClientConnectorError"}

    async def make_post_request(self, path: str, data=None, description=''):
        """
        This is an asynchronous function that makes a POST request to a specified URL with optional parameters.

        @param self - the instance of the class
        @param path - path after URL address
        @param data - optional parameters to include in the POST request
        @param description - this will be added in header
        @return a tuple containing the status code and data from the response
        """
        if path.startswith('/'):
            self.log.warning('path should not start with a slash')
            path = path[1:]

        try:
            headers = {'Content-type': 'application/json',
                       'Accept': 'text/plain',
                       'description': description}
            url = f'http://{self.host}:{self.port}/{path}'
            async with self.session.post(url, data=json.dumps(data), headers=headers) as response:
                self.log.info(f'fetch_json url={url} params={data}')
                status = response.status
                body = await response.text()
                try:
                    data_response = json.loads(body)
                except json.JSONDecodeError:
                    self.log.error(f'JSONDecodeError with body={body}')
                    data_response = None
                return status, data_response
        except ClientConnectorError:
            return 503, {"msg": "ClientConnectorError"}

    async def check_diag(self):
        http_code, data = await self.make_get_request(path='diag')
        self.log.debug(f'http_code={http_code} and data={data}')
        return http_code == status.HTTP_200_OK

    def send_analise(self):
        pass
