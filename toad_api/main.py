from toad_api.http_server import APIServer


async def toad_api_app():
    api_server = APIServer()
    await api_server.start()
    return api_server.app
