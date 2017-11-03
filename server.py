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
"""


def print_with_date(content):
    print("{} {}".format(time.asctime(), content))


def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


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
                image = Image.open(BytesIO(self.rfile.read(content_length)))
                img_data = np.array(image)

                print_with_date("Start to process image")

                landmarks = detect_face_landmark(img_data, create_rect(0, 0, image.size[0], image.size[1]))
                style_idx = retrieve_painting(landmarks, image) % 32

                os.chdir(tmp_dir)
                image.save("tmp.jpg")
                subprocess.call([transfer_command.format("tmp.jpg", style_idx, "./")], shell=True)

                stylized = "stylized_{}.png".format(style_idx)
                with open(stylized, "rb") as fp:
                    response = {"landmarks": landmarks, "stylized": str(fp.read())}
                    self.wfile.write(bytes(json.dumps(response), encoding="utf-8"))

                os.remove(stylized)

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

    subprocess.call(["source activate magenta"], shell=True)

    try:
        myServer.serve_forever()
    except KeyboardInterrupt:
        print_with_date("Keyboard interrupt")

    subprocess.call(["source deactivate"], shell=True)

    myServer.server_close()
    print_with_date("Server stops - {}:{}".format(ip, hostPort))

    zeroconf.unregister_service(info)
    zeroconf.close()
    print_with_date("Multi-cast service unregistered - {}".format(txtRecord))
