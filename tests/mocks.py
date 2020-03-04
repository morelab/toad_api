import asyncio
from gmqtt import Client as MQTTClient
from abc import ABC, abstractmethod

mqtt_client = MQTTClient("mock-mqtt-client")


class MQTTMock(ABC):
    @abstractmethod
    def get_subscribe_topics(self):
        pass

    @abstractmethod
    async def handle_message(self, topic, payload):
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
        asyncio.create_task(self.mock.handle_message(topic, payload))

    def on_disconnect(self, packet, exc=None):
        print("Disconnected")

    def on_subscribe(self, mid, qos, properties):
        print("SUBSCRIBED")

    async def run_loop(self, broker_host, token):
        self.set_auth_credentials(token, None)
        await self.connect(broker_host)

        await self.STOP.wait()
        await self.disconnect()
