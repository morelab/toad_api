import asyncio
from typing import Dict, List, Any, Callable, Coroutine, Optional

from gmqtt import Client as MQTTClient

from toad_api import logger

MQTTTopic = str
MQTTPayload = bytes
MQTTProperties = Dict
MessageHandler = Callable[
    [MQTTTopic, MQTTPayload, MQTTProperties], Coroutine[Any, Any, None]
]


class MQTT(MQTTClient):
    """
    MQTT client class, which sends and receives MQTT messages.

    :ivar message_handler: async function that handles MQTT messages
    :ivar running: boolean that represents if the server is running.
    """

    message_handler: MessageHandler
    running: bool

    def __init__(self, client_id):
        """
        Initializes the MQTT client.

        :param client_id: MQTT client id
        """
        MQTTClient.__init__(self, client_id)
        self.message_handler = ...
        self.running = False
        self._STARTED = asyncio.Event()
        self._STOP = asyncio.Event()

    def on_connect(self, client, flags, rc, properties):
        logger.log_info_verbose("CONNECTED")

    def on_message(self, client, topic, payload, qos, properties):
        asyncio.create_task(self.message_handler(topic, payload, properties))
        logger.log_info_verbose("RECV MSG:" + payload.decode())

    def on_disconnect(self, client, packet, exc=None):
        logger.log_info_verbose("DISCONNECTED")

    def on_subscribe(self, client, mid, qos, properties):
        logger.log_info_verbose("SUBSCRIBED")

    async def run(
        self,
        broker_host: str,
        message_handler: MessageHandler,
        topics: List[MQTTTopic],
        token: str = None,
    ):
        """
        Runs the MQTT client.

        :param broker_host: MQTT broker IP
        :param message_handler: async function for handliung incoming messages.
        :param topics: topics to which subscribe
        :param token: optional token credential for MQTT security
        :return:
        """
        if self.running:
            raise RuntimeError("MQTT already running")
        self.message_handler = message_handler  # type: ignore
        asyncio.create_task(self._run_loop(broker_host, token, topics))
        await self._STARTED.wait()
        self.running = True

    async def stop(self):
        """
        Stops MQTT client.

        :return:
        """
        if self.running:
            self._STOP.set()
            self._STARTED = asyncio.Event()
            self._STOP = asyncio.Event()
            self.running = False

    async def _run_loop(
        self, broker_host: str, token: Optional[str], topics: List[MQTTTopic]
    ):
        if token:
            self.set_auth_credentials(token, None)
        await self.connect(broker_host)
        for topic in topics:
            self.subscribe(topic)
        self._STARTED.set()
        await self._STOP.wait()
        await self.disconnect()
