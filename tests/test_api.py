import asyncio
import pytest
from tests.mocks import MQTTMockClient, InfluxMQTTMock, SPMQTTMock
from toad_api.http_server import  APIServer


MQTT_BROKER = "127.0.0.1"

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


@pytest.mark.asyncio
@pytest.fixture
async def mqtt_mocks(loop: asyncio.AbstractEventLoop):
    influx_mock = MQTTMockClient(InfluxMQTTMock())
    sp_mock = MQTTMockClient(SPMQTTMock())
    api_server = APIServer()

    influx_mock_task = loop.create_task(influx_mock.run_loop(MQTT_BROKER))
    sp_mock_task = loop.create_task(sp_mock.run_loop(MQTT_BROKER))
    api_server_task = await api_server.start()

    yield api_server


    # todo: stop api_server await api_server.
    influx_mock.stop_loop()
    sp_mock.stop_loop()
    await influx_mock_task
    await sp_mock_task


async def test_requests(mqtt_mocks, aiohttp_client, loop):
    app = mqtt_mocks
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

