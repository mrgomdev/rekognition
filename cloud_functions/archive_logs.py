import posixpath
import os
import requests
import requests.adapters


ALERT_NAME = os.environ.get('ALERT_NAME', 'archive_logs.py')
MODI_REALTIME_DB_URL_ROOT = os.environ.get('MODI_REALTIME_DB_URL_ROOT', None)
_session = requests.session()
_session.mount(MODI_REALTIME_DB_URL_ROOT, requests.adapters.HTTPAdapter(max_retries=requests.adapters.Retry(total=2, connect=2, backoff_factor=0.1)))


def archive_hot_logs(event, context):
    response = _session.get(posixpath.join(MODI_REALTIME_DB_URL_ROOT, 'rekognition/logs.json'))
    parsed = response.json()
    if parsed is None:
        parsed = {}

    response = _session.patch(posixpath.join(MODI_REALTIME_DB_URL_ROOT, 'rekognition/logs-archived.json'), json=parsed)
    assert response.ok

    response = _session.delete(posixpath.join(MODI_REALTIME_DB_URL_ROOT, 'rekognition/logs.json'))
    assert response.ok
