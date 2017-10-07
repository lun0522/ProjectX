from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import json
from PIL import Image
from io import BytesIO
import dlib
import socket
from zeroconf import ServiceInfo, Zeroconf
import numpy as np


hostName = ""  # if use "localhost", this server will only be accessible for the local machine
hostPort = 8080
authenticationString = "PortableEmotionAnalysis"
identityString = "PEAServer"
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
    bounding_box = dlib.rectangle(0, 0, img.shape[1], img.shape[0])
    landmark_points = predictor(img, bounding_box)
    return [(point.x, point.y) for point in landmark_points.parts()]


class MyServer(BaseHTTPRequestHandler):

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_POST(self):
        start_time = time.time()
        print_with_date("Receive a request")

        self._set_headers()
        if "Authentication" in self.headers:
            if self.headers["Authentication"] == authenticationString:
                print_with_date("Request is authenticated")

                content_length = int(self.headers['Content-Length'])
                img = Image.open(BytesIO(self.rfile.read(content_length)))

                print_with_date("Start to process image")
                landmarks = detect_face_landmark(np.array(img))

                response = {"landmarks": landmarks}
                self.wfile.write(bytes(json.dumps(response), encoding="utf-8"))

                print_with_date("Response sent")
                print_with_date("Elapsed time {:.3f}s".format(time.time() - start_time))
            else:
                print_with_date("Request is not authenticated")
        else:
            print_with_date("Request has no authentication string")


if __name__ == "__main__":
    myServer = HTTPServer((hostName, hostPort), MyServer)
    ip = get_ip_address()
    print_with_date("Server starts - {}:{}".format(ip, hostPort))

    txtRecord = {"Identity": identityString,
                 "Address": "http://{}:{}".format(ip, hostPort)}
    info = ServiceInfo("_demox._tcp.local.", "server._demox._tcp.local.",
                       socket.inet_aton(ip), 0, properties=txtRecord)
    zeroconf = Zeroconf()
    zeroconf.register_service(info)
    print_with_date("Multi-cast service registered - {}".format(txtRecord))

    try:
        myServer.serve_forever()
    except KeyboardInterrupt:
        print_with_date("Keyboard interrupt")

    myServer.server_close()
    print_with_date("Server stops - {}:{}".format(ip, hostPort))

    zeroconf.unregister_service(info)
    zeroconf.close()
    print_with_date("Multi-cast service unregistered - {}".format(txtRecord))
