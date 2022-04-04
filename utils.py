import base64
from io import BytesIO

from PIL import Image

def image_to_base64(image_path) -> bytes:
    with open(image_path, 'rb') as image:
        return image.read()
