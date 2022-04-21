import io
import os
import urllib.parse

from PIL import Image
import requests
import streamlit as st

import rekognition.utils_alert
import rekognition.utils_boto3
import rekognition.utils
import rekognition.manage_faces


SESSION_STATE_INITS = dict(file_uploader_key_index=0)
for key, value in SESSION_STATE_INITS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def main():
    with st.container():
        st.header('Upload new image')

        if st.button(label='Upload'):
            with st.spinner():
                upload()

        st.text_input(label='idol_id', placeholder='jennie-blackpink', key='idol_id')

        url = st.text_input(label="url", placeholder="https://...", key='url')
        def clear_url():
            st.session_state.url = ''
        if st.button('preview'):
            st.image(url)
            st.session_state.file_uploader_key_index += 1

        # TODO:
        file = st.file_uploader(label='image', accept_multiple_files=False, key=f'file_uploader{st.session_state.file_uploader_key_index}', on_change=clear_url)


def upload():
    try:
        if st.session_state.idol_id == '':
            raise ValueError("idol_id must not be empty!")

        with requests.session() as session:
            response = session.get(url=st.session_state.url)
            if not response.headers['Content-Type'].startswith('image/'):
                raise ValueError(f"Should be image! {response.headers['Content-Type']}")
            image = Image.open(io.BytesIO(response.content))
            image = rekognition.utils.convert_pillow_image_popular(image)

        content_type = Image.MIME[image.format]
        image_bytes_io = io.BytesIO()
        image.save(image_bytes_io, format=image.format)
        image_bytes_io.seek(0)

        idol_id = st.session_state.idol_id
        image_s3_bucket_name = rekognition.config.idols_bucket_name
        image_s3_object_key = os.path.join(rekognition.config.idols_profile_root_path, idol_id, os.path.basename(urllib.parse.urlparse(url=st.session_state.url).path)).replace('\\', '/')

        result = rekognition.manage_faces.upload_idol(image=image_bytes_io, idol_id=idol_id, image_s3_bucket_name=image_s3_bucket_name, image_s3_object_key=image_s3_object_key, content_type=content_type)
        face_meta = result['FaceRecords'][0]['Face']

        db_dict = {
            'face_id': face_meta['FaceId'],
            'idol_id': idol_id,
            'collection_id': rekognition.config.idols_collection_id,
            'image_id': face_meta['ImageId'],
            'external_image_id': face_meta['ExternalImageId'],
            'image_s3_bucket_name': image_s3_bucket_name,
            'image_s3_object_key': image_s3_object_key,
            'image_from_url': st.session_state.url
        }
        st.code(','.join([db_dict[key] for key in ['face_id', 'idol_id', 'collection_id', 'image_id', 'external_image_id', 'image_s3_bucket_name', 'image_s3_object_key', 'image_from_url']]))
        st.success(dict(face=face_meta, idol_id=idol_id, image_s3_bucket_name=image_s3_bucket_name, image_s3_object_key=image_s3_object_key, content_type=content_type))
    except Exception as e:
        st.exception(e)


if __name__ == '__main__':
    main()
