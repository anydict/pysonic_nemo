import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ApiResponse(object):
    http_code: int
    execute_time: int
    net_status: bool
    success: bool
    message: str
    result: dict | None
    content_type: str = 'application/json'
    used_attempts: int = 0
    api_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: str = field(default_factory=lambda: datetime.now().isoformat())

    def __str__(self):
        dict_object = self.__dict__.copy()

        if len(str(self.result)) > 1000:
            dict_object['result'] = f"len={len(str(self.result))}"

        return str(dict_object)


if __name__ == "__main__":
    ar = ApiResponse(http_code=0, execute_time=0, net_status=False, success=False, message='', result=None)
    print(ar)
