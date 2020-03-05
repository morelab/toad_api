import asyncio

from tests.mocks import MQTTMockClient, InfluxMQTTMock, SPMQTTMock
from toad_api.http_server import app

MQTT_BROKER = "127.0.0.1"

influx_mock = None
influx_mock_task = None
sp_mock = None
sp_mock_task = None

sp_requests = {
    "iotoad.org/api/in/mock/sp_command/sp_m1",
    "iotoad.org/api/in/mock/sp_command/sp_g0",
    "iotoad.org/api/in/mock/sp_command/row/1",
    "iotoad.org/api/in/mock/sp_command/column/2",
}

influx_requests = [
    "/api/out/mock/influx_query/sp/power?type=w",
    "/api/out/mock/influx_query/sp/power?operation=sum&type=w",
    "/api/out/mock/influx_query/sp/power?operation=median&type=w&row=1",
    "/api/out/mock/influx_query/sp/status?operation=median&type=g",
]


async def start_mocks(loop: asyncio.AbstractEventLoop):
    global influx_mock, sp_mock, influx_mock_task, sp_mock_task

    influx_mock = MQTTMockClient(InfluxMQTTMock())
    sp_mock = MQTTMockClient(SPMQTTMock())

    influx_mock_task = loop.create_task(influx_mock.run_loop(MQTT_BROKER))
    sp_mock_task = loop.create_task(sp_mock.run_loop(MQTT_BROKER))


async def stop_mocks():
    global influx_mock, sp_mock, influx_mock_task, sp_mock_task

    influx_mock.stop_loop()
    sp_mock.stop_loop()
    await influx_mock_task
    await sp_mock_task

    influx_mock = None
    sp_mock = None
    influx_mock_task = None
    sp_mock_task = None


async def test_requests(aiohttp_client, loop):
    await start_mocks(loop)

    client = await aiohttp_client(app)
    for request in sp_requests:
        resp = await client.get(request)
        assert resp.status == 200
        response = await resp.json()
        assert response == SPMQTTMock.get_generic_response()
    for request, expected_response in influx_requests:
        resp = await client.get(request)
        assert resp.status == 200
        response = await resp.json()
        assert response == InfluxMQTTMock.get_generic_response()

    await stop_mocks()
