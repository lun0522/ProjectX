from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import json
import base64
from PIL import Image
from skimage import io
from io import BytesIO
import dlib
import datetime
import os
import socket


hostName = ""  # if use "localhost", this server will only be accessible for the local machine
hostPort = 8080
authenticationString = "PortableEmotionAnalysis"
temp_dir = "/Users/lun/Desktop/ProjectX/temp/"
predictor_path = "/Users/lun/Desktop/ProjectX/shape_predictor_68_face_landmarks.dat"

detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(predictor_path)


def print_with_date(content):
    print("{} {}".format(time.asctime(), content))


def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


def detect_face_landmark(img):
    bbox_list = detector(img, 1)
    if not len(bbox_list):
        print_with_date("No face found")
        return None
    else:
        print_with_date("{} face(s) found".format(len(bbox_list)))
        result = []
        for num, bbox in enumerate(bbox_list):
            shape = predictor(img, bbox)
            result.append([(point.x, point.y) for point in shape.parts()])
        return result


class MyServer(BaseHTTPRequestHandler):

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_POST(self):
        print_with_date("Receive a request")
        self._set_headers()
        if "Authentication" in self.headers:
            if self.headers["Authentication"] == authenticationString:
                print_with_date("Request is authenticated")
                content_length = int(self.headers['Content-Length'])
                post_data = json.loads(self.rfile.read(content_length))
                if "image" in post_data:
                    print_with_date("Start to process image")

                    os.chdir(temp_dir)
                    temp_file = "{}.jpg".format(int(datetime.datetime.now().timestamp()))
                    img = Image.open(BytesIO(base64.b64decode(post_data["image"])))
                    # photo is always updated in landscape mode, so it need to be rotated
                    img.rotate(-90, expand=True).save(temp_file)
                    landmarks = detect_face_landmark(io.imread(temp_file))
                    os.remove(temp_file)

                    response = {"landmarks": landmarks}
                    self.wfile.write(bytes(json.dumps(response), encoding="utf-8"))
                    print_with_date("Response sent")
                else:
                    print_with_date("Request does not contain image")
            else:
                print_with_date("Request is not authenticated")
        else:
            print_with_date("Request has no authentication string")


if __name__ == "__main__":
    myServer = HTTPServer((hostName, hostPort), MyServer)
    print_with_date("Server starts - {}:{}".format(get_ip_address(), hostPort))

    try:
        myServer.serve_forever()
    except KeyboardInterrupt:
        pass

    myServer.server_close()
    print_with_date("Server stops - {}:{}".format(get_ip_address(), hostPort))
