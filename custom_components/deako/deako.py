import telnetlib
import socket
import select
import string
import sys
import threading
import json
import logging

_LOGGER: logging.Logger = logging.getLogger(__package__)

x = {
    "transactionId": "015c44d3-abec-4be0-bb0d-34adb4b81559",
    "type": "DEVICE_LIST",
    "dst": "deako",
    "src": "ACME Corp"
}

state_change_dict = {
    "transactionId": "015c44d3-abec-4be0-bb0d-34adb4b81559",
    "type": "CONTROL",
    "dst": "deako",
    "src": "ACME Corp",
}


class Deako:
    def __init__(self, ip, what, device_state_callback, callback, callback_param):
        self.device_state_callback = device_state_callback
        self.device_list_callback = callback
        self.ip = ip
        self.src = what
        self.callback_param = callback_param
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(2)

    def incoming_json(self, in_data):
        if in_data["type"] == "DEVICE_LIST":
            print("Got device list")
        elif in_data["type"] == "DEVICE_FOUND":
            subdata = in_data["data"]
            state = subdata["state"]
            if "dim" in state:
                self.device_list_callback(
                    self, subdata["name"], subdata["uuid"], state["power"], state["dim"], self.callback_param)
            else:
                self.device_list_callback(
                    self, subdata["name"], subdata["uuid"], state["power"], None, self.callback_param)
        elif in_data["type"] == "EVENT":
            subdata = in_data["data"]
            state = subdata["state"]
            if "dim" in state:
                self.device_state_callback(
                    subdata["target"], state["power"], state["dim"])
            else:
                self.device_state_callback(subdata["target"], state["power"])
        else:
            print(json.dumps(in_data))

    def read_func(self, s):
        leftovers = ""

        while 1:
            socket_list = [sys.stdin, s]

            # Get the list sockets which are readable
            read_sockets, write_sockets, error_sockets = select.select(
                socket_list, [], [])

            for sock in read_sockets:
                # incoming message from remote server
                if sock == s:
                    try:
                        data = sock.recv(1024)
                        if not data:
                            print('Connection closed')
                            sys.exit()
                        else:
                            raw_string = data.decode("utf-8")
                            list_of_items = raw_string.split("\r\n")
                            for item in list_of_items:
                                if len(item) == 0:
                                    continue
                                try:
                                    self.incoming_json(
                                        json.loads(item))
                                    continue
                                except json.decoder.JSONDecodeError:
                                    leftovers = leftovers + item

                                if len(leftovers) != 0:
                                    try:
                                        self.incoming_json(
                                            json.loads(leftovers))
                                        leftovers = ""
                                    except json.decoder.JSONDecodeError:
                                        self.errors = 0
                    except ConnectionResetError:
                        self.connect()
                        return

    def connect(self):

        # connect to remote host
        try:
            self.s.connect((self.ip, 23))
        except:
            print('Unable to connect')
            sys.exit()

        print('Connected to remote host')

        x = threading.Thread(target=self.read_func, args=(self.s,))
        x.start()

    def send_data(self, data_to_send):
        self.s.send(str.encode(data_to_send))

    def find_devices(self):
        x["src"] = self.src
        print("Sending device List Request")
        self.send_data(json.dumps(x))

    def send_device_control(self, uuid, power, dim=None):
        state_change = {
            "target": uuid,
            "state": {
                "power": power,
                "dim": dim
            }
        }
        state_change_dict["data"] = state_change
        state_change_dict["src"] = self.src
        self.send_data(json.dumps(state_change_dict))
