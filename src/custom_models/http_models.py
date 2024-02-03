from pydantic import BaseModel, ConfigDict


class Event(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_name: str
    event_time: str
    call_id: str
    chan_id: str
    send_time: str
    token: str
    info: dict | object


class EventCreate(Event):
    class EventCreateInfo(BaseModel):
        chan_id: str
        em_host: str
        em_port: int
        em_codec: str
        em_wait_seconds: int
        em_sample_rate: int
        em_sample_width: int
        save_record: int
        save_format: str
        save_sample_rate: int
        save_sample_width: int
        save_filename: str
        save_concat_call_id: str
        speech_recognition: int
        detection_autoresponse: int
        detection_voice_start: int
        detection_absolute_silence: int
        callback_host: str
        callback_port: int

    model_config = ConfigDict(from_attributes=True)

    info: EventCreateInfo


class EventProgress(Event):
    model_config = ConfigDict(from_attributes=True)

    info: dict


class EventAnswer(Event):
    model_config = ConfigDict(from_attributes=True)

    info: dict


class EventDetect(Event):
    model_config = ConfigDict(from_attributes=True)

    info: dict


class EventDestroy(Event):
    model_config = ConfigDict(from_attributes=True)

    info: dict
