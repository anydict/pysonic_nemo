import json
import os
import platform

SEQ_NUMBER_AFTER_FIRST_RESET = 65535
AMPLITUDE_THRESHOLD_BEEP = 9200
AMPLITUDE_THRESHOLD_VOICE = 250
AMPLITUDE_THRESHOLD_NOISE = 100
MIN_AMPLITUDE_FOR_DETECTION = 2000

DEFAULT_SAMPLE_WIDTH = 2  # for 16 bit this equal 2
DEFAULT_SAMPLE_RATE = 8000  # 8k kHz

CONNECTIVITY_MASK = 1
DEFAULT_FS = 8000
DEFAULT_WINDOW_SIZE = 512  # 4096
DEFAULT_OVERLAP_RATIO = 0.5
DEFAULT_FAN_VALUE = 15  # 15 was the original value.
DEFAULT_AMP_MIN = 20
PEAK_NEIGHBORHOOD_SIZE = 8  # 20 was the original value.
MIN_HASH_TIME_DELTA = 0
MAX_HASH_TIME_DELTA = 200
PEAK_SORT = True
TOPN = 2


def filter_error_log(record):
    return record["level"].name == "ERROR"


class Config(object):
    """Config for our app"""

    default = {
        "app": "pysonic",
        "app_api_host": "127.0.0.1",
        "app_api_port": 7005,
        "alive": True,
        "wait_shutdown": False,
        "console_log": True,
        "app_unicast_host": "127.0.0.1",
        "app_unicast_port": 1234,
        "app_unicast_protocol": "udp",
        "app_unicast_buffer_size": 1024
    }

    def __init__(self, config_path: str = ''):
        join_config = {}
        if config_path and os.path.isfile(config_path):
            with open(config_path, "r") as jsonfile:
                join_config = json.load(jsonfile)
        else:
            print('WARNING! Config path not found => The default configuration will be used')

        self.log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green>[<level>{level}</level>]" \
                          "<cyan>[{extra[object_id]}]</cyan>" \
                          "<magenta>{name}</magenta>:<magenta>{function}</magenta>:" \
                          "<cyan>{line}</cyan> - <level>{message}</level>"

        self.join_config: dict = join_config
        self.app_version = self.get_app_version()
        self.python_version = platform.python_version()

        self.new_config = self.default.copy()
        self.new_config.update(join_config)
        self.alive: bool = bool(self.new_config['alive'])  # if true then start kill FastAPI and APP
        self.wait_shutdown: bool = bool(self.new_config['wait_shutdown'])  # if true then waiting for finish all tasks
        self.console_log: bool = bool(self.new_config['console_log'])  # enable/disable log in console

        self.app: str = str(self.new_config['app'])
        self.app_api_host: str = str(self.new_config['app_api_host'])
        self.app_api_port: int = int(self.new_config['app_api_port'])
        self.app_unicast_host: str = str(self.new_config['app_unicast_host'])
        self.app_unicast_port: int = int(self.new_config['app_unicast_port'])
        self.app_unicast_protocol: str = str(self.new_config['app_unicast_protocol'])
        self.app_unicast_buffer_size: int = int(self.new_config['app_unicast_buffer_size'])

    def get_different_type_variables(self) -> list:
        different: list[str] = []
        for variable in self.new_config:
            new_type = type(self.default[variable])
            if variable not in self.default:
                different.append(f'not found config variable with name: {variable}')
            elif isinstance(self.new_config[variable], type(self.default[variable])) is False:
                different.append(f'{variable}: wrong={new_type}, right={type(self.new_config[variable])}')
        return different

    @staticmethod
    def get_app_version():
        if os.path.isfile('version'):
            f = open('version')
            return f.readline()
        else:
            print('WARNING! Not found file version, use version = 1.0.0')
            return '1.0.0'


if __name__ == "__main__":
    c = Config()
    print(c.alive)
