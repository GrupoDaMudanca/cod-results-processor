import json
from abc import ABC
from typing import List

from app.serializable import Serializable
from config import PLAYER_NAMES_FILE_PATH


class Player(Serializable, ABC):

    def __init__(self, raw_player_name):
        self.__raw_player_name = raw_player_name

    @property
    def _serializable_properties(self) -> List[str]:
        return [
            'id',
            'name',
        ]

    @property
    def id(self):
        return self.__raw_player_name.split(']')[-1]

    @property
    def name(self) -> str:
        return Player.__get_names().get(self.id)

    @staticmethod
    def __get_names() -> dict:
        with open(PLAYER_NAMES_FILE_PATH, 'r') as player_names_file:

            return {
                player_id: player_name
                for player_name, player_ids
                in json.loads(player_names_file.read()).items()
                for player_id in
                player_ids
            }
