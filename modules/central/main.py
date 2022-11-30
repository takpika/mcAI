from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import json, requests, argparse, os, urllib.parse, hashlib
import math, random
from logging import getLogger, DEBUG, StreamHandler, Formatter

logger = getLogger(__name__)
logger.setLevel(DEBUG)
logger_handler = StreamHandler()
logger_formatter = Formatter(fmt='%(asctime)-15s [%(name)s] %(message)s')
logger_handler.setFormatter(logger_formatter)
logger.addHandler(logger_handler)

clients = {}
mc_server = None
learn_server = None

parser = argparse.ArgumentParser(
    prog='main.py',
    description='mcAI Central Agent',
    add_help = True
)
parser.add_argument('configFile', help='Config File (JSON)', type=argparse.FileType('r'))
args = parser.parse_args()

config = json.loads(args.configFile.read())
args.configFile.close()

with open(config["files"]["name_file"].replace("__WORKDIR__", os.getcwd()), "r") as f:
    names = f.read().splitlines()

def get_players():
    global clients
    clientsCopy = clients.copy()
    players = {}
    for client in clientsCopy:
        try:
            data = json.loads(requests.get("http://%s:8000/" % (clientsCopy[client]["ip"])).text)
            if "playing":
                players[data["player"]["name"]] = {
                    "name": clientsCopy[client]["name"],
                    "pos": data["player"]["pos"],
                    "dir": data["player"]["direction"]
                }
                continue
        except:
            pass
        clients.pop(client)
    return players

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global clients
        global mc_server
        global learn_server
        global names
        global config
        parse_data = urllib.parse.urlparse(self.path)
        path = parse_data.path
        query = urllib.parse.parse_qs(parse_data.query)
        status_code = 400
        if path == "/config":
            if "type" in query:
                pc_type = query["type"][0].lower()
                if pc_type == "client":
                    if learn_server != None and mc_server != None:
                        status_code = 200
                        response = {
                            "status": "ok",
                            "config": {
                                "mc_server": mc_server["ip"],
                                "learn_server": learn_server["ip"],
                                "port": config["port"],
                                "mc_folder": config["files"]["mc_folder"],
                                "char_file": config["files"]["char_file"],
                                "video_file": config["files"]["video_file"],
                                "work_dir": config["files"]["work_dir"],
                                "chat_chars_limit": config["chat_chars_limit"],
                                "frame_record_limit": config["frame_record_limit"],
                                "version": config["version"],
                                "resolution": config["resolution"]
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
                            "port": config["port"],
                            "save_folder": config["files"]["save_folder"],
                            "data_folder": config["files"]["data_folder"],
                            "video_folder": config["files"]["video_folder"],
                            "char_file": config["files"]["char_file"],
                            "version": config["version"],
                            "resolution": config["resolution"],
                            "epochs": config["epochs"]
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
            hostname = query["hostname"][0]
            players = get_players()
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
                        if dis <= config["threshold"]["distance"]:
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
                    if x_dir_dis <= config["threshold"]["direction"] and y_dir_dis <= config["threshold"]["direction"]:
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
                if query["hostname"][0] in clients:
                    client_data = clients[query["hostname"][0]]
                    players = get_players()
                    p_names = [players[p]["name"] for p in players]
                    while True:
                        if len(names) < 1:
                            with open(config["files"]["name_file"].replace("__WORKDIR__", os.getcwd()), "r") as f:
                                names = f.read().splitlines()
                        name = random.sample(names, 1)[0]
                        if not name in p_names:
                            break
                    if not query["hostname"][0] in clients:
                        clients[query["hostname"][0]] = client_data
                    clients[query["hostname"][0]]["name"] = name
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
                hostname = query["hostname"][0]
                if hostname in clients:
                    status_code = 200
                    response = {
                        'status': 'ok',
                        'info': {
                            'name': clients[hostname]["name"]
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
            if "type" in query and "ip" in query:
                status_code = 404
                response = {
                    'status': 'ok',
                    'info': {
                        'result': False
                    }
                }
                if query['type'][0] == 'client':
                    for c in clients:
                        if clients[c]['ip'] == query["ip"][0]:
                            status_code = 200
                            response['info']['result'] = True
                elif query['type'][0] == 'learn':
                    if learn_server != None:
                        if learn_server["ip"] == query['ip'][0]:
                            status_code = 200
                            response['info']['result'] = True
                elif query['type'][0] == 'minecraft':
                    if mc_server != None:
                        if mc_server['ip'] == query['ip'][0]:
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
        global clients
        global mc_server
        global learn_server
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
                            clients[data["hostname"]] = {
                                "ip": data["ip"],
                                "name": ""
                            }
                    elif pc_type == "learn":
                        learn_server = {
                            "ip": data["ip"]
                        }
                    elif pc_type == "minecraft":
                        mc_server = {
                            "ip": data["ip"]
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
            logger.error("An error occured")
            logger.error("The information of error is as following")
            logger.error(type(e))
            logger.error(e.args)
            logger.error(e)
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

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

if __name__ == '__main__':
    server = ThreadedHTTPServer(("0.0.0.0", 8000), Handler)
    server.serve_forever()