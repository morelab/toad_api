from toad_api.http_server import app

in_requests = {
    "iotoad.org/api/in/mock/sp/sp_m1",
    "iotoad.org/api/in/mock/sp/sp_g0",
    "iotoad.org/api/in/mock/sp/row/1",
    "iotoad.org/api/in/mock/sp/column/2",
}

out_requests = {
    "/api/out/mock/influx/sp/power?type=w",
    "/api/out/mock/influx/sp/power?operation=sum&type=w",
    "/api/out/mock/influx/sp/power?operation=median&type=w&row=1",
    "/api/out/mock/influx/sp/status?operation=median&type=g",
}


async def test_requests(aiohttp_client, loop):
    client = await aiohttp_client(app)
    for request, expected_response in in_requests:
        resp = await client.get(request)
        assert resp.status == 200
        response = await resp.json()
        assert response == expected_response
    for request, expected_response in out_requests:
        resp = await client.get(request)
        assert resp.status == 200
        response = await resp.json()
        assert response == expected_response
