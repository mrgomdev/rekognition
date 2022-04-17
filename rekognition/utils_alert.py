from typing import Callable, Any, Dict, Optional
import traceback
import functools
import datetime
import json
import os
import socket
import logging
logging.getLogger().setLevel(logging.INFO)

import requests

ALERT = True

ALERT_NAME = os.environ.get('ALERT_NAME', socket.gethostname())


def str_limited(obj) -> str:
    if isinstance(obj, bytes) or (str(obj).startswith("b'")):
        return 'BYTES'
    elif len(str(obj)) > 1000 and 'Traceback (most recent call last):' not in str(obj):
        return 'TOO LONG'
    else:
        return str(obj)


def escape_slack(message: str) -> str:
    return str(message).replace('&', '&amp;').replace('>', '&gt;').replace('<', '&lt;')


def to_slack_message_body(body: Optional[dict] = None, already_escaped_str: bool = False, **kwargs) -> dict:
    if body is not None:
        kwargs.update(body)
    to_str = escape_slack if already_escaped_str else str
    return dict(text=f"• [{ALERT_NAME}] {datetime.datetime.now().strftime('%Y %m%d %H:%M:%S')}\n" + to_str('\n'.join([f"> {key}\n ```{kwargs[key]}``` " for key in kwargs])))


def alert_slack(logging_level: int = logging.ERROR, already_escaped_str: bool = False, **kwargs):
    if ALERT:
        webhooks_url = os.environ['SLACK_MODI_ALERTS_URL']
        with requests.session() as session:
            try:
                logging.log(logging_level, f'alert_slack: {session.post(url=webhooks_url, json=to_slack_message_body(kwargs, already_escaped_str=already_escaped_str))}')
            except Exception as e:
                logging.error(session.post(url=webhooks_url, json=to_slack_message_body(message="Alert! but exception during post.", exception=f"{type(e)}: {e}", already_escaped_str=already_escaped_str)))


def format_exception_str(exception: Exception) -> Dict[str, str]:
    body = dict(exception=f"{type(exception)}: {str_limited(exception)}")
    body['traceback'] = traceback.format_exc()
    return body


def alert_slack_exception(exception: Exception, already_alerted_exception: Optional[bool] = None, **kwargs):
    if already_alerted_exception is None:
        if hasattr(exception, 'already_alerted') and exception.already_alerted:
            already_alerted_exception = exception.already_alerted
        else:
            already_alerted_exception = False
    if not already_alerted_exception:
        kwargs = dict(**format_exception_str(exception), **kwargs)
        exception.already_alerted = True
    if len(kwargs) > 0:
        alert_slack(**kwargs)


def alert_slack_when_exception(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            alert_slack_exception(e, function_call=f"{func.__name__}({', '.join(json.dumps(arg, default=str_limited) for arg in args)}, { {key: json.dumps(value, default=str_limited) for key, value in kwargs.items()} })")
            raise
    return wrapper


alert_slack(logging_level=logging.INFO, message="Slack alert is running.")


if __name__ == '__main__':
    alert_slack(logging_level=logging.DEBUG, gomdev=123)
    @alert_slack_when_exception
    def _test(foo, bar):
        raise NotImplementedError('42')
        return foo, bar
    _test(4, bar=11)
