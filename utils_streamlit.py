from typing import Optional, Dict, Any, IO
import enum

import requests

import rekognition.utils_alert
import streamlit_config

import streamlit as st


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


class AdminStatus(enum.Enum):
    AUTHORIZED = 'authoried'
    WRONG_TOKEN = 'wrong_token'
    NOT_YET = 'not_yet'


def ask_admin_password(password: Optional[str] = None) -> bool:
    if 'admin' not in st.session_state:
        st.session_state.admin = AdminStatus.NOT_YET

    admin_auth = st.empty()
    if password is None:
        if 'admin' not in st.experimental_get_query_params():
            admin_auth.write('Please input username')
            return False
        username = st.experimental_get_query_params()['admin'][0]
        password = st.secrets.admin[username]
    else:
        username = 'OVERRIDDEN'

    if st.session_state.admin != AdminStatus.AUTHORIZED:
        admin_auth.text_input(label=f'{username}', placeholder='password', key='admin_auth_password', type='password')
        if st.session_state.admin_auth_password == password:
            st.session_state.admin = AdminStatus.AUTHORIZED
        else:
            st.session_state.admin = AdminStatus.WRONG_TOKEN

    if st.session_state.admin == AdminStatus.AUTHORIZED:
        admin_auth.write('In Admin Mode')
        return True
    else:
        return False


def ask_admin_password_if_needed(password: Optional[str] = None) -> bool:
    if 'admin' in st.experimental_get_query_params():
        return ask_admin_password(password=password)
    else:
        return True


if __name__ == '__main__':
    if ask_admin_password_if_needed():
        st.write('main')
