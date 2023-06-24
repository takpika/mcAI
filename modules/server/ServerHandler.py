import json, os, socket, requests, subprocess, sys
from logging import getLogger, DEBUG, StreamHandler, Formatter
from time import sleep
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import threading, urllib.parse
from mcrcon import MCRcon
import random, traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed

class ServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parse_data = urllib.parse.urlparse(self.path)
        path = parse_data.path
        query = urllib.parse.parse_qs(parse_data.query)
        status_code = 404
        response = {
            "status": "ng",
            "msg": "Not Found"
        }
        if path == "/kill":
            if "name" in query:
                self.server.parent.runCommand("kill %s" % query["name"][0])
                status_code = 200
                response["status"] = "ok"
                response["msg"] = "Success"
            else:
                status_code = 400
                response["msg"] = "Bad Request"
        elif path == "/gamemode":
            if "name" in query and "mode" in query:
                self.server.parent.runCommand("gamemode %s %s" % (query["mode"][0], query["name"][0]))
                status_code = 200
                response["status"] = "ok"
                response["msg"] = "Success"
            else:
                status_code = 400
                response["msg"] = "Bad Request"
        elif path == "/effect":
            if "name" in query and "effect" in query and not "clear" in query:
                playerName = query["name"][0]
                effectName = query["effect"][0]
                level = int(query["level"][0]) if "level" in query else 1
                duration = int(query["duration"][0]) if "duration" in query else 999999
                self.server.parent.runCommand("effect give %s %s %d %d true" % (playerName, effectName, duration, level))
                status_code = 200
                response["status"] = "ok"
                response["msg"] = "Success"
            elif "name" in query and "clear" in query:
                playerName = query["name"][0]
                effect = query["effect"][0] if "effect" in query else ""
                self.server.parent.runCommand("effect clear %s %s" % (playerName, effect))
                status_code = 200
                response["status"] = "ok"
                response["msg"] = "Success"
            else:
                status_code = 400
                response["msg"] = "Bad Request"
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))