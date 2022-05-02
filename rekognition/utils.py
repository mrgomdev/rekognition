from typing import Optional, Union, Tuple
import io

from PIL import Image

import requests

try:
    from . import utils_alert
except ImportError:
    import utils_alert


def pillow_to_bytes(image: Image.Image, format: Optional[str] = None) -> bytes:
    buffer = io.BytesIO()
    if format is None:
        format = image.format if image.format is not None else 'JPEG'
    if format == 'JPEG' and image.mode != 'RGB':
        image = image.convert('RGB')
    image.save(buffer, format=format)
    return buffer.getvalue()


def as_image_bytes(image: Union[Image.Image, bytes]) -> bytes:
    if isinstance(image, Image.Image):
        image_bytes = pillow_to_bytes(image=image, format='JPEG')
    elif isinstance(image, bytes):
        image_bytes = image
    else:
        raise TypeError(f"Union[Image.Image, bytes] Expected. Got {type(image)}")
    return image_bytes


MAX_IMAGE_LENGTH = 1920
@utils_alert.alert_slack_when_exception
def convert_image_bytes_popular(image_bytes: bytes) -> bytes:
    image = convert_pillow_image_popular(Image.open(io.BytesIO(image_bytes)))

    output_format = image.format if image.format in ['JPEG', 'PNG'] else 'PNG'
    return pillow_to_bytes(image=image, format=output_format)


@utils_alert.alert_slack_when_exception
def roughly_fit_to(image: Image.Image, target_size: Tuple[float, float], zoom_threshold: float = 0.9) -> Image.Image:
    zoom = 1.
    zoom = min(zoom, target_size[0] / image.size[0])
    zoom = min(zoom, target_size[1] / image.size[1])

    if zoom < zoom_threshold:
        assert image.size[0] * zoom > 10 and image.size[1] * zoom > 10, f'Size of image is too small {image.size}, zoom={zoom}.'
        image = image.resize(size=(int(image.size[0] * zoom), int(image.size[1] * zoom)))
    else:
        image = image.copy()
    return image

@utils_alert.alert_slack_when_exception
def convert_pillow_image_popular(image: Image.Image) -> Image.Image:
    old_image_format = image.format
    image = roughly_fit_to(image, target_size=(MAX_IMAGE_LENGTH, MAX_IMAGE_LENGTH))
    image.format = old_image_format

    if all(allowed not in image.format.lower() for allowed in ['jpeg', 'jpg', 'png']):
        image = image.convert('RGB')
        image.format = 'JPEG'
    return image


def get_error_image(url="https://twemoji.maxcdn.com/v/14.0.2/72x72/1f6ab.png") -> Image.Image:
    with requests.session() as session:
        response = session.get(url=url)
        image = Image.open(io.BytesIO(response.content))
    return image
