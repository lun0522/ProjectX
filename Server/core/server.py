from http.server import BaseHTTPRequestHandler, HTTPServer
import time
from io import BytesIO
import json
import socket
import os
import subprocess
import glob

import requests
import numpy as np
from PIL import Image
from zeroconf import ServiceInfo, Zeroconf
from sklearn.externals import joblib

from database.modelDB import emotions
from core.comparator import Comparator
from core.detector import create_rect, detect_landmarks, normalize_landmarks, pose_landmarks
from database.paintingDB import style_dir, tmp_dir, get_painting_filename, get_all_landmarks, svm_dir, faces_dir
from transfer.transfer import StyleTransfer

host_name = ""  # if use "localhost", this server will only be accessible for the local machine
host_port = 8080
auth_string = "PortableEmotionAnalysis"
id_string = "PEAServer"
app_id = "OH4VbcK1AXEtklkhpkGCikPB-MdYXbMMI"
app_key = "0azk0HxCkcrtNGIKC5BMwxnr"
cloud_url = "https://us-api.leancloud.cn/1.1/classes/Server/5a40a4eee37d040044aa4733"
valid_operations = {"Store", "Delete", "Retrieve", "Transfer"}

svm = joblib.load(svm_dir)
paintings = get_all_landmarks()
painting_landmarks = [[] for _ in range(len(emotions))]
painting_map = [[] for _ in range(len(emotions))]
for lid, pid, eid, _, points, _ in paintings:
    painting_map[eid].append([lid, pid])
    painting_landmarks[eid].append(points)
painting_comparators = [Comparator(points, 3) for points in painting_landmarks]
style_transfer = StyleTransfer(style_dir)
painting_faces = []
for img_file in sorted(glob.glob(os.path.join(faces_dir, "*.jpg"))):
    painting_faces.append(Image.open(img_file))


def print_with_date(content):
    print("{} {}".format(time.asctime(), content))


def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


def publish_address(address):
    headers = {"X-LC-Id": app_id,
               "X-LC-Key": app_key,
               "Content-Type": "application/json"}
    response = requests.put(cloud_url, headers=headers, json={"address": address})
    if response.status_code != 200:
        print_with_date("Failed in publishing server address: {}".format(response.reason))


class MyServer(BaseHTTPRequestHandler):

    def _set_headers(self, code, content_type="application/json", extra_info=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        if extra_info:
            [self.send_header(key, value) for key, value in extra_info.items()]
        self.end_headers()

    def do_POST(self):
        start_time = time.time()
        print_with_date("Receive a POST request")

        if "Authentication" not in self.headers or self.headers["Authentication"] != auth_string:
            print_with_date("Not authenticated")
            self._set_headers(401)

        elif "Operation" not in self.headers or self.headers["Operation"] not in valid_operations:
            print_with_date("No operation / Invalid operation")
            self._set_headers(400)

        elif self.headers["Operation"] == "Store":
            if "Photo-Timestamp" not in self.headers:
                print_with_date("No timestamp provided")
                self._set_headers(400)

            else:
                content_length = int(self.headers["Content-Length"])
                photo = Image.open(BytesIO(self.rfile.read(content_length)))

                # currently set a limit to the length of the longer side of the photo
                limit = 500
                if photo.size[0] > limit or photo.size[1] > limit:
                    ratio = max(photo.size[0], photo.size[1]) / limit
                    photo = photo.resize((int(photo.size[0] / ratio), int(photo.size[1] / ratio)), Image.ANTIALIAS)

                photo.save("{}{}.jpg".format(tmp_dir, self.headers["Photo-Timestamp"]))
                self._set_headers(200)

        elif self.headers["Operation"] == "Retrieve":
            content_length = int(self.headers["Content-Length"])
            face_image = Image.open(BytesIO(self.rfile.read(content_length)))

            bounding_box = create_rect(0, 0, face_image.size[1], face_image.size[0])
            landmarks = detect_landmarks(np.array(face_image), bounding_box)
            normalized = normalize_landmarks(landmarks)
            posed = pose_landmarks(landmarks)

            image_info, image_bytes = [], BytesIO()
            emotion_id = svm.predict([posed])[0]
            for idx in painting_comparators[emotion_id](normalized):
                face_id, painting_id = painting_map[emotion_id][idx]
                face = painting_faces[face_id - 1]
                prev_len = len(image_bytes.getvalue())
                original = Image.open(get_painting_filename(painting_id))
                original.save(image_bytes, format="jpeg")
                mid_len = len(image_bytes.getvalue())
                face.save(image_bytes, format="jpeg")
                image_info.append({
                    "Painting-Id": painting_id,
                    "Painting-Length": mid_len - prev_len,
                    "Portrait-Length": len(image_bytes.getvalue()) - mid_len,
                })

            self._set_headers(200, "application/octet-stream", {"Image-Info": json.dumps(image_info)})
            self.wfile.write(image_bytes.getvalue())

        elif self.headers["Operation"] == "Transfer":
            os.chdir(tmp_dir)
            photo_path = "{}.jpg".format(self.headers["Photo-Timestamp"])
            if os.path.isfile(photo_path):
                style_id = int(self.headers["Style-Id"])
                print_with_date("Start transfer style {}".format(style_id))

                # style_id should subtract 1 before used as index, since the database starts indexing from 1
                stylized = Image.fromarray(style_transfer(photo_path, tmp_dir, style_id - 1))
                image_bytes = BytesIO()
                stylized.save(image_bytes, format="jpeg")

                self._set_headers(200, "application/octet-stream")
                self.wfile.write(image_bytes.getvalue())

        else:
            print_with_date("Shouldn't reach here")
            self._set_headers(404)

        print_with_date("Response sent")
        print_with_date("Elapsed time {:.3f}s".format(time.time() - start_time))

    def do_DELETE(self):
        start_time = time.time()
        print_with_date("Receive a DELETE request")

        if "Authentication" not in self.headers or self.headers["Authentication"] != auth_string:
            print_with_date("Not authenticated")
            self._set_headers(401)

        elif "Photo-Timestamp" not in self.headers:
            print_with_date("No timestamp provided")
            self._set_headers(400)

        else:
            file_path = "{}{}.jpg".format(tmp_dir, self.headers["Photo-Timestamp"])
            if os.path.isfile(file_path):
                os.remove(file_path)
                print_with_date("{} removed".format(file_path))
            else:
                print_with_date("{} not exists".format(file_path))
            self._set_headers(200)

        print_with_date("Response sent")
        print_with_date("Elapsed time {:.3f}s".format(time.time() - start_time))


if __name__ == "__main__":
    server = HTTPServer((host_name, host_port), MyServer)
    ip = get_ip_address()
    server_address = "http://{}:{}".format(ip, host_port)
    publish_address(server_address)
    print_with_date("Server started - " + server_address)

    txtRecord = {"Identity": id_string,
                 "Address": server_address}
    info = ServiceInfo("_demox._tcp.local.", "server._demox._tcp.local.",
                       socket.inet_aton(ip), 0, properties=txtRecord)
    zeroconf = Zeroconf()
    zeroconf.register_service(info)
    print_with_date("Multi-cast service registered - {}".format(txtRecord))

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print_with_date("Keyboard interrupt")

    server.server_close()
    print_with_date("Server stopped - " + server_address)

    subprocess.call(["cd {}; rm *".format(tmp_dir)], shell=True)
    print_with_date("Temp folder cleared")

    zeroconf.unregister_service(info)
    zeroconf.close()
    print_with_date("Multi-cast service unregistered - {}".format(txtRecord))
