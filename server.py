from http.server import BaseHTTPRequestHandler, HTTPServer
import time
from PIL import Image
from io import BytesIO
from detector import create_rect, detect_face_landmark
import socket
from zeroconf import ServiceInfo, Zeroconf
import numpy as np
from comparator import retrieve_painting
import subprocess
import os

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

    def _set_headers(self, code, content_type="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.end_headers()

    def do_POST(self):
        start_time = time.time()
        print_with_date("Receive a POST request")

        if "Authentication" in self.headers and self.headers["Authentication"] == authenticationString:
            if "Operation" in self.headers and "Timestamp" in self.headers:
                if self.headers["Operation"] == "Store":
                    content_length = int(self.headers["Content-Length"])
                    photo = Image.open(BytesIO(self.rfile.read(content_length)))

                    # currently set a limit to the length of the longer side of the photo
                    limit = 500
                    if photo.size[0] > limit or photo.size[1] > limit:
                        ratio = max(photo.size[0], photo.size[1]) / limit
                        photo = photo.resize((int(photo.size[0] / ratio), int(photo.size[1] / ratio)), Image.ANTIALIAS)

                    photo.save("{}{}.jpg".format(tmp_dir, self.headers["Timestamp"]))
                    self._set_headers(200)

                elif self.headers["Operation"] == "Transfer":
                    os.chdir(tmp_dir)
                    photo_path = "{}.jpg".format(self.headers["Timestamp"])
                    if os.path.isfile(photo_path):
                        content_length = int(self.headers["Content-Length"])
                        face_image = Image.open(BytesIO(self.rfile.read(content_length)))

                        landmarks = detect_face_landmark(np.array(face_image),
                                                         create_rect(0, 0, face_image.size[0], face_image.size[1]))
                        style_idx = retrieve_painting(landmarks, face_image) % 32

                        print_with_date("Start transfer style: {}".format(style_idx))
                        subprocess.call([transfer_command.format(photo_path, style_idx, "./")], shell=True)

                        stylized = "stylized_{}.png".format(style_idx)
                        with open(stylized, "rb") as fp:
                            self._set_headers(200, "application/octet-stream")
                            self.wfile.write(fp.read())

                        print_with_date("Transfer finished")
                        os.remove(stylized)

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
