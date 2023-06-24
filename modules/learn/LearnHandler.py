from http.server import BaseHTTPRequestHandler
import threading
import json, os
import numpy as np

class LearnHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        status = 500
        if ".h5" in self.path:
            fileName = self.path[1:]
            if os.path.exists("models/%s" % fileName):
                self.send_response(200)
                self.send_header('Content-type', 'application/octet-stream')
                self.end_headers()
                with open("models/%s" % fileName, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                response = {
                    'status': 'ng',
                    'message': 'File not found'
                }
                status = 404
        elif self.path == "/hello":
            response = {
                "status": "ok",
                "info": {
                    "type": "learn"
                }
            }
            status = 200
        else:
            currentVersion = {
                "version": 0,
                "count": 0
            }
            if os.path.exists('models/version.json'):
                with open("models/version.json", "r") as f:
                    currentVersion = json.load(f)
            response = {
                'status': 'ok',
                'version': currentVersion["version"],
                'count': currentVersion["count"]
            }
            status = 200
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        responseBody = json.dumps(response)
        self.wfile.write(responseBody.encode('utf-8'))


    def do_POST(self):
        try:
            content_len=int(self.headers.get('content-length'))
            id = str(self.headers.get('id'))
            if self.path == "/videoND":
                width = int(self.headers.get('width'))
                height = int(self.headers.get('height'))
                frameCount = int(self.headers.get('frameCount'))
                self.server.parent.videoFrames[id] = np.frombuffer(self.rfile.read(content_len), dtype=np.uint8).reshape((frameCount, height, width, 3))
                status_code = 200
                response = {
                    'status': 'ok'
                }
            else:
                requestBody = json.loads(self.rfile.read(content_len).decode('utf-8'))
                if "data" in requestBody:
                    if len(requestBody["data"]) > 0:
                        self.server.parent.moveFrames[id] = requestBody
                status_code = 200
                response = {
                    'status' : "ok",
                }
            self.send_response(status_code)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            responseBody = json.dumps(response)

            self.wfile.write(responseBody.encode('utf-8'))
            threading.Thread(target=self.server.parent.check).start()
        except Exception as e:
            print("An error occured")
            print("The information of error is as following")
            print(type(e))
            print(e.args)
            print(e)
            response = {
                'status' : 500,
                'msg' : 'An error occured'
            }

            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            responseBody = json.dumps(response)

            self.wfile.write(responseBody.encode('utf-8'))