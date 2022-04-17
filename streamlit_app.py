import io
from typing import TypedDict, Tuple

from PIL import Image, ImageDraw

import streamlit as st

import flask_app.models
import rekognition.utils_alert
import rekognition
import rekognition.utils
import utils_streamlit
import streamlit_config


class MatchParsed(TypedDict):
    idol: rekognition.Idol
    similarity: float


def suggest_line_width(size: Tuple[float, float]) -> int:
    longer = max(size)
    return max(1, int(longer * 0.01))


@rekognition.utils_alert.alert_slack_when_exception
def main():
    file = st.file_uploader('Image of the star you are watching.', type=streamlit_config.image_types)

    if file is not None:
        file_bytes = file.read()
        try:
            matches_response: flask_app.models.UploadPostPayload = utils_streamlit.call_api(url_path='/upload', method='POST', files=dict(file=file_bytes))
        except Exception as e:
            rekognition.utils_alert.alert_slack_exception(e)
            st.write('Error on receiving result.')
            return

        column1, column2 = st.columns(2)
        with column1:
            try:
                canvas_image = Image.open(io.BytesIO(file_bytes))
                zoom = 400 / canvas_image.size[1]
                if zoom * canvas_image.size[0] > 400:
                    zoom = 400 / canvas_image.size[0]
                canvas_image = canvas_image.resize(size=(int(canvas_image.size[0] * zoom), int(canvas_image.size[1] * zoom)))
                draw = ImageDraw.Draw(canvas_image)
                bounding_box_corners = rekognition.utils_boto3.to_abs_bounding_box_corners(bounding_box=matches_response['searched_face_bounding_box'], size=canvas_image.size)
                draw.rounded_rectangle(xy=bounding_box_corners, radius=suggest_line_width(canvas_image.size) * 4, width=suggest_line_width(canvas_image.size))
            except Exception as e:
                rekognition.utils_alert.alert_slack_exception(exception=e)
                canvas_image = rekognition.utils.get_error_image()
            st.image(image=canvas_image)
        with column2:
            for each_match in matches_response['matches']:
                try:
                    idol = rekognition.Idol.from_external_image_id(each_match['Face']['ExternalImageId'])
                    similarity = each_match['Similarity']
                except Exception as e:
                    rekognition.utils_alert.alert_slack_exception(exception=e)
                    st.write("Error occured. Please contact the developer.")
                else:
                    st.write(idol.repr_name, similarity)

                    try:
                        detail_response: flask_app.models.DetailPayload = utils_streamlit.call_api(url_path=f'/detail/{idol.repr_name}')
                        detail_md = detail_response['markdown']
                    except Exception as e:
                        rekognition.utils_alert.alert_slack_exception(exception=e)
                    else:
                        st.markdown(detail_md)


if __name__ == '__main__':
    main()
