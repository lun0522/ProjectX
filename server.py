from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import json
from PIL import Image
from io import BytesIO
from detector import create_rect, detect_face_landmark
import socket
from zeroconf import ServiceInfo, Zeroconf
import numpy as np
from comparator import retrieve_painting
import subprocess
import glob
import os
import base64

hostName = ""  # if use "localhost", this server will only be accessible for the local machine
hostPort = 8080
authenticationString = "PortableEmotionAnalysis"
identityString = "PEAServer"
tmp_dir = "/Users/lun/Desktop/ProjectX/temp/"
transfer_command = """
source activate magenta
image_stylization_transform \
--num_styles=32 \
--checkpoint=/Users/lun/Desktop/ProjectX/varied.ckpt \
--input_image={} \
--which_styles="[{}]" \
--output_dir={} \
--output_basename="stylized"
source deactivate
"""


def print_with_date(content):
    print("{} {}".format(time.asctime(), content))


def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


class MyServer(BaseHTTPRequestHandler):

    def _set_headers(self, code):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_POST(self):
        start_time = time.time()
        print_with_date("Receive a POST request")

        if "Authentication" in self.headers and self.headers["Authentication"] == authenticationString:
            if "Operation" in self.headers and "Timestamp" in self.headers:
                if self.headers["Operation"] == "Store":
                    content_length = int(self.headers["Content-Length"])
                    photo = Image.open(BytesIO(self.rfile.read(content_length)))
                    photo.save("{}{}.jpg".format(tmp_dir, self.headers["Timestamp"]))
                    self._set_headers(200)

                elif self.headers["Operation"] == "Transfer":
                    os.chdir(tmp_dir)
                    photo_path = "{}.jpg".format(self.headers["Timestamp"])
                    if os.path.isfile(photo_path):
                        content_length = int(self.headers["Content-Length"])
                        selfie = Image.open(BytesIO(self.rfile.read(content_length)))
                        selfie_data = np.array(selfie)

                        landmarks = detect_face_landmark(selfie_data, create_rect(0, 0, selfie.size[0], selfie.size[1]))
                        style_idx = retrieve_painting(landmarks, selfie) % 32

                        subprocess.call([transfer_command.format(photo_path, style_idx, "./")], shell=True)

                        stylized = "stylized_{}.png".format(style_idx)
                        with open(stylized, "rb") as fp:
                            response = {"Landmarks": landmarks, "Stylized": str(fp.read())}
                            self.wfile.write(bytes(json.dumps(response), encoding="utf-8"))
                            os.remove(stylized)
                        self._set_headers(200)

                    else:
                        print_with_date("Photo not exist: {}".format(photo_path))
                        self._set_headers(404)
                else:
                    print_with_date("Unknown operation: {}".format(self.headers["Operation"]))
                    self._set_headers(400)
            else:
                print_with_date("No operation provided")
                self._set_headers(400)
        else:
            print_with_date("Not authenticated")
            self._set_headers(401)

        print_with_date("Response sent")
        print_with_date("Elapsed time {:.3f}s".format(time.time() - start_time))

    def do_DELETE(self):
        start_time = time.time()
        print_with_date("Receive a DELETE request")

        if "Authentication" in self.headers and self.headers["Authentication"] == authenticationString:
            if "Timestamp" in self.headers:
                file_path = "{}{}.jpg".format(tmp_dir, self.headers["Timestamp"])
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print_with_date("{} removed".format(file_path))
                else:
                    print_with_date("{} not exists".format(file_path))
                self._set_headers(200)
            else:
                print_with_date("No timestamp provided")
                self._set_headers(400)
        else:
            print_with_date("Not authenticated")
            self._set_headers(401)

        print_with_date("Response sent")
        print_with_date("Elapsed time {:.3f}s".format(time.time() - start_time))


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
