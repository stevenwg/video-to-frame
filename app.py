import base64
import os
from urllib.parse import quote as urlquote

from flask import Flask, send_from_directory, Response
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

import numpy as np
import cv2


UPLOAD_DIRECTORY = "/Users/luffy/Downloads/GitHub/video-to-frame/upload-files"

if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

# Normally, Dash creates its own Flask server internally. By creating our own,
# we can create a route for downloading files directly:
server = Flask(__name__)
app = dash.Dash(server=server, external_stylesheets=[dbc.themes.BOOTSTRAP])

class video_object(object):
    def __init__(self, URL):
        self.video = cv2.VideoCapture(URL)

    def __del__(self):
        self.video.release()

    def get_frame(self):
        success, image = self.video.read()
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()

    def get_video_frame_nums(self):
        return self.video.get(cv2.CAP_PROP_FRAME_COUNT)
    
progress_percentage = 0
    
def get_every_frame_from_video(video_object, folder_path):
    global progress_percentage
    success,image = video_object.video.read()
    count = 0
    amount_of_frames = video_object.get_video_frame_nums()
    while success:
        file_path = os.path.join(folder_path, "frame%d.jpg" % count)
        cv2.imwrite(file_path, image)     # save frame as JPEG file
        success,image = video_object.video.read()
        progress_percentage = count / amount_of_frames * 100
        count += 1

@server.route("/download/<path:path>")
def download(path):
    """Serve a file from the upload directory."""
    return send_from_directory(UPLOAD_DIRECTORY, path, as_attachment=True)


progress = html.Div(
    [
        dcc.Interval(id="progress-interval", n_intervals=0),
        dbc.Progress(id="progress", striped=True, animated=True),
    ]
)

app.layout = html.Div(
    [
        html.H1("Video to Frame"),
        html.H2("Upload"),
        dcc.Upload(
            id="upload-data",
            children=html.Div(
                ["Drag and drop or click to select a video to upload."]
            ),
            style={
                "width": "100%",
                "height": "60px",
                "lineHeight": "60px",
                "borderWidth": "1px",
                "borderStyle": "dashed",
                "borderRadius": "5px",
                "textAlign": "center",
                "margin": "10px",
            },
            multiple=True,
        ),
        html.H2("Video"),
        html.Ul(id="video-preview-label"),
        progress,
    ],
    style={"max-width": "500px"},
)


def save_file(name, content):
    """Decode and store a file uploaded with Plotly Dash."""
    data = content.encode("utf8").split(b";base64,")[1]
    with open(os.path.join(UPLOAD_DIRECTORY, name), "wb") as fp:
        fp.write(base64.decodebytes(data))


def uploaded_files():
    """List the files in the upload directory."""
    files = []
    for filename in os.listdir(UPLOAD_DIRECTORY):
        path = os.path.join(UPLOAD_DIRECTORY, filename)
        if os.path.isfile(path):
            files.append(filename)
    return files


def file_download_link(filename):
    """Create a Plotly Dash 'A' element that downloads a file from the app."""
    location = "/download/{}".format(urlquote(filename))
    return html.A(filename, href=location)

def load_video(filename):
    path = os.path.join(UPLOAD_DIRECTORY, filename)
    video = video_object(path)
    return video

@app.callback(
    Output("video-preview-label", "children"),
    [Input("upload-data", "filename"), Input("upload-data", "contents")],
)
def update_output(uploaded_filenames, uploaded_file_contents):
    """Save uploaded files and regenerate the file list."""
    if uploaded_filenames is not None and uploaded_file_contents is not None:
        if len(uploaded_filenames) > 1:
            return [html.Li("Choose one video")]
        save_file(uploaded_filenames[0], uploaded_file_contents[0])
        
        if uploaded_filenames[0].lower().endswith((".avi", ".mp4", ".mov", ".3gp")):
            folder_path = os.path.join(UPLOAD_DIRECTORY, os.path.splitext(uploaded_filenames[0])[0])
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            video = load_video(uploaded_filenames[0])
            amount_of_frames = video.get_video_frame_nums()
            get_every_frame_from_video(video, folder_path)
            return [html.Li("Total frames: %d" % amount_of_frames)]


    files = uploaded_files()
    if len(files) == 0:
        return [html.Li("No video yet!")]
    else:
        return [html.Li(file_download_link(filename)) for filename in files]

@app.callback(
    [Output("progress", "value"), Output("progress", "children")],
    [Input("progress-interval", "n_intervals")],
)
def update_progress(_):
    global progress_percentage
    progress = int(progress_percentage)
    return progress, f"{progress} %" if progress >= 5 else ""

if __name__ == "__main__":
    app.run_server(debug=True, port=8080)