from abc import ABC, abstractmethod

class BaseListener(ABC):
    @abstractmethod
    def poll_and_download(self, timeout: int = 30) -> int:
        """Poll for new messages, download media if present, and handle commands.
        Returns the last processed update ID.
        """
        pass

    @abstractmethod
    def confirm_updates(self, last_update_id: int):
        """Acknowledge updates so they aren't processed again."""
        pass
