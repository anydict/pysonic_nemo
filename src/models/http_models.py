from pydantic import BaseModel


class Event(BaseModel):
    event_name: str
    event_time: str
    druid: str
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
        save_concat_druid: str
        speech_recognition: int
        detection_autoresponse: int
        detection_voice_start: int
        detection_absolute_silence: int

    event_name: str
    event_time: str
    druid: str
    chan_id: str
    send_time: str
    token: str
    info: EventCreateInfo

    class Config:
        orm_mode = True


class EventProgress(BaseModel):
    class EventProgressInfo(BaseModel):
        em_host: str
        em_port: int
        em_ssrc: int

    event_name: str
    event_time: str
    druid: str
    chan_id: str
    send_time: str
    token: str
    info: EventProgressInfo

    class Config:
        orm_mode = True


class EventAnswer(BaseModel):
    class EventAnswerInfo(BaseModel):
        em_host: str
        em_port: int
        em_ssrc: int

    event_name: str
    event_time: str
    druid: str
    chan_id: str
    send_time: str
    token: str
    info: EventAnswerInfo

    class Config:
        orm_mode = True


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
    druid: str
    chan_id: str
    send_time: str
    token: str
    info: EventDetectInfo

    class Config:
        orm_mode = True


class EventDestroy(BaseModel):
    class EventDestroyInfo(BaseModel):
        em_host: str
        em_port: int
        em_ssrc: int

    event_name: str
    event_time: str
    druid: str
    chan_id: str
    send_time: str
    token: str
    info: EventDestroyInfo

    class Config:
        orm_mode = True
