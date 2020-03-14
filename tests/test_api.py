import asyncio
import json
from typing import Dict

import pytest

from tests.mocks import MQTTMockClient, InfluxMQTTMock, SPMQTTMock
from toad_api import config
from toad_api import protocol
from toad_api.mqtt import MQTT, MQTTProperties, MQTTTopic
from toad_api.server import APIServer


TEST_SUBTOPICS = ["topic1", "topic2"]
TEST_DATA = "data"

body_with_subtopics = {
    protocol.REST_PAYLOAD_FIELD: TEST_DATA,
    protocol.REST_SUBTOPICS_FIELD: TEST_SUBTOPICS,
}

body_without_subtopics = {
    protocol.REST_PAYLOAD_FIELD: TEST_DATA,
}

bad_body = {
    protocol.REST_SUBTOPICS_FIELD: TEST_SUBTOPICS,
}

sp_requests = [
    ("/api/in/mock/sp_command/sp_m1", body_with_subtopics),
    ("/api/in/mock/sp_command/sp_g0", body_without_subtopics),
    ("/api/in/mock/sp_command/row/1", body_with_subtopics),
    ("/api/in/mock/sp_command/column/2", body_without_subtopics),
]

influx_requests = [
    ("/api/out/mock/influx_query/sp/power", {"type": "w"}),
    ("/api/out/mock/influx_query/sp/power", {"operation": "sum", "type": "w"}),
    (
        "/api/out/mock/influx_query/sp/power",
        {"operation": "median", "type": "w", "row": 1},
    ),
    ("/api/out/mock/influx_query/sp/status", {"operation": "median", "type": "g"}),
]

sp_bad_requests = [
    ("/api/error/mock/sp_command/sp_m1", body_with_subtopics, 404),
    ("/api/in/mock/sp_command/sp_g0", bad_body, 500),
    ("/api/in/mock/1", body_with_subtopics, 500),
    ("/api/in/mock/column/2", bad_body, 500),
]

influx_bad_requests = [
    ("/api/out/influx_query/sp/power", {"type": "w"}, 500),
    ("/api/out/mock/power", {"operation": "sum", "type": "w"}, 500),
    ("/api/out/mock/power", {"operation": "median", "type": "w", "row": 1}, 500),
    ("/api/out/sp/status", {"operation": "median", "type": "g"}, 500),
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


@pytest.fixture
def mqtt_client_fixture(loop: asyncio.AbstractEventLoop):
    mqtt_client = MQTT("mqtt-test-client")

    yield mqtt_client

    if mqtt_client.running:
        loop.run_until_complete(mqtt_client.stop())


@pytest.mark.asyncio
async def test_start_stop_server():
    api_server = APIServer()
    await api_server.start()

    await asyncio.sleep(1)

    await api_server.stop()


async def test_requests(api_server_fixture):
    client, influx_mock, sp_mock = api_server_fixture
    for url, params in influx_requests:
        resp = await client.get(url, params=params)
        assert resp.status == 200
        response = await resp.json()
        assert response == influx_mock.get_generic_response()
    for url, data in sp_requests:
        resp = await client.put(url, json=data)
        assert resp.status == 200
        subtopic_responses = await resp.json()
        data_subtopics = {
            (url.replace("/api/in", "") + "/" + subtopic).strip("/")
            for subtopic in data.get(protocol.REST_SUBTOPICS_FIELD, [""])
        }
        for subtopic, response in subtopic_responses.items():
            assert subtopic in data_subtopics
            assert response == sp_mock.get_generic_response()
    for url, data, expected_status in sp_bad_requests:
        resp = await client.put(url, json=data)
        assert resp.status == expected_status

    for url, params, expected_status in influx_bad_requests:
        resp = await client.get(url, params=params)
        assert resp.status == expected_status


async def test_mqtt(api_server_fixture, mqtt_client_fixture):
    client, influx_mock, sp_mock = api_server_fixture
    mqtt_client = mqtt_client_fixture

    expected_topics = []
    expected_data = TEST_DATA
    mqtt_was_correct: Dict[str, asyncio.Event] = {}

    async def handler(topic: MQTTTopic, payload: bytes, properties: MQTTProperties):
        nonlocal expected_data, expected_topics, mqtt_was_correct
        assert topic in expected_topics
        payload_json = json.loads(payload.decode())
        assert protocol.PAYLOAD_RESPONSE_TOPIC_FIELD in payload_json
        assert payload_json[protocol.PAYLOAD_DATA_FIELD] == expected_data
        mqtt_was_correct[topic].set()

    await mqtt_client.run(
        config.MQTT_BROKER_IP, handler, ["query/mock/#", "command/mock/#"]
    )

    for url, params in influx_requests:
        expected_topic = url.replace("/api/out/", "query/").strip("/")
        expected_topics = [expected_topic]
        expected_data = params
        await client.get(url, params=params)

    for url, data in sp_requests:
        expected_topics = [
            (url.replace("/api/in/", "command/") + "/" + subtopic).strip("/")
            for subtopic in data.get(protocol.REST_SUBTOPICS_FIELD, [""])
        ]
        expected_data = data[protocol.REST_PAYLOAD_FIELD]

        events_to_wait = []
        for topic in expected_topics:
            event = asyncio.Event()
            mqtt_was_correct[topic] = event
            events_to_wait.append(event.wait())

        await client.put(url, json=data)

        await asyncio.wait_for(asyncio.gather(*events_to_wait), 1)
