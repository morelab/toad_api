from gmqtt.mqtt.constants import MQTTv311
import json
import asyncio
from abc import ABC, abstractmethod

from gmqtt import Client as MQTTClient

from toad_api import protocol


class MQTTMock(ABC):
    @abstractmethod
    def get_subscribe_topics(self):
        pass

    @abstractmethod
    def get_generic_response(self, error=False):
        pass

    @abstractmethod
    async def handle_message(self, topic, payload, properties, mqtt_client):
        pass


class MQTTMockClient(MQTTClient):
    def __init__(self, mock: MQTTMock):
        client_id = mock.__class__.__name__
        MQTTClient.__init__(self, client_id)
        self.mock = mock
        self.STOP = asyncio.Event()

    def on_connect(self, client, flags, rc, properties):
        for topic in self.mock.get_subscribe_topics():
            self.subscribe(topic, qos=0)

    def on_message(self, client, topic, payload, qos, properties):
        print("RECV MSG:", payload)
        asyncio.create_task(self.mock.handle_message(topic, payload, properties, self))

    def on_disconnect(self, client, packet, exc=None):
        print("Disconnected")

    def on_subscribe(self, client, mid, qos, properties):
        print("SUBSCRIBED")

    async def run_loop(self, broker_host, token=None):
        if token:
            self.set_auth_credentials(token, None)
        await self.connect(broker_host, version=MQTTv311)

        await self.STOP.wait()
        await self.disconnect()

    def stop_loop(self):
        self.STOP.set()


class SPMQTTMock(MQTTMock):
    def get_subscribe_topics(self):
        return ["command/mock/sp_command/#"]

    def get_generic_response(self, error=False):
        return {protocol.PAYLOAD_ERROR_FIELD: "Error" if error else None}

    async def handle_message(self, topic, payload, properties, mqtt_client: MQTTClient):
        payload = json.loads(payload.decode())
        response_topic = payload[protocol.PAYLOAD_RESPONSE_TOPIC_FIELD]
        mqtt_client.publish(response_topic, self.get_generic_response())


class InfluxMQTTMock(MQTTMock):
    def get_subscribe_topics(self):
        return ["query/mock/influx_query/#"]

    def get_generic_response(self, error=False):
        if error:
            return {protocol.PAYLOAD_ERROR_FIELD: "Error"}
        return {
            protocol.PAYLOAD_ERROR_FIELD: None,
            protocol.PAYLOAD_DATA_FIELD: {
                "e": [{"v": 0.0, "t": 12345678}],
                "bn": "sp_mock",
                "bu": "MOCK",
            },
        }

    async def handle_message(self, topic, payload, properties, mqtt_client: MQTTClient):
        payload = json.loads(payload.decode())
        response_topic = payload[protocol.PAYLOAD_RESPONSE_TOPIC_FIELD]
        mqtt_client.publish(response_topic, self.get_generic_response())
