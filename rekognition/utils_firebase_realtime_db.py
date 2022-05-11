from typing import Optional
import dataclasses

import datetime
from pytz import timezone

import requests
_session = requests.session()

try:
    from . import utils_alert
    from . import config
except ImportError:
    import config
    import utils_alert


@dataclasses.dataclass
class LogItem:
    client_service_id: str
    client_api_name: str
    request: dict
    response: Optional[dict]
    kst: str = dataclasses.field(init=False)

    def __post_init__(self):
        self.request = utils_alert.deep_str_limited(a_dict=self.request)
        self.response = utils_alert.deep_str_limited(a_dict=self.response)
        self.kst = datetime.datetime.now(timezone('Asia/Seoul')).strftime('%Y %m%d %H:%M:%S.%f %Z')


def post_log(item: LogItem) -> requests.Response:
    return _session.post(f'{config.firebase_realtime_db_logs_url}', json=dataclasses.asdict(item))
