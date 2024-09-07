from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class ApiRequest(object):
    url: str
    method: str
    request: dict = None
    timeout: int = None
    correct_http_code: set = (200, 201, 204, 404)
    debug_log: bool = True
    attempts: int = 3
    duration_warning: int = 1
    api_id: str = field(default_factory=lambda: str(uuid4().hex))
    headers: dict = field(default_factory=lambda: dict())

    def __post_init__(self):
        self.headers['x-api-id'] = self.api_id
        self.headers['x-duration-warning'] = str(self.duration_warning)
        if self.attempts <= 0:
            self.attempts = 1

    def __str__(self):
        dict_object = self.__dict__.copy()

        if len(str(self.request)) > 1000:
            dict_object['request'] = f"len={len(str(self.request))}"

        return str(dict_object)


if __name__ == "__main__":
    ar = ApiRequest(url='http://example.com', method='POST', request={"action": "test"})
    print(ar)
