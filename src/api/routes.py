import datetime
import json

from fastapi import APIRouter
from loguru import logger

from src.config import Config
from fastapi.responses import Response

from pydantic import BaseModel

from src.manager import Manager


class OriginateParams(BaseModel):
    token: str
    intphone: int
    extphone: int
    idclient: int
    dir: str
    calleridrule: str
    actionid: str | None


class HangupParams(BaseModel):
    token: str
    actionid: str


class Routers(object):
    def __init__(self, config, manager):
        self.config: Config = config
        self.manager: Manager = manager
        self.log = logger.bind(object_id='routers')

        self.router = APIRouter(
            tags=["ALL"],
            responses={404: {"description": "Not found"}},
        )
        self.router.add_api_route("/diag", self.get_diag, methods=["GET"])
        self.router.add_api_route("/restart", self.restart, methods=["POST"])

    def get_diag(self):
        json_str = json.dumps({"res": "OK", "alive": self.config.alive}, indent=4, default=str)

        return Response(content=json_str, media_type='application/json')

    def restart(self):
        self.config.shutdown = True

        json_str = json.dumps({
            "app": "callpy",
            "shutdown": self.config.shutdown,
            "alive": self.config.alive,
            "msg": "app restart started",
            "current_time": datetime.datetime.now().isoformat()
        }, indent=4, default=str)

        return Response(content=json_str, media_type='application/json')
