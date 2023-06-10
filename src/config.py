class Config(object):
    """Config for our app"""

    default = {'app': 'pysonic',
               'app_api_host': '127.0.0.1',
               'app_api_port': 8005,
               'alive': True,
               'shutdown': False,
               'app_unicast_host': '127.0.0.1',
               'app_unicast_port': 1234,
               'app_unicast_protocol': 'udp',
               'app_unicast_buffer_size': 1024
               }

    def __init__(self, join_config: dict):
        self.join_config: dict = join_config

        self.new_config = self.default
        self.new_config.update(join_config)
        self.alive: bool = bool(self.new_config['alive'])  # if true then start kill FastAPI and APP
        self.shutdown: bool = bool(self.new_config['shutdown'])  # if true then waiting for finish all tasks

        self.app: str = str(self.new_config['app'])
        self.app_api_host: str = str(self.new_config['app_api_host'])
        self.app_api_port: int = int(self.new_config['app_api_port'])
        self.app_unicast_host: str = str(self.new_config['app_unicast_host'])
        self.app_unicast_port: int = int(self.new_config['app_unicast_port'])
        self.app_unicast_protocol: str = str(self.new_config['app_unicast_protocol'])
        self.app_unicast_buffer_size: int = int(self.new_config['app_unicast_buffer_size'])


if __name__ == "__main__":
    c = Config(join_config={})
    print(c.alive)
