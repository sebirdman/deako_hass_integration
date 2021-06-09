from threading import Timer
import socket
import select
import threading
import json
import asyncio
import logging
from threading import Thread

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

_LOGGER: logging.Logger = logging.getLogger(__package__)

class ConnectionThread(Thread):

    def set_callbacks(self, on_data_callback):
        #self.connect_callback = connect_callback
        self.on_data_callback = on_data_callback
        #self.error_callback = error_callback

    def connect(self, ip, port):
        self.ip = ip
        self.port = port

    async def send_data(self, data_to_send):
        if self.socket is None:
            return

        try:
            await self.loop.sock_sendall(self.socket, str.encode(data_to_send))
        except:
            self.has_send_error = True

    async def read_socket(self):
        data = await self.loop.sock_recv(self.socket, 1024)

        raw_string = data.decode("utf-8")
        list_of_items = raw_string.split("\r\n")
        for item in list_of_items:
            self.leftovers = self.leftovers + item
            if len(self.leftovers) == 0:
                return
            try:
                self.on_data_callback(json.loads(self.leftovers))
                self.leftovers = ""
            except json.decoder.JSONDecodeError:
                _LOGGER.error("Got partial message")

    async def connect_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #this.s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        #this.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
        #this.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 3)
        #this.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
        #this.s.settimeout(2)
        await self.loop.sock_connect(self.socket, (self.ip, self.port))

    async def close_socket(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None
        self.has_send_error = False

    def run(self):
        self.leftovers = ""
        self.socket = None
        self.state = 0
        self.has_send_error = False
        self.loop = asyncio.new_event_loop()
        self.loop.run_until_complete(self._run())
        self.loop.close()

    async def wait_for_connect(self):
        while self.state != 1:
            await asyncio.sleep(1)

    async def _run(self):
        while True:
            if self.state == 0:
                try:
                    await self.connect_socket()
                    self.state = 1
                except:
                    _LOGGER.error("Failed to connect")
                    self.state = 2
                    continue
            elif self.state == 1:
                try:
                    await self.read_socket()
                except:
                    self.state = 2
                    continue
            elif self.state == 2:
                try:
                    await self.close_socket()
                    self.state = 0
                    await asyncio.sleep(5)
                except:
                    self.state = 2
                    continue
            else:
                _LOGGER.error("Unknown state")

            if self.has_send_error:
                _LOGGER.error("Failed to send")
                self.state = 2


class Deako:

    def __init__(self, ip, what):
        self.ip = ip
        self.src = what
        self.connection = ConnectionThread()
        self.connection.set_callbacks(self.incoming_json)

        self.devices = {}
        self.expected_devices = 0

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

    def incoming_json(self, in_data):
        try:
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
        except:
            _LOGGER.error("Failed to parse %s", in_data)

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

    async def connect(self):
        self.connection.connect(self.ip, 23)
        self.connection.start()
        await self.connection.wait_for_connect()

    def get_devices(self):
        return self.devices

    async def find_devices(self, timeout = 10):
        device_list_dict["src"] = self.src
        await self.connection.send_data(json.dumps(device_list_dict))
        remaining = timeout
        while(self.expected_devices == 0 or len(self.devices) != self.expected_devices and remaining > 0):
            await asyncio.sleep(1)
            remaining -= 1

    async def send_device_control(self, uuid, power, dim=None):
        state_change = {
            "target": uuid,
            "state": {
                "power": power,
                "dim": dim
            }
        }
        state_change_dict["data"] = state_change
        state_change_dict["src"] = self.src
        await self.connection.send_data(json.dumps(state_change_dict))
        self.devices[uuid]["state"]["power"] = power
        self.devices[uuid]["state"]["dim"] = dim

    def get_name_for_device(self, uuid):
        return self.devices[uuid]["name"]

    def get_state_for_device(self, uuid):
        return self.devices[uuid]["state"]
