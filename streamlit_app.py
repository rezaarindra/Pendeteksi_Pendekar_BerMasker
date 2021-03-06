import streamlit as st
from PIL import Image, ImageEnhance
import numpy as np
import av
import cv2
import os
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model
import detect_mask_image
from streamlit_webrtc import VideoTransformerBase, webrtc_streamer

def local_css(file_name):
    """ Method for reading styles.css and applying necessary changes to HTML"""
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)



def mask_image_init():
    # load our serialized face detector model from disk
    print("[INFO] loading face detector model...")
    prototxtPath = os.path.sep.join(["face_detector", "deploy.prototxt"])
    weightsPath = os.path.sep.join(["face_detector",
                                    "res10_300x300_ssd_iter_140000.caffemodel"])
    net = cv2.dnn.readNet(prototxtPath, weightsPath)

    # load the face mask detector model from disk
    print("[INFO] loading face mask detector model...")
    model = load_model("mask_detector.model")
    return net, model


def get_detections_from_image(net, image):
    # construct a blob from the image
    blob = cv2.dnn.blobFromImage(image, 1.0, (300, 300),
                                 (104.0, 177.0, 123.0))

    # pass the blob through the network and obtain the face detections
    net.setInput(blob)
    return net.forward()

def mask_image(model, detections, image):
    (h, w) = image.shape[:2]

    # loop over the detections
    for i in range(0, detections.shape[2]):
        # extract the confidence (i.e., probability) associated with
        # the detection
        confidence = detections[0, 0, i, 2]

        # filter out weak detections by ensuring the confidence is
        # greater than the minimum confidence
        if confidence > 0.5:
            # compute the (x, y)-coordinates of the bounding box for
            # the object
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            # ensure the bounding boxes fall within the dimensions of
            # the frame
            (startX, startY) = (max(0, startX), max(0, startY))
            (endX, endY) = (min(w - 1, endX), min(h - 1, endY))

            # extract the face ROI, convert it from BGR to RGB channel
            # ordering, resize it to 224x224, and preprocess it
            face = image[startY:endY, startX:endX]
            face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
            face = cv2.resize(face, (224, 224))
            face = img_to_array(face)
            face = preprocess_input(face)
            face = np.expand_dims(face, axis=0)

            # pass the face through the model to determine if the face
            # has a mask or not
            (mask, withoutMask) = model.predict(face)[0]

            # determine the class label and color we'll use to draw
            # the bounding box and text
            label = "Bermasker" if mask > withoutMask else "Tidak Bermasker"
            color = (0, 255, 0) if label == "Bermasker" else (0, 0, 255)

            # include the probability in the label
            label = "{}: {:.2f}%".format(label, max(mask, withoutMask) * 100)

            # display the label and bounding box rectangle on the output
            # frame
            cv2.putText(image, label, (startX, startY - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
            cv2.rectangle(image, (startX, startY), (endX, endY), color, 2)
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def mask_detection():
    class VideoTransformer(VideoTransformerBase):
        def __init__(self) -> None:
            (self.net, self.model) = mask_image_init()

        def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
            image = frame.to_ndarray(format="bgr24")
            detections = get_detections_from_image(self.net, image)
            RGB_img = mask_image(self.model, detections, image)
            return av.VideoFrame.from_ndarray(RGB_img, format="bgr24")

    local_css("css/styles.css")

    st.markdown('<h1 align="center">???? Pendeteksi Wajah BerMasker</h1>', unsafe_allow_html=True)
    activities = ["Melalui Gambar", "Melalui Webcam"]
    st.set_option('deprecation.showfileUploaderEncoding', False)
    st.sidebar.markdown("# Mask Detection on?")
    choice = st.sidebar.selectbox("Pilih Beberapa Pilihan:", activities)

    if choice == 'Melalui Gambar':
        st.markdown('<h2 align="center">Detection Berdasarkan Gambar</h2>', unsafe_allow_html=True)
        st.markdown("### Upload Gambarmu Disini ???")
        image_file = st.file_uploader("", type=['jpg'])  # upload image
        if image_file is not None:
            our_image = Image.open(image_file)  # making compatible to PIL
            im = our_image.save('./images/out.jpg')
            saved_image = st.image(image_file, caption='', use_column_width=True)
            st.markdown('<h3 align="center">Gambar Berhasil Di Upload!</h3>', unsafe_allow_html=True)
            if st.button('Process'):
                # load the input image from disk and grab the image spatial
                # dimensions
                image = cv2.imread("./images/out.jpg")
                (net, model) = mask_image_init()
                detections = get_detections_from_image(net, image)
                RGB_img = mask_image(model, detections, image)
                st.image(RGB_img, use_column_width=True)

    if choice == 'Melalui Webcam':
        st.markdown('<h2 align="center">Detection Secara Realtime</h2>', unsafe_allow_html=True)
        webrtc_streamer(key="example", video_processor_factory=VideoTransformer)


if __name__ == "__main__":
    # Setting custom Page Title and Icon with changed layout and sidebar state
    st.set_page_config(page_title='Pendeteksi Wajah BerMasker', page_icon='????', layout='centered', initial_sidebar_state='expanded')
    mask_detection()