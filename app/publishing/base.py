"""Common interface every platform publisher implements."""
from __future__ import annotations

import abc
from dataclasses import dataclass

from app.models import ContentPiece, PlatformAccount


@dataclass
class PublishResult:
    success: bool
    remote_post_id: str = ""
    error_message: str = ""


class PlatformPublisher(abc.ABC):
    """
    Publishes a ContentPiece to one PlatformAccount. Every implementation
    must raise no exceptions for expected failure modes (missing creds,
    API rejection) — it should catch them and return a PublishResult with
    success=False and a clear error_message instead, so the scheduler can
    record the outcome without crashing the whole dispatch loop.
    """

    platform_name: str

    @abc.abstractmethod
    def publish(self, piece: ContentPiece, account: PlatformAccount, caption: str, hashtags: str) -> PublishResult:
        raise NotImplementedError
