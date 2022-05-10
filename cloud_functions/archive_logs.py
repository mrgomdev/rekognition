import os.path
import requests


ALERT_NAME = os.environ.get('ALERT_NAME', 'archive_logs.py')
MODI_REALTIME_DB_URL_ROOT = os.environ.get('MODI_REALTIME_DB_URL_ROOT', None)
_session = requests.session()


def archive_hot_logs(event, context):
    response = _session.get(os.path.join(MODI_REALTIME_DB_URL_ROOT, 'rekognition/logs.json'))
    parsed = response.json()
    if parsed is None:
        parsed = {}

    response = _session.patch(os.path.join(MODI_REALTIME_DB_URL_ROOT, 'rekognition/logs-archived.json'), json=parsed)
    assert response.ok

    response = _session.delete(os.path.join(MODI_REALTIME_DB_URL_ROOT, 'rekognition/logs.json'))
    assert response.ok
