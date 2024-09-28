import hashlib
import json

from abc import ABC
from typing import List, Dict

from app.player import Player
from app.serializable import Serializable


class MatchRecord(Serializable, ABC):

    def __init__(
        self,
        raw_player_name: str,
        score: int,
        kills: int,
        damage: int,
        redeploys: int,
        objectives: int
    ):
        self.player = Player(
            raw_player_name=raw_player_name
        )
        self.score = score
        self.kills = kills
        self.damage = damage
        self.redeploys = redeploys
        self.objectives = objectives

    @property
    def _serializable_properties(self) -> List[str]:
        return [
            'player',
            'score',
            'kills',
            'damage',
            'redeploys',
            'objectives'
        ]


class Match(Serializable, ABC):
    def __init__(
        self,
        record1: MatchRecord,
        record2: MatchRecord,
        record3: MatchRecord,
        record4: MatchRecord
    ):
        self.record1 = record1
        self.record2 = record2
        self.record3 = record3
        self.record4 = record4

    @property
    def _serializable_properties(self) -> List[str]:
        return [
            'id',
            'records',
        ]

    @property
    def id(self) -> str:
        serializable_properties = self._serializable_properties

        # Do not try to serialize itself
        serializable_properties.remove('id')

        dhash = hashlib.sha256()

        encoded = json.dumps(
            self.to_dict(serialize_only=serializable_properties),
            sort_keys=True
        ).encode()

        dhash.update(encoded)

        return dhash.hexdigest()

    @property
    def records(self) -> List[MatchRecord]:
        return [
            self.record1,
            self.record2,
            self.record3,
            self.record4
        ]

    def to_dict(
        self,
        serialize_only: List[str] = None,
        override_serialization: Dict[str, Dict] = None
    ) -> dict:
        return super().to_dict(
            serialize_only=serialize_only,
            override_serialization={
                'records': [record.to_dict() for record in self.records]
            }
        )
