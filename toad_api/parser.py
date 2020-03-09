from typing import Dict

from toad_api.protocol import PAYLOAD_FIELD, SUBTOPICS_FIELD


def check_request_body(data_json: Dict):
    """
    Parses POST /api/in requests body
    :param data_json: JSON dictionary containin
    :return: JSON dictionary
    """
    if 2 < len(data_json):
        raise ValueError("Invalid data JSON")
    if PAYLOAD_FIELD not in data_json:
        raise ValueError("Invalid data JSON")
    if len(data_json) == 2 and SUBTOPICS_FIELD not in data_json:
        raise ValueError("Invalid data JSON")
