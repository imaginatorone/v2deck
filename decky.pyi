# Type hints for decky plugin module

DECKY_USER: str
DECKY_USER_HOME: str
DECKY_HOME: str
DECKY_PLUGIN_SETTINGS_DIR: str
DECKY_PLUGIN_RUNTIME_DIR: str
DECKY_PLUGIN_LOG_DIR: str
DECKY_PLUGIN_DIR: str
DECKY_PLUGIN_NAME: str
DECKY_PLUGIN_VERSION: str
DECKY_PLUGIN_AUTHOR: str

class logger:
    @staticmethod
    def info(msg: str) -> None: ...
    @staticmethod
    def debug(msg: str) -> None: ...
    @staticmethod
    def warning(msg: str) -> None: ...
    @staticmethod
    def error(msg: str) -> None: ...

def migrate_logs(path: str) -> None: ...
def migrate_settings(path: str) -> None: ...
def migrate_runtime(path: str) -> None: ...
