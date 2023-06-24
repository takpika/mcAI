from http.server import BaseHTTPRequestHandler
import json, os, urllib.parse, hashlib
import math, random
from logging import getLogger, DEBUG, StreamHandler, Formatter

class CentralHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parse_data = urllib.parse.urlparse(self.path)
        path = parse_data.path
        query = urllib.parse.parse_qs(parse_data.query)
        status_code = 400
        ip_addr = self.client_address[0]
        if path == "/config":
            if "type" in query:
                pc_type = query["type"][0].lower()
                if pc_type == "client":
                    if self.server.parent.learn_server != None and self.server.parent.mc_server != None:
                        status_code = 200
                        response = {
                            "status": "ok",
                            "config": {
                                "mc_server": self.server.parent.mc_server["ip"],
                                "learn_server": self.server.parent.learn_server["ip"],
                                "port": self.server.parent.config["port"],
                                "mc_folder": self.server.parent.config["files"]["mc_folder"],
                                "char_file": self.server.parent.config["files"]["char_file"],
                                "video_file": self.server.parent.config["files"]["video_file"],
                                "work_dir": self.server.parent.config["files"]["work_dir"],
                                "chat_chars_limit": self.server.parent.config["chat_chars_limit"],
                                "frame_record_limit": self.server.parent.config["frame_record_limit"],
                                "version": self.server.parent.config["version"],
                                "resolution": self.server.parent.config["resolution"]
                            }
                        }
                    else:
                        status_code = 500
                        response = {
                            "status": "ng",
                            "msg": "data is not yet"
                        }
                elif pc_type == "learn":
                    status_code = 200
                    response = {
                        "status": "ok",
                        "config": {
                            "port": self.server.parent.config["port"],
                            "save_folder": self.server.parent.config["files"]["save_folder"],
                            "data_folder": self.server.parent.config["files"]["data_folder"],
                            "video_folder": self.server.parent.config["files"]["video_folder"],
                            "char_file": self.server.parent.config["files"]["char_file"],
                            "version": self.server.parent.config["version"],
                            "resolution": self.server.parent.config["resolution"],
                            "epochs": self.server.parent.config["epochs"]
                        }
                    }
                elif pc_type == "server":
                    status_code = 200
                    response = {
                        "status": "ok",
                        "config": {
                            "port": self.server.parent.config["port"]
                        }
                    }
                else:
                    status_code = 400
                    response = {
                        "status": "ng",
                        "msg": "unknown type"
                    }
            else:
                status_code = 400
                response = {
                    "status": "ng",
                    "msg": "type is required"
                }
        elif path == "/chat":
            hostname = query["hostname"][0].replace("\n","")
            players = self.server.parent.get_players()
            if hostname in players:
                player_pos = players[hostname]["pos"]
                player_dir = players[hostname]["dir"]
                dis_ok = []
                for p in players:
                    if p != hostname:
                        dis_x = players[p]["pos"]["x"] - player_pos["x"]
                        dis_y = players[p]["pos"]["y"] - player_pos["y"]
                        dis_z = players[p]["pos"]["z"] - player_pos["z"]
                        dis = (dis_x ** 2 + dis_y ** 2 + dis_z ** 2) ** 0.5
                        if dis <= self.server.parent.config["threshold"]["distance"]:
                            dis_ok.append(p)
                talkable = []
                dir_dis = []
                for p in dis_ok:
                    dis_x = players[p]["pos"]["x"] - player_pos["x"]
                    dis_z = players[p]["pos"]["z"] - player_pos["z"]
                    y_degree = 0
                    if dis_x == 0:
                        if dis_z >= 0:
                            y_degree = 0
                        else:
                            y_degree = 180
                    elif dis_z == 0:
                        if dis_x >= 0:
                            y_degree = 270
                        else:
                            y_degree = 90
                    else:
                        tmp_x = dis_x
                        if tmp_x < 0:
                            tmp_x = -tmp_x
                        tmp_z = dis_z
                        if tmp_z < 0:
                            tmp_z = -tmp_z
                        degree = math.degrees(math.atan(tmp_x/tmp_z))
                        if tmp_z >= 0 and tmp_x < 0:
                            y_degree = degree + 0
                        elif tmp_z < 0 and tmp_x < 0:
                            y_degree = degree + 90
                        elif tmp_z < 0 and tmp_x >= 0:
                            y_degree = degree + 180
                        elif tmp_z >= 0 and tmp_x >= 0:
                            y_degree = degree + 270
                    dis_xz = (dis_x ** 2 + dis_z ** 2) ** 0.5
                    dis_y = players[p]["pos"]["y"] - player_pos["y"]
                    tmp_y = dis_y
                    if tmp_y < 0:
                        tmp_y = -tmp_y
                    x_degree = 0
                    if dis_xz == 0:
                        if dis_y > 0:
                            x_degree = -90
                        elif dis_y < 0:
                            x_degree = 90
                    elif dis_y == 0:
                        x_degree = 0
                    else:
                        degree = math.degrees(math.atan(dis_xz / dis_y))
                        if dis_y < 0:
                            x_degree = degree
                        else:
                            x_degree = -degree
                    x_dir_dis = player_dir["x"] - x_degree
                    if x_dir_dis < 0:
                        x_dir_dis = -x_dir_dis
                    y_dir_dis = player_dir["y"] - y_degree
                    if y_dir_dis < 0:
                        y_dir_dis = -y_dir_dis
                    if y_dir_dis > 180:
                        y_dir_dis = 360 - y_dir_dis
                    if x_dir_dis <= self.server.parent.config["threshold"]["direction"] and y_dir_dis <= self.server.parent.config["threshold"]["direction"]:
                        talkable.append(p)
                        dir_dis.append((x_dir_dis ** 2 + y_dir_dis ** 2) ** 0.5)
                if len(talkable) == 0:
                    status_code = 404
                    response = {
                        'status': 'ng',
                        'msg': 'not found'
                    }
                else:
                    for i in range(len(talkable)):
                        if dir_dis[i] == min(dir_dis):
                            status_code = 200
                            response = {
                                'status': 'ok',
                                'info': {
                                    'name': talkable[i]
                                }
                            }
                            break
            else:
                status_code = 400
                response = {
                    'status': 'ng',
                    'msg': 'unknown name. please register'
                }
        elif path == "/name":
            if "hostname" in query:
                hostname = query["hostname"][0].replace("\n","")
                if hostname in self.server.parent.clients:
                    client_data = self.server.parent.clients[hostname]
                    players = self.server.parent.get_players()
                    p_names = [players[p]["name"] for p in players]
                    while True:
                        if len(self.server.parent.names) < 1:
                            with open(self.server.parent.config["files"]["name_file"].replace("__WORKDIR__", os.getcwd()), "r") as f:
                                self.server.parent.names = f.read().splitlines()
                        name = random.sample(self.server.parent.names, 1)[0]
                        if not name in p_names:
                            break
                    if not hostname in self.server.parent.clients:
                        self.server.parent.clients[hostname] = client_data
                    self.server.parent.clients[hostname]["name"] = name
                    status_code = 200
                    response = {
                        'status': 'ok',
                        'info': {
                            'name': name
                        }
                    }
                else:
                    status_code = 400
                    response = {
                        'status': 'ng',
                        'msg': 'plz register first'
                    }
            else:
                status_code = 400
                response = {
                    'status': 'ng',
                    'msg': 'missing parm hostname'
                }
        elif path == "/hostname":
            if "hostname" in query:
                hostname = query["hostname"][0].replace("\n", "")
                if hostname in self.server.parent.clients:
                    status_code = 200
                    response = {
                        'status': 'ok',
                        'info': {
                            'name': self.server.parent.clients[hostname]["name"]
                        }
                    }
                else:
                    status_code = 404
                    response = {
                        'status': 'ng',
                        'msg': 'not found'
                    }
            else:
                status_code = 400
                response = {
                    'status': 'ng',
                    'msg': 'missing parm hostname'
                }
        elif path == "/id":
            seed = str(random.random())
            status_code = 200
            response = {
                'status': 'ok',
                'info': {
                    'id': hashlib.md5(seed.encode()).hexdigest()
                }
            }
        elif path == "/check":
            if "type" in query:
                status_code = 404
                response = {
                    'status': 'ok',
                    'info': {
                        'result': False
                    }
                }
                if query['type'][0] == 'client' and "hostname" in query:
                    for c in self.server.parent.clients:
                        if self.server.parent.clients[c]['ip'] == ip_addr and c == query["hostname"][0]:
                            status_code = 200
                            response['info']['result'] = True
                elif query['type'][0] == 'learn':
                    if self.server.parent.learn_server != None:
                        if self.server.parent.learn_server["ip"] == ip_addr:
                            status_code = 200
                            response['info']['result'] = True
                elif query['type'][0] == 'server':
                    if self.server.parent.mc_server != None:
                        if self.server.parent.mc_server['ip'] == ip_addr:
                            status_code = 200
                            response['info']['result'] = True
                else:
                    status_code = 400
                    response = {
                        'status': 'ng',
                        'msg': 'unknown type'
                    }
            else:
                status_code = 400
                response = {
                    'status': 'ng',
                    'msg': 'some query missing'
                }
        elif path == "/hello":
            status_code = 200
            response = {
                'status': 'ok',
                'info': {
                    'type': 'central'
                }
            }
        else:
            status_code = 400
            response = {
                'status': 'ng',
                'msg': 'unknown'
            }
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        responseBody = json.dumps(response)
        self.wfile.write(responseBody.encode("utf-8"))

    def do_POST(self):
        try:
            content_len=int(self.headers.get('content-length'))
            requestBody = json.loads(self.rfile.read(content_len).decode('utf-8'))
            status_code = 400
            if not "type" in requestBody:
                response = {
                    'status': 'ng',
                    'msg': 'type required'
                }
            else:
                type = requestBody["type"]
                if type == "register":
                    status_code = 200
                    ip_addr = self.client_address[0]
                    response = {
                        "status": "ok"
                    }
                    data = requestBody["info"]
                    pc_type = data["type"]
                    if pc_type == "client":
                        if not "hostname" in data:
                            status_code = 400
                            response = {
                                "status": "ng",
                                "msg": "missing parm hostname"
                            }
                        else:
                            self.server.parent.clients[data["hostname"]] = {
                                "ip": ip_addr,
                                "name": ""
                            }
                    elif pc_type == "learn":
                        self.server.parent.learn_server = {
                            "ip": ip_addr
                        }
                    elif pc_type == "server":
                        self.server.parent.mc_server = {
                            "ip": ip_addr
                        }
                    else:
                        response = {
                            "status": "ng",
                            "msg": "unknown pc type"
                        }
                else:
                    status_code = 400
                    response = {
                        "status": "ng",
                        "msg": "unknown type"
                    }
        except Exception as e:
            self.server.parent.logger.error("An error occured")
            self.server.parent.logger.error("The information of error is as following")
            self.server.parent.logger.error(type(e))
            self.server.parent.logger.error(e.args)
            self.server.parent.logger.error(e)
            status_code = 500
            response = {
                'status' : 500,
                'msg' : 'An error occured'
            }
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        responseBody = json.dumps(response)
        self.wfile.write(responseBody.encode("utf-8"))

    