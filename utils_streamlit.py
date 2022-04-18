from typing import Optional, Dict, Any, IO

import requests

import rekognition.utils_alert
import streamlit_config


assert not streamlit_config.api_url_root.endswith('/')


class ErrorResponse(Exception):
    def __init__(self, error_code: int, body: Optional[dict]):
        super(ErrorResponse, self).__init__()
        self.error_code = error_code
        self.body = body

    def __str__(self):
        return f'Error code: {self.error_code}. {str(self.body)}'


@rekognition.utils_alert.alert_slack_when_exception
def _fetch(session, url: str, method: str, data: Optional[Dict[str, Any]], files: Optional[Dict[str, IO]]) -> Dict[str, Any]:
    try:
        result = session.request(method=method, url=url, data=data, files=files)
    except requests.exceptions.ConnectionError as e:
        masking_exception = requests.exceptions.ConnectionError(f'Error on connect to {method} {url}. Original exception: {type(e)}: {e}')
        raise masking_exception from None
    except Exception:
        raise
    try:
        result = result.json()
        if result['error_code'] != 0:
            raise ErrorResponse(error_code=result['error_code'], body=result.get('body'))
        return result['body']
    except ErrorResponse:
        raise
    except Exception:
        raise
@rekognition.utils_alert.alert_slack_when_exception
def fetch(url: str, method: str = 'GET', data: Optional[Dict[str, Any]] = None, files: Optional[Dict[str, IO]] = None) -> Dict[str, Any]:
    with requests.session() as session:
        return _fetch(session, url=url, method=method, data=data, files=files)


@rekognition.utils_alert.alert_slack_when_exception
def call_api(url_path: str, method: str = 'GET', data: Optional[Dict[str, Any]] = None, files: Optional[Dict[str, IO]] = None) -> Dict[str, Any]:
    if not url_path.startswith('/'):
        url_path = '/' + url_path
    return fetch(url=f'{streamlit_config.api_url_root}{url_path}', method=method, data=data, files=files)
