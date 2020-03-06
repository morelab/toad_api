from typing import Dict, Any
from aiohttp import web
from toad_api.parser import parse_data
from toad_api.protocol import SUBTOPICS_FIELD, PAYLOAD_FIELD, RESPONSES_BASE_TOPIC
from toad_api.config import MQTT_RESPONSE_TIMEOUT
from toad_api.mqtt import MQTT
import asyncio


class APIServer:
    events: Dict[str, asyncio.Event]
    events_results: Dict[str, Any]
    mqtt_client: MQTT
    app: web.Application

    def __init__(self):
        self.events = {}
        self.events_results = {}
        self.mqtt_client = MQTT()
        self.app = web.Application()
        self.app.add_routes(
            [
                web.post("/api/in", self.in_requests),
                web.get("/api/out/{mqtt_base_topic}", self.out_requests),
            ]
        )

    async def start(self, mqtt_broker="0.0.0.0", mqtt_token=None):
        await self.mqtt_client.run(mqtt_broker, mqtt_token)

    async def in_requests(self, request: web.Request):
        # parse the data
        data = await request.post()
        if isinstance(data, bytes):
            data = data.decode()
        data_json = parse_data(data)
        # parse topic and publish to mqtt
        topic_base = request.match_info[
            "mqtt_base_topic"
        ]  # retrieved from url variable path
        topic_response_id = {}
        for subtopic in data_json[SUBTOPICS_FIELD]:
            topic = topic_base + "/" + subtopic
            payload = data_json[PAYLOAD_FIELD]
            response_id = ""  # generate
            response_topic = RESPONSES_BASE_TOPIC + "/" + response_id
            topic_response_id[topic] = response_id
            self.events[response_id] = asyncio.Event()
            self.mqtt_client.publish(topic, payload, response_topic=response_topic)
        # wait for mqtt response (with timeout)
        await asyncio.wait_for(
            await asyncio.gather(
                [
                    self.events[event_id].wait()
                    for event_id in topic_response_id.values()
                ]),
            MQTT_RESPONSE_TIMEOUT,
        )
        # return response
        response_json = {}
        for topic, response_id in topic_response_id:
            if not self.events[response_id].is_set():
                continue
            response = self.events_results[response_id]
            response_json[topic] = response
        web.Response()
        pass  # todo

    async def out_requests(self, request: web.Request):
        # extract mqtt topic
        # extract mqtt payload
        # publish to mqtt
        # wait for mqtt response (with timeout)
        # return response
        pass  # todo
