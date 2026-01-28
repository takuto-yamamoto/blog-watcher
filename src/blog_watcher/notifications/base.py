from abc import ABC, abstractmethod

from blog_watcher.notifications.models import Notification


class Notifier(ABC):
    @abstractmethod
    async def send(self, notification: Notification) -> None: ...
