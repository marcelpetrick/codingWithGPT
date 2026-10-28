# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""A captured still image plus its metadata (§6.5). Lives in memory only."""

import io
import time
from dataclasses import dataclass, field

from PIL import Image

from linkedin_reply_assistant.capture.roi import Roi


@dataclass(frozen=True)
class Capture:
    sequence_id: int
    image: Image.Image
    source_name: str
    roi: Roi | None
    timestamp: float = field(default_factory=time.time)

    @property
    def size(self) -> tuple[int, int]:
        return self.image.size

    def cropped(self) -> Image.Image:
        return self.roi.crop(self.image) if self.roi else self.image

    def metadata(self) -> dict[str, object]:
        return {
            "sequence_id": self.sequence_id,
            "timestamp": self.timestamp,
            "source": self.source_name,
            "size": f"{self.size[0]}x{self.size[1]}",
            "crop": self.roi.to_dict() if self.roi else None,
        }


def png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
