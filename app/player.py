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
        return self.__raw_player_name.split(']')[-1].strip()

    @property
    def name(self) -> str:
        return Player.__get_names().get(self.id)

    @staticmethod
    def __get_names() -> dict:
        from app.helpers import get_player_names_map
        return get_player_names_map()
