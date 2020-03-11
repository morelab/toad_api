import asyncio

import pytest

from tests.mocks import MQTTMockClient, InfluxMQTTMock, SPMQTTMock
from toad_api import config
from toad_api import protocol
from toad_api.http_server import APIServer

in_request_json = {
    protocol.REST_PAYLOAD_FIELD: "data",
    protocol.REST_SUBTOPICS_FIELD: ["topic1", "topic2"],
}

sp_requests = [
    ("/api/in/mock/sp_command/sp_m1", in_request_json),
    ("/api/in/mock/sp_command/sp_g0", in_request_json),
    ("/api/in/mock/sp_command/row/1", in_request_json),
    ("/api/in/mock/sp_command/column/2", in_request_json),
]

influx_requests = [
    "/api/out/mock/influx_query/sp/power?type=w",
    "/api/out/mock/influx_query/sp/power?operation=sum&type=w",
    "/api/out/mock/influx_query/sp/power?operation=median&type=w&row=1",
    "/api/out/mock/influx_query/sp/status?operation=median&type=g",
]


@pytest.fixture
def api_server_fixture(loop: asyncio.AbstractEventLoop, aiohttp_client):
    sp_mock = SPMQTTMock()
    influx_mock = InfluxMQTTMock()
    mqtt_influx_mock = MQTTMockClient(InfluxMQTTMock())
    mqtt_sp_mock = MQTTMockClient(SPMQTTMock())
    api_server = APIServer()

    client = loop.run_until_complete(aiohttp_client(api_server.app))
    influx_mock_task = loop.create_task(
        mqtt_influx_mock.run_loop(config.MQTT_BROKER_IP)
    )
    sp_mock_task = loop.create_task(mqtt_sp_mock.run_loop(config.MQTT_BROKER_IP))
    loop.run_until_complete(api_server.start())

    yield client, influx_mock, sp_mock

    mqtt_influx_mock.stop_loop()
    mqtt_sp_mock.stop_loop()
    loop.run_until_complete(influx_mock_task)
    loop.run_until_complete(sp_mock_task)
    loop.run_until_complete(api_server.stop())


@pytest.mark.asyncio
async def test_start_stop_server():
    api_server = APIServer()
    await api_server.start()

    await asyncio.sleep(1)

    await api_server.stop()


async def test_requests(api_server_fixture):
    client, influx_mock, sp_mock = api_server_fixture
    for url in influx_requests:
        resp = await client.get(url)
        assert resp.status == 200
        response = await resp.json()
        assert response == influx_mock.get_generic_response()
    for url, data in sp_requests:
        resp = await client.post(url, json=data)
        assert resp.status == 200
        subtopic_responses = await resp.json()
        data_subtopics = set(data[protocol.REST_SUBTOPICS_FIELD])
        for subtopic, response in subtopic_responses.items():
            assert subtopic in data_subtopics
            assert response == sp_mock.get_generic_response()
    # todo: invalid requests
