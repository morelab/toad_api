import asyncio
import json
import uuid
from typing import Dict

from aiohttp import web

from toad_api import config
from toad_api import logger
from toad_api.mqtt import MQTT, MQTTTopic, MQTTProperties
from toad_api.protocol import PAYLOAD_FIELD, SUBTOPICS_FIELD
from toad_api.protocol import RESPONSES_BASE_TOPIC


class APIServer:
    """
    Runs the server and handles the requests.

    :ivar events: events that are being waited. Mostly is used for MQTT responses.
    :ivar events_results: dict where events results are stored.
    :ivar mqtt_client: ~`toad_api.mqtt.MQTT` mqtt client.
    :ivar app: aiohttp ~`aiohttp.web.Application` of the running server.
    :ivar ip: IP address where the server will be running.
    :ivar port: port number where the server will be running.
    :ivar running: boolean that represents if the server is running.
    """

    events: Dict[str, asyncio.Event]
    events_results: Dict[str, bytes]
    mqtt_client: MQTT
    app: web.Application
    ip: str
    port: int
    running: bool

    def __init__(self):
        self.events = {}
        self.events_results = {}
        self.mqtt_client = MQTT(self.__class__.__name__)
        self.app = web.Application()
        self.app.add_routes(
            [
                web.post("/api/in/{mqtt_base_topic}", self.in_requests),
                web.get("/api/out/{mqtt_base_topic}", self.out_requests),
            ]
        )
        self.running = False

    async def start(
        self,
        ip: str = config.SERVER_IP,
        port: int = config.SERVER_PORT,
        mqtt_broker=config.MQTT_BROKER_IP,
        mqtt_token=None,
    ):
        """
        Runs the server.

        :param mqtt_broker: MQTT broker IP.
        :param mqtt_token: MQTT credential token.
        :return:
        """
        if self.running:
            raise RuntimeError("Server already running")
        self.ip = ip
        self.port = port
        await self.mqtt_client.run(
            mqtt_broker,
            self._mqtt_response_handler,
            [RESPONSES_BASE_TOPIC + "/#"],
            mqtt_token,
        )
        # todo: start aiohttp app?
        self.running = True

    async def stop(self):
        """
        Stops the server.

        :return:
        """
        if self.running:
            await self.mqtt_client.stop()
            # todo: stop aiothpp app?
            self.running = False

    async def in_requests(self, request: web.Request):
        """
        Handles POST /api/in requests.

        :param request: ~`aiohttp.web.Request` instance
        :return:
        """
        # parse the data
        data_json = await request.json()
        try:
            check_request_body(data_json)
        except ValueError:
            return web.HTTPInternalServerError(
                reason="Invalid request body"
            )  # todo: log that no all events were received?
        # parse topic and publish to mqtt
        topic_base = request.match_info[
            "mqtt_base_topic"
        ]  # retrieved from url variable path
        topic_response_id = {}
        for subtopic in data_json[SUBTOPICS_FIELD]:
            topic = topic_base + "/" + subtopic
            payload = data_json[PAYLOAD_FIELD]
            response_id = uuid.uuid4().hex  # generate random ID
            response_topic = RESPONSES_BASE_TOPIC + "/" + response_id
            topic_response_id[topic] = response_id
            self.events[response_id] = asyncio.Event()
            self.mqtt_client.publish(topic, payload, response_topic=response_topic)
        # wait for mqtt response (with timeout)
        try:
            await asyncio.wait_for(
                await asyncio.gather(  # type: ignore
                    [
                        self.events[event_id].wait()
                        for event_id in topic_response_id.values()
                    ]
                ),
                config.MQTT_RESPONSE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.log_error_verbose(
                f"Some events were not received from "
                f"the following requests: {topic_response_id.keys()}"
            )
        # return response
        response_json: Dict = {}
        for topic, response_id in topic_response_id:
            if not self.events[response_id].is_set():
                response_json[topic] = None
                continue
            response = json.loads(self.events_results[response_id].decode())
            response_json[topic] = response
        return web.Response(text=json.dumps(response_json))

    async def out_requests(self, request: web.Request):
        """
        Handles GET /api/out requests.

        :param request: ~`aiohttp.web.Request` instance
        :return:
        """
        # extract mqtt topic
        topic = request.match_info["mqtt_base_topic"]
        # build mqtt payload and response topic
        payload = request.query
        response_id = uuid.uuid4().hex  # generate random ID
        response_topic = RESPONSES_BASE_TOPIC + "/" + response_id
        # publish to mqtt
        self.events[response_id] = asyncio.Event()
        self.mqtt_client.publish(topic, payload, response_topic=response_topic)
        # wait for mqtt response (with timeout)
        try:
            await asyncio.wait_for(
                self.events[response_id].wait(), config.MQTT_RESPONSE_TIMEOUT
            )
        except asyncio.TimeoutError:
            return web.HTTPInternalServerError(
                reason="No hook responded the request"
            )  # todo: log that no all events were received?
        response = json.loads(self.events_results[response_id].decode())
        return web.Response(text=json.dumps(response))

    async def _mqtt_response_handler(
        self, topic: MQTTTopic, payload: bytes, properties: MQTTProperties
    ):
        """
        Handles MQTT messages; it stores the message payload in.

        ~`APIServer.events_results`, and it sets the Event in
        ~`APIServer.events`

        :param topic: MQTT topic the message was received in.
        :param payload: MQTT message payload
        :param properties: MQTT message properties
        :return:
        """
        # extract response_id
        response_id = topic.replace(RESPONSES_BASE_TOPIC, "")
        response_id = response_id.replace("/", "")
        # store event result
        self.events_results[response_id] = payload
        # set event
        self.events[response_id].set()


def check_request_body(data_json: Dict):
    """
    Parses POST /api/in requests body.

    :param data_json: JSON dictionary containin
    :return: JSON dictionary
    """
    if 2 < len(data_json):
        raise ValueError("Invalid data JSON")
    if PAYLOAD_FIELD not in data_json:
        raise ValueError("Invalid data JSON")
    if len(data_json) == 2 and SUBTOPICS_FIELD not in data_json:
        raise ValueError("Invalid data JSON")
