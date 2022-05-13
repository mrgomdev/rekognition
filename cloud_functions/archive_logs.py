import posixpath
import os

import requests
import requests.adapters

import google.cloud.pubsub_v1


ALERT_NAME = os.environ.get('ALERT_NAME', 'archive_logs.py')
MODI_REALTIME_DB_URL_ROOT = os.environ.get('MODI_REALTIME_DB_URL_ROOT', None)
_session = requests.session()
_session.mount(MODI_REALTIME_DB_URL_ROOT, requests.adapters.HTTPAdapter(max_retries=requests.adapters.Retry(total=2, connect=2, backoff_factor=0.1)))


google_application_credentials = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
PROJECT_ID = os.getenv('GCLOUD_PROJECT_ID')
_publisher = google.cloud.pubsub_v1.PublisherClient()
def publish(topic_id: str, data: str = '{}') -> str:
    future = _publisher.publish(topic=_publisher.topic_path(PROJECT_ID, topic_id), data=data.encode('utf-8'))
    message_id = future.result()
    return message_id


def archive_hot_logs(event=None, context=None):
    response = _session.get(posixpath.join(MODI_REALTIME_DB_URL_ROOT, 'rekognition/logs.json'))
    parsed = response.json()
    if parsed is None:
        parsed = {}

    response = _session.patch(posixpath.join(MODI_REALTIME_DB_URL_ROOT, 'rekognition/logs-archived.json'), json=parsed)
    assert response.ok

    response = _session.delete(posixpath.join(MODI_REALTIME_DB_URL_ROOT, 'rekognition/logs.json'))
    assert response.ok

    publish(topic_id='update-pause-charged-aws-api')
