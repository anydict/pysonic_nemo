import json
from datetime import datetime

from fastapi import APIRouter, status
from fastapi.responses import Response, JSONResponse
from loguru import logger
from pydantic import ValidationError

from src.config import Config
from src.custom_models.http_models import EventAnswer, EventDetect, EventDestroy, EventProgress, EventCreate, Event
from src.manager import Manager


class Routers(object):
    def __init__(self, config, manager):
        self.config: Config = config
        self.manager: Manager = manager
        self.log = logger.bind(object_id=self.__class__.__name__)

        self.router = APIRouter(
            tags=["ALL"],
            responses={404: {"description": "Not found"}},
        )
        self.router.add_api_route("/diag", self.get_diag, methods=["GET"])
        self.router.add_api_route("/restart", self.restart, methods=["POST"])
        self.router.add_api_route("/events", self.events, methods=["POST"])

    async def get_diag(self):
        response = {
            "app": self.config.app,
            "wait_shutdown": self.config.wait_shutdown,
            "alive": self.config.alive,
            "current_time": datetime.now().isoformat()
        }

        return Response(content=response, media_type='application/json')

    async def restart(self):
        self.config.wait_shutdown = True

        json_str = json.dumps({
            "app": "callpy",
            "wait_shutdown": self.config.wait_shutdown,
            "alive": self.config.alive,
            "msg": "app restart started",
            "current_time": datetime.now().isoformat()
        }, indent=4, default=str)

        return JSONResponse(content=json_str)

    async def events(self, event: Event):
        receive_time = datetime.now().isoformat()

        response = {
            "status": "ok",
            "call_id": event.call_id,
            "event_name": event.event_name,
            "send_time": event.send_time,
            "receive_time": receive_time
        }

        try:
            if event.event_name == 'CREATE':
                event = EventCreate.model_validate(event)
                success = await self.manager.start_event_create(event)
            elif event.event_name == 'PROGRESS':
                event = EventProgress.model_validate(event)
                success = await self.manager.start_event_progress(event)
            elif event.event_name == 'ANSWER':
                event = EventAnswer.model_validate(event)
                success = await self.manager.start_event_answer(event)
            elif event.event_name == 'DETECT':
                event = EventDetect.model_validate(event)
                success = await self.manager.start_event_detect(event)
            elif event.event_name == 'DESTROY':
                event = EventDestroy.model_validate(event)
                success = await self.manager.start_event_destroy(event)
            else:
                return Response(content=json.dumps({"msg": "Event not found"}), status_code=404)

            if success:
                return JSONResponse(content=response)
            else:
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                    content={"status": "error", "msg": f"Not found audio_packages"})

        except AttributeError as exc:
            logger.error(f"AttributeError in event={event.event_name}")
            logger.error(f"AttributeError detail: {exc}")

            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"status": "error", "msg": "invalid request", "detail": str(exc)}
            )
        except ValidationError as exc:
            logger.error(f"ValidationError in event {event.event_name}: {exc}")

            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"status": "error", "msg": str(exc)}
            )
