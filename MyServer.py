from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import json
import base64
from PIL import Image
from io import BytesIO


hostName = ""  # if use "localhost", this server will only be accessible for the local machine
hostPort = 8080
authenticationString = "PortableEmotionAnalysis"


class MyServer(BaseHTTPRequestHandler):

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_POST(self):
        print(self.headers)
        self._set_headers()
        if "Authentication" in self.headers:
            if self.headers["Authentication"] == authenticationString:
                content_length = int(self.headers['Content-Length'])
                image_data = json.loads(self.rfile.read(content_length))["image"]
                image = Image.open(BytesIO(base64.b64decode(image_data)))
                image.rotate(-90).show()
                response = {"word": "thank you"}
                self.wfile.write(bytes(json.dumps(response), encoding="utf-8"))


if __name__ == "__main__":
    myServer = HTTPServer((hostName, hostPort), MyServer)
    print("{} Server starts - {}:{}".format(time.asctime(), hostName, hostPort))

    try:
        myServer.serve_forever()
    except KeyboardInterrupt:
        pass

    myServer.server_close()
    print("{} Server stops - {}:{}".format(time.asctime(), hostName, hostPort))
