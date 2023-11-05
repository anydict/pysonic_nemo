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
    class EventProgressInfo(BaseModel):
        em_host: str
        em_port: int
        em_ssrc: int

    model_config = ConfigDict(from_attributes=True)

    info: EventProgressInfo


class EventAnswer(Event):
    class EventAnswerInfo(BaseModel):
        em_host: str
        em_port: int
        em_ssrc: int

    model_config = ConfigDict(from_attributes=True)

    info: EventAnswerInfo


class EventDetect(Event):
    class EventDetectInfo(BaseModel):
        em_host: str
        em_port: int
        em_ssrc: int
        from_detect_time: str
        to_detect_time: str
        stop_words: list[str]
        stop_after_noise_and_silence: list[int]

    model_config = ConfigDict(from_attributes=True)

    info: EventDetectInfo


class EventDestroy(Event):
    class EventDestroyInfo(BaseModel):
        em_host: str
        em_port: int
        em_ssrc: int

    model_config = ConfigDict(from_attributes=True)

    info: EventDestroyInfo
