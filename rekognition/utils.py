import io

from PIL import Image

import requests


MAX_IMAGE_BYTES_LENGTH = 1920
def convert_image_bytes_popular(image_bytes: bytes) -> bytes:
    image = Image.open(io.BytesIO(image_bytes))

    zoom = 1
    for each_length in image.size:
        zoom = min(zoom, MAX_IMAGE_BYTES_LENGTH / each_length)
    if zoom < 0.9:
        assert image.size[0] * zoom > 10 and image.size[1] * zoom > 10, f'Size of image is too small {image.size}, zoom={zoom}.'
        image = image.resize(size=(int(image.size[0] * zoom), int(image.size[1] * zoom)))

    output_format = image.format if image.format in ['JPEG', 'PNG'] else 'PNG'
    buffer = io.BytesIO()
    image.save(buffer, format=output_format)
    return buffer.getvalue()


def get_error_image(url="https://twemoji.maxcdn.com/v/14.0.2/72x72/1f6ab.png") -> Image.Image:
    with requests.session() as session:
        response = session.get(url=url)
        image = Image.open(io.BytesIO(response.content))
    return image
