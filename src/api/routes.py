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
        self.log = logger.bind(object_id='routers')

        self.router = APIRouter(
            tags=["ALL"],
            responses={404: {"description": "Not found"}},
        )
        self.router.add_api_route("/diag", self.get_diag, methods=["GET"])
        self.router.add_api_route("/restart", self.restart, methods=["POST"])
        self.router.add_api_route("/events", self.events, methods=["POST"])
        self.router.add_api_route("/{not_found}", self.not_found, methods=["POST"])

    async def get_diag(self):
        response = {
            "app": self.config.app,
            "shutdown": self.config.shutdown,
            "alive": self.config.alive,
            "current_time": datetime.now().isoformat()
        }

        return Response(content=response, media_type='application/json')

    async def restart(self):
        self.config.shutdown = True

        json_str = json.dumps({
            "app": "callpy",
            "shutdown": self.config.shutdown,
            "alive": self.config.alive,
            "msg": "app restart started",
            "current_time": datetime.now().isoformat()
        }, indent=4, default=str)

        return JSONResponse(content=json_str)

    async def events(self, event: Event):
        receive_time = datetime.now().isoformat()

        response = {
            "call_id": event.call_id,
            "event_name": event.event_name,
            "send_time": event.send_time,
            "receive_time": receive_time
        }

        try:
            if event.event_name == 'CREATE':
                event = EventCreate.model_validate(event)
                ssrc = await self.manager.start_event_create(event)

                if ssrc == '':
                    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                        content={"msg": f"Not found audio_packages"})
                else:
                    return JSONResponse(content={
                        "ssrc": ssrc,
                        "event_time": event.event_time,
                        "send_time": event.send_time,
                        "receive_time": receive_time,
                        "response_time": datetime.now().isoformat()
                    })

            elif event.event_name == 'PROGRESS':
                event = EventProgress.model_validate(event)
                await self.manager.start_event_progress(event)
            elif event.event_name == 'ANSWER':
                event = EventAnswer.model_validate(event)
                await self.manager.start_event_answer(event)
            elif event.event_name == 'DETECT':
                event = EventDetect.model_validate(event)
                await self.manager.start_event_detect(event)
            elif event.event_name == 'DESTROY':
                event = EventDestroy.model_validate(event)
                await self.manager.start_event_destroy(event)
            else:
                return Response(content=json.dumps({"msg": "Event not found"}), status_code=404)
        except AttributeError as exc:
            logger.error(f"AttributeError in event={event.event_name}")
            logger.error(f"AttributeError detail: {exc}")

            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"msg": "invalid request", "detail": str(exc)}
            )
        except ValidationError as exc:
            errors = []
            for error in exc.errors():
                errors.append({
                    'loc': error['loc'],
                    'msg': error['msg'],
                    'type': error['type']
                })
            logger.error(f"ValidationError in event={event.event_name}")
            logger.error(f"ValidationError detail: {errors}")
            logger.exception(exc)

            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content=errors[0] if len(errors) > 0 else {"msg": "invalid request"}
            )

        return JSONResponse(content=response)

    @staticmethod
    async def not_found():
        response = {
            "msg": "Not found"
        }
        return JSONResponse(content=response, status_code=404)
