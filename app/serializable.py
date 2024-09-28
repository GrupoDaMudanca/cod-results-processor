from abc import ABC, abstractmethod
from typing import List


class Serializable(ABC):

    @property
    @abstractmethod
    def _serializable_properties(self) -> List[str]:
        pass

    def to_dict(
        self,
        serialize_only: List[str] = None,
        override_serialization: dict = None
    ) -> dict:

        override_serialization = override_serialization or {}

        return {
            **{
                attrib_name: (
                    getattr(self, attrib_name).to_dict()
                    if isinstance(getattr(self, attrib_name), Serializable)
                    else getattr(self, attrib_name)
                )
                for attrib_name in (
                    serialize_only
                    if serialize_only else
                    self._serializable_properties
                )
                if not override_serialization or attrib_name not in override_serialization.keys()
            },
            **override_serialization
        }
