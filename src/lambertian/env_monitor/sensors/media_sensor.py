"""Media sensor — currently playing track via Windows Media Session (SMTC/winrt)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

_log = logging.getLogger(__name__)


class MediaSensor:
    """Returns media dict using Windows.Media.Control (SMTC) via winrt.

    Wraps async winrt API in asyncio.run() to keep the monitor loop synchronous.
    Returns playing=False with null fields if no session is active or on any error.
    """

    def collect(self) -> dict[str, Any]:
        try:
            return asyncio.run(self._collect_async())
        except Exception as exc:
            _log.warning("MediaSensor.collect failed: %s", exc)
            return {"media": {"playing": False, "title": None, "artist": None, "source_app": None}}

    async def _collect_async(self) -> dict[str, Any]:
        try:
            from winsdk.windows.media.control import (  # type: ignore[import-untyped]
                GlobalSystemMediaTransportControlsSessionManager as SessionManager,
            )
        except ImportError:
            _log.warning("winsdk not available — media sensor returning empty")
            return {"media": {"playing": False, "title": None, "artist": None, "source_app": None}}

        try:
            manager = await SessionManager.request_async()
            session = manager.get_current_session()

            if session is None:
                return {
                    "media": {"playing": False, "title": None, "artist": None, "source_app": None}
                }

            info = await session.try_get_media_properties_async()
            playback = session.get_playback_info()

            from winsdk.windows.media import MediaPlaybackStatus  # type: ignore[import-untyped]

            playing = (
                playback is not None
                and playback.playback_status == MediaPlaybackStatus.PLAYING
            )

            return {
                "media": {
                    "playing": playing,
                    "title": info.title if info else None,
                    "artist": info.artist if info else None,
                    "source_app": session.source_app_user_model_id,
                }
            }
        except Exception as exc:
            _log.warning("MediaSensor async collection failed: %s", exc)
            return {"media": {"playing": False, "title": None, "artist": None, "source_app": None}}
