from threading import Timer
import socket
import select
import threading
import json
import asyncio

device_list_dict = {
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


class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        if self.is_running:
            self._timer.cancel()
            self.is_running = False


class Deako:

    def __init__(self, ip, what):
        self.ip = ip
        self.src = what
        self.s = None

        self.devices = {}
        self.expected_devices = 0
        self.rt = RepeatedTimer(2,  self._internal_connect, self)

    def update_state(self, uuid, power, dim=None):
        if uuid is None:
            return
        if uuid not in self.devices:
            return

        self.devices[uuid]["state"]["power"] = power
        self.devices[uuid]["state"]["dim"] = dim

        if "callback" not in self.devices[uuid]:
            return
        self.devices[uuid]["callback"]()

    def set_state_callback(self, uuid, callback):
        if uuid not in self.devices:
            return
        self.devices[uuid]["callback"] = callback

    def record_device(self, name, uuid, power, dim=None):
        if uuid is None:
            return
        if uuid not in self.devices:
            self.devices[uuid] = {}
            self.devices[uuid]["state"] = {}

        self.devices[uuid]["name"] = name
        self.devices[uuid]["uuid"] = uuid
        self.devices[uuid]["state"]["power"] = power
        self.devices[uuid]["state"]["dim"] = dim

    def incoming_json(self, in_data):
        if in_data["type"] == "DEVICE_LIST":
            subdata = in_data["data"]
            self.expected_devices = subdata["number_of_devices"]
        elif in_data["type"] == "DEVICE_FOUND":
            subdata = in_data["data"]
            state = subdata["state"]
            if "dim" in state:
                self.record_device(
                    subdata["name"], subdata["uuid"], state["power"], state["dim"])
            else:
                self.record_device(
                    subdata["name"], subdata["uuid"], state["power"])
        elif in_data["type"] == "EVENT":
            subdata = in_data["data"]
            state = subdata["state"]
            if "dim" in state:
                self.update_state(subdata["target"],
                                  state["power"], state["dim"])
            else:
                self.update_state(subdata["target"], state["power"])
        else:
            print(json.dumps(in_data))

    def read_func(self, s):
        leftovers = ""

        while 1:
            socket_list = [s]

            # Get the list sockets which are readable
            read_sockets, write_sockets, error_sockets = select.select(
                socket_list, [], [])

            for sock in read_sockets:
                # incoming message from remote server
                if sock == s:
                    try:
                        data = sock.recv(1024)
                        if not data:
                            self.rt.start()
                            return
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
                    except:
                        self.rt.start()
                        return

    def _internal_connect(self, this):
        this.rt.stop()
        try:
            this.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            this.s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            this.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
            this.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 3)
            this.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)

            this.s.settimeout(2)
            this.s.connect((this.ip, 23))
            x = threading.Thread(target=this.read_func, args=(this.s,))
            x.start()
        except:
            this.rt.start()

    def connect(self):
        self._internal_connect(self)

    def send_data(self, data_to_send):
        if self.s is None:
            return

        try:
            self.s.send(str.encode(data_to_send))
        except:
            self.s.close()
            self.rt.start()

    def get_devices(self):
        return self.devices

    async def find_devices(self, timeout = 10):
        device_list_dict["src"] = self.src
        self.send_data(json.dumps(device_list_dict))
        remaining = timeout
        while(self.expected_devices == 0 or len(self.devices) != self.expected_devices and remaining > 0):
            await asyncio.sleep(1)
            remaining -= 1

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

    def get_name_for_device(self, uuid):
        return self.devices[uuid]["name"]

    def get_state_for_device(self, uuid):
        return self.devices[uuid]["state"]
