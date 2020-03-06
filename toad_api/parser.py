from typing import Dict, Union
import json

from toad_api.protocol import PAYLOAD_FIELD, SUBTOPICS_FIELD


def parse_data(data: Union[str, bytes]) -> Dict:
    data_json = json.loads(data)
    if 2 < len(data_json):
        raise ValueError("Invalid data JSON")
    if PAYLOAD_FIELD not in data_json:
        raise ValueError("Invalid data JSON")
    if len(data_json) == 2 and SUBTOPICS_FIELD not in data_json:
        raise ValueError("Invalid data JSON")
    return data_json
