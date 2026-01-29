from abc import ABC, abstractmethod

from blog_watcher.notification.models import Notification


class Notifier(ABC):
    @abstractmethod
    async def send(self, notification: Notification) -> None: ...
