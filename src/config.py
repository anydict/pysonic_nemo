import json
import os


class Config(object):
    """Config for our app"""

    default = {
        "app": "pysonic",
        "app_api_host": "127.0.0.1",
        "app_api_port": 7005,
        "alive": True,
        "shutdown": False,
        "log_console": True,
        "app_unicast_host": "127.0.0.1",
        "app_unicast_port": 1234,
        "app_unicast_protocol": "udp",
        "app_unicast_buffer_size": 1024,
        "first_noise_answer_threshold": 250
    }

    def __init__(self, config_path: str = ''):
        join_config = {}
        if config_path and os.path.isfile(config_path):
            with open(config_path, "r") as jsonfile:
                join_config = json.load(jsonfile)
        else:
            print('WARNING! Config path not found => The default configuration will be used')

        self.join_config: dict = join_config

        self.new_config = self.default.copy()
        self.new_config.update(join_config)
        self.alive: bool = bool(self.new_config['alive'])  # if true then start kill FastAPI and APP
        self.shutdown: bool = bool(self.new_config['shutdown'])  # if true then waiting for finish all tasks
        self.log_console: bool = bool(self.new_config['log_console'])  # enable/disable log in console

        self.app: str = str(self.new_config['app'])
        self.app_api_host: str = str(self.new_config['app_api_host'])
        self.app_api_port: int = int(self.new_config['app_api_port'])
        self.app_unicast_host: str = str(self.new_config['app_unicast_host'])
        self.app_unicast_port: int = int(self.new_config['app_unicast_port'])
        self.app_unicast_protocol: str = str(self.new_config['app_unicast_protocol'])
        self.app_unicast_buffer_size: int = int(self.new_config['app_unicast_buffer_size'])

        self.first_noise_answer_threshold: int = int(self.new_config['first_noise_answer_threshold'])

    def get_different_type_variables(self) -> list:
        different: list[str] = []
        for variable in self.new_config:
            new_type = type(self.default[variable])
            if variable not in self.default:
                different.append(f'not found config variable with name: {variable}')
            elif isinstance(self.new_config[variable], type(self.default[variable])) is False:
                different.append(f'{variable}: wrong={new_type}, right={type(self.new_config[variable])}')
        return different


if __name__ == "__main__":
    c = Config()
    print(c.alive)
