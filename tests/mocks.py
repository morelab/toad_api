import asyncio
from gmqtt import Client as MQTTClient
from abc import ABC, abstractmethod
from toad_api.protocol import PAYLOAD_ERROR_FIELD, PAYLOAD_DATA_FIELD


class MQTTMock(ABC):
    @staticmethod
    @abstractmethod
    def get_subscribe_topics():
        pass

    @staticmethod
    @abstractmethod
    def get_generic_response(error=False):
        pass

    @staticmethod
    @abstractmethod
    async def handle_message(topic, payload, properties, mqtt_client):
        pass


class MQTTMockClient(MQTTClient):
    def __init__(self, mock: MQTTMock):
        self.mock = mock
        self.STOP = asyncio.Event()

    def on_connect(self, flags, rc, properties):
        for topic in self.mock.get_subscribe_topics():
            self.subscribe(topic, qos=0)

    def on_message(self, topic, payload, qos, properties):
        print("RECV MSG:", payload)
        asyncio.create_task(self.mock.handle_message(topic, payload,properties, self))

    def on_disconnect(self, packet, exc=None):
        print("Disconnected")

    def on_subscribe(self, mid, qos, properties):
        print("SUBSCRIBED")

    async def run_loop(self, broker_host, token=None):
        if token:
            self.set_auth_credentials(token, None)
        await self.connect(broker_host)

        await self.STOP.wait()
        await self.disconnect()

    def stop_loop(self):
        self.STOP.set()


class SPMQTTMock(MQTTMock):
    @staticmethod
    def get_subscribe_topics():
        return ["command/mock/sp_command/#"]

    @staticmethod
    def get_generic_response(error=False):
        return {PAYLOAD_ERROR_FIELD: "Error" if error else None}

    @staticmethod
    async def handle_message(topic, payload, properties, mqtt_client: MQTTClient):
        response_topic = properties["response_topic"]
        mqtt_client.publish(response_topic, SPMQTTMock.get_generic_response())


class InfluxMQTTMock(MQTTMock):
    @staticmethod
    def get_subscribe_topics():
        return ["query/mock/influx_query/#"]

    @staticmethod
    def get_generic_response(error=False):
        if error:
            return {PAYLOAD_ERROR_FIELD: "Error"}
        return {
            PAYLOAD_ERROR_FIELD: None,
            PAYLOAD_DATA_FIELD: {
                "e": [
                    {
                        "v": 0.0,
                        "t": 12345678
                    }
                ],
                "bn": "sp_mock",
                "bu": "MOCK"
            }
        }

    @staticmethod
    async def handle_message(topic, payload,properties, mqtt_client: MQTTClient):
        response_topic = properties["response_topic"]
        mqtt_client.publish(response_topic, InfluxMQTTMock.get_generic_response())

