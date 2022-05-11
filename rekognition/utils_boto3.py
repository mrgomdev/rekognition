from __future__ import annotations

import enum
import mimetypes
from typing import Optional, Callable, Any, IO, Union, TypedDict, Tuple

from types import MappingProxyType
import functools
import os
import posixpath

import requests

import botocore.exceptions
import botocore.client
import boto3

try:
    from . import utils
    from . import utils_alert
    from . import utils_firebase_realtime_db
    from . import config
except ImportError:
    import utils
    import utils_alert
    import utils_firebase_realtime_db
    import config


ClientError = botocore.exceptions.ClientError


class RequestError(ValueError):
    def __init__(self, message: str, boto_exception: Optional[botocore.exceptions.ClientError] = None):
        self.message = message

        if boto_exception is not None:
            assert isinstance(boto_exception, botocore.exceptions.ClientError)
            try:
                self.request_id = boto_exception.response['ResponseMetadata']['RequestId']
            except Exception:
                self.request_id = None

    __context__: ClientError

    def __str__(self):
        return f'{self.message}' + (f' RequestId={self.request_id}' if self.request_id is not None else '')


def handle_request_error(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RequestError as e:
            try:
                request_id = e.__context__.response['ResponseMetadata']['RequestId']
            except Exception:
                request_id = None
            e.request_id = request_id
            raise
    return wrapper


class ProxyBoto3Client:
    def __init__(self, boto3_client: Union[botocore.client.BaseClient, ProxyBoto3Client]):
        self.boto3_client = boto3_client

    def __getattr__(self, item_name):
        if item_name in self.__dict__:
            return getattr(self, item_name)
        else:
            return getattr(self.boto3_client, item_name)

    @property
    def service_id(self) -> str:
        if hasattr(self.boto3_client, 'service_id'):
            return self.boto3_client.service_id
        else:
            return self.boto3_client.meta.service_model.service_id


def proxy_client(*args, **kwargs) -> ProxyBoto3Client:
    return ProxyBoto3Client(boto3.client(*args, **kwargs))


class PausedError(OSError):
    pass


class ControlledBoto3Client(ProxyBoto3Client):
    _flag_session = requests.session()

    FLAGS_URL_PREFIX = config.firebase_realtime_db_configs_url_prefix

    class Flag(enum.Enum):
        PAUSE_CHARGED_AWS_API = 'pause-charged-aws-api'

    CONTROLLING_FLAGS = MappingProxyType({
        'index_faces': Flag.PAUSE_CHARGED_AWS_API,
        'search_faces_by_image': Flag.PAUSE_CHARGED_AWS_API,
        'search_faces': Flag.PAUSE_CHARGED_AWS_API,
        'detect_faces': Flag.PAUSE_CHARGED_AWS_API
    })

    def is_paused(self, flag: Flag) -> bool:
        assert isinstance(flag, self.Flag)
        url = posixpath.join(self.FLAGS_URL_PREFIX, f'{flag.value}.json')
        response = self._flag_session.get(url)
        ret = response.json()
        if not isinstance(ret, bool):
            raise ValueError(f'Invalid value for flag. {dict(url=url, response_content=response.content)}')
        return ret

    def __getattr__(self, item_name):
        ret = super(ControlledBoto3Client, self).__getattr__(item_name)
        if item_name in self.CONTROLLING_FLAGS:
            if not hasattr(ret, '__call__'):
                raise TypeError(f'Controlled method should be a Callable. Got {item_name}: {type(ret)}')
            if self.is_paused(flag=self.CONTROLLING_FLAGS[item_name]):
                raise PausedError(f'For {item_name}, {self.CONTROLLING_FLAGS[item_name]} is True')

        return ret
ControlledBoto3Client._flag_session.mount(ControlledBoto3Client.FLAGS_URL_PREFIX, utils.build_retry_http_adapter())


def controlled_client(*args, **kwargs) -> ControlledBoto3Client:
    return ControlledBoto3Client(proxy_client(*args, **kwargs))


class LoggingBoto3Client(ProxyBoto3Client):
    def __getattr__(self, item_name):
        ret = super(LoggingBoto3Client, self).__getattr__(item_name)
        if hasattr(ret, '__call__'):
            @functools.wraps(ret)
            def wrapper(*args, **kwargs):
                result = ret(*args, **kwargs)

                if len(args) > 0:
                    kwargs['args'] = args
                log_item = utils_firebase_realtime_db.LogItem(client_service_id=self.service_id, client_api_name=item_name, request=kwargs, response=result)
                utils_firebase_realtime_db.post_log(log_item)
                return result
            return wrapper
        else:
            return ret


def logging_client(*args, **kwargs) -> LoggingBoto3Client:
    return LoggingBoto3Client(proxy_client(*args, **kwargs))


def client(*args, **kwargs):
    return LoggingBoto3Client(ControlledBoto3Client(proxy_client(*args, **kwargs)))


@utils_alert.alert_slack_when_exception
def upload_s3(file: Union[str, IO], bucket_name: str, key: str, content_type: Optional[str] = None, content_encoding: Optional[str] = None) -> dict:
    if isinstance(file, str):
        if content_type is None and content_encoding is None:
            content_type, content_encoding = mimetypes.guess_type(file)

        file_should_be_closed = True
        file = open(file, 'rb')
    else:
        file_should_be_closed = False

    s3_client = client('s3')
    if os.sep == '\\':
        key = key.replace(os.sep, '/')
    kwargs = {key: value for key, value in dict(ContentType=content_type, ContentEncoding=content_encoding).items() if value is not None}
    returned = s3_client.put_object(Bucket=bucket_name, Body=file, Key=key, **kwargs)

    if file_should_be_closed:
        file.close()
    return returned


@utils_alert.alert_slack_when_exception
def download_s3(bucket_name: str, key: str) -> bytes:
    s3_client = client('s3')
    returned = s3_client.get_object(Bucket=bucket_name, Key=key)['Body'].read()
    return returned


class BoundingBox(TypedDict):
    Width: float
    Height: float
    Left: float
    Top: float


def to_abs_bounding_box_corners(bounding_box: BoundingBox, size: Tuple[float, float]) -> Tuple[int, int, int, int]:
    x0_rel = bounding_box['Left']
    y0_rel = bounding_box['Top']
    x1_rel = bounding_box['Left'] + bounding_box['Width']
    y1_rel = bounding_box['Top'] + bounding_box['Height']

    x0_abs, x1_abs = [(x * size[0]) for x in [x0_rel, x1_rel]]
    y0_abs, y1_abs = [(y * size[1]) for y in [y0_rel, y1_rel]]
    return int(x0_abs), int(y0_abs), int(x1_abs), int(y1_abs)


def margin_bounding_box(bounding_box: BoundingBox, ratio: float = 0.1) -> BoundingBox:
    margin_size = bounding_box['Width'] * ratio, bounding_box['Height'] * ratio
    assert all(each >= 0 for each in margin_size)
    margined_bounding_box = BoundingBox(Width=bounding_box['Width'] + 2 * margin_size[0], Height=bounding_box['Height'] + 2 * margin_size[1], Left=bounding_box['Left'] - margin_size[0], Top=bounding_box['Top'] - margin_size[1])
    return margined_bounding_box


def join_relative_bounding_boxes(*bounding_boxes) -> BoundingBox:
    if len(bounding_boxes) == 0:
        raise ValueError('No bounding_box provided.')
    joined = BoundingBox(Width=1., Height=1., Left=0., Top=0.)

    for bounding_box in bounding_boxes:
        if any(value > 10. for value in bounding_box.values()):
            raise ValueError(f'Expected relative bounding_box. Got {bounding_box}')
        width, height = joined['Width'] * bounding_box['Width'], joined['Height'] * bounding_box['Height']
        left, top = joined['Left'] + joined['Width'] * bounding_box['Left'], joined['Top'] + joined['Height'] * bounding_box['Top']
        joined = BoundingBox(Width=width, Height=height, Left=left, Top=top)
    return joined


class Face(TypedDict):
    FaceId: str
    BoundingBox: BoundingBox
    ImageId: str
    ExternalImageId: str
    Confidence: float


class FaceMatch(TypedDict):
    Similarity: float
    Face: Face
