from abc import ABC, abstractmethod

class MessengerClient(ABC):
    @abstractmethod
    def send_message(self, text: str, reply_to_message_id: str = None, msg_type: str = "UNKNOWN"):
        """Send a simple text message."""
        pass

    @abstractmethod
    def send_photo(self, photo_path: str, caption: str = None, reply_to_message_id: str = None, msg_type: str = "UNKNOWN"):
        """Send a photo with an optional caption."""
        pass
