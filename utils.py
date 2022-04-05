import io

from PIL import Image


MAX_LENGTH = 1920
def convert_image_bytes_popular(image_bytes: bytes) -> bytes:
    image = Image.open(io.BytesIO(image_bytes))

    zoom = 1
    for each_length in image.size:
        zoom = min(zoom, MAX_LENGTH / each_length)
    if zoom < 0.9:
        image = image.resize(size=tuple(int(each * zoom) for each in image.size))

    output_format = image.format if image.format in ['JPEG', 'PNG'] else 'PNG'
    buffer = io.BytesIO()
    image.save(buffer, format=output_format)
    return buffer.getvalue()
