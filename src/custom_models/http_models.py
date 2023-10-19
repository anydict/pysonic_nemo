from pydantic import BaseModel


class Event(BaseModel):
    event_name: str
    event_time: str
    call_id: str
    chan_id: str
    send_time: str
    token: str
    info: dict


class EventCreate(BaseModel):
    class EventCreateInfo(BaseModel):
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

    event_name: str
    event_time: str
    call_id: str
    chan_id: str
    send_time: str
    token: str
    info: EventCreateInfo


class EventProgress(BaseModel):
    class EventProgressInfo(BaseModel):
        em_host: str
        em_port: int
        em_ssrc: int

    event_name: str
    event_time: str
    call_id: str
    chan_id: str
    send_time: str
    token: str
    info: EventProgressInfo


class EventAnswer(BaseModel):
    class EventAnswerInfo(BaseModel):
        em_host: str
        em_port: int
        em_ssrc: int

    event_name: str
    event_time: str
    call_id: str
    chan_id: str
    send_time: str
    token: str
    info: EventAnswerInfo


class EventDetect(BaseModel):
    class EventDetectInfo(BaseModel):
        em_host: str
        em_port: int
        em_ssrc: int
        from_detect_time: str
        to_detect_time: str
        stop_words: list[str]
        stop_after_noise_and_silence: list[int]

    event_name: str
    event_time: str
    call_id: str
    chan_id: str
    send_time: str
    token: str
    info: EventDetectInfo


class EventDestroy(BaseModel):
    class EventDestroyInfo(BaseModel):
        em_host: str
        em_port: int
        em_ssrc: int

    event_name: str
    event_time: str
    call_id: str
    chan_id: str
    send_time: str
    token: str
    info: EventDestroyInfo
