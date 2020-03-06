import asyncio
from gmqtt import Client as MQTTClient


class MQTT(MQTTClient):
    def __init__(self):
        self.STARTED = asyncio.Event()
        self.STOP = asyncio.Event()

    def on_connect(self, flags, rc, properties):
        pass  # todo

    def on_message(self, topic, payload, qos, properties):
        print("RECV MSG:", payload)
        # todo

    def on_disconnect(self, packet, exc=None):
        print("Disconnected")

    def on_subscribe(self, mid, qos, properties):
        print("SUBSCRIBED")

    async def run(self, broker_host, token=None):
        asyncio.create_task(self._run_loop(broker_host, token))
        await self.STARTED.wait()

    def stop(self):
        self.STOP.set()

    async def _run_loop(self, broker_host, token):
        if token:
            self.set_auth_credentials(token, None)
        await self.connect(broker_host)
        self.STARTED.set()
        await self.STOP.wait()
        await self.disconnect()
