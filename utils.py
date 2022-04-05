import base64
from io import BytesIO

from PIL import Image

def load_image_bytes(image_path) -> bytes:
    with open(image_path, 'rb') as image:
        return image.read()
