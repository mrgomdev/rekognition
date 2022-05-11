from typing import Optional
from types import MappingProxyType

import datetime
from pytz import timezone
import os
import posixpath
import logging

import requests
import requests.adapters


CHARGED_APIS = MappingProxyType({
    'Rekognition': (
        'index_faces',
        'search_faces_by_image',
        'search_faces',
        'detect_faces'
    ),
    's3': tuple()
})

ALERT = True
ALERT_NAME = os.environ.get('ALERT_NAME', 'update_pause_charged_aws_api.py')
MODI_REALTIME_DB_URL_ROOT = os.environ.get('MODI_REALTIME_DB_URL_ROOT', None)


_session = requests.session()
_session.mount(MODI_REALTIME_DB_URL_ROOT, requests.adapters.HTTPAdapter(max_retries=requests.adapters.Retry(total=2, connect=2)))


def escape_slack(message: str) -> str:
    return str(message).replace('&', '&amp;').replace('>', '&gt;').replace('<', '&lt;')


def to_slack_message_body(body: Optional[dict] = None, already_escaped_str: bool = False, **kwargs) -> dict:
    if body is not None:
        kwargs.update(body)
    to_str = escape_slack if already_escaped_str else str
    return dict(text=f"• [{ALERT_NAME}] {datetime.datetime.now(timezone('Asia/Seoul')).strftime('%Y %m%d %H:%M:%S.%f %Z')}\n" + to_str('\n'.join([f"> {key}\n ```{kwargs[key]}``` " for key in kwargs])))


def alert_slack(logging_level: int = logging.ERROR, already_escaped_str: bool = False, **kwargs):
    if ALERT:
        webhooks_url = os.environ['SLACK_MODI_ALERTS_URL']
        with requests.session() as session:
            try:
                logging.log(logging_level, f'alert_slack: {session.post(url=webhooks_url, json=to_slack_message_body(kwargs, already_escaped_str=already_escaped_str))}')
            except Exception as e:
                logging.error(session.post(url=webhooks_url, json=to_slack_message_body(message="Alert! but exception during post.", exception=f"{type(e)}: {e}", already_escaped_str=already_escaped_str)))
    else:
        logging.log(logging_level, (to_slack_message_body(kwargs, already_escaped_str=already_escaped_str)['text']))


def update_hot_charged_logs(event, context):
    response = _session.get(posixpath.join(MODI_REALTIME_DB_URL_ROOT, 'rekognition/logs.json'))
    parsed = response.json()
    if parsed is None:
        parsed = {}
    count = 0
    for key, value in sorted(parsed.items(), key=lambda kv: kv[1]['kst']):
        if value['client_service_id'] not in CHARGED_APIS:
            raise KeyError(f'Invalid client_class_name')
        client_service_id = value['client_service_id']

        is_charged = False
        if value['client_api_name'] in CHARGED_APIS[client_service_id]:
            is_charged = True
            count += 1
        print(f'is_charged: {is_charged}, {key}: {value}')

    configs = _session.get(posixpath.join(MODI_REALTIME_DB_URL_ROOT, 'rekognition/configs.json')).json()
    assert isinstance(configs['max-every-minute'], int)

    pause_charged_aws_api = count >= configs['max-every-minute']
    old_pause_charged_aws_api = _session.get(posixpath.join(MODI_REALTIME_DB_URL_ROOT, 'rekognition/flags/pause-charged-aws-api.json')).json() == True

    if pause_charged_aws_api != old_pause_charged_aws_api:
        alert_slack(quota_warning=f"pause_charged_aws_api changed. {old_pause_charged_aws_api} -> {pause_charged_aws_api}. Current {count}. config[\'max-every-minute\'] {configs['max-every-minute']}")
        response = _session.put(posixpath.join(MODI_REALTIME_DB_URL_ROOT, 'rekognition/flags/pause-charged-aws-api.json'), json=pause_charged_aws_api)
    assert response.ok
