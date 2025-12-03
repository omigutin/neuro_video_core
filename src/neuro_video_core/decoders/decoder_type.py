from enum import Enum


class DecoderType(Enum):
    AUTO = 'auto'
    OPENCV = "opencv"
    PYAV = "pyav"
    FFMPEG = "ffmpeg"
    GSTREAMER = "gstreamer"
    HYBRID = "hybrid"

    @property
    def is_supported(self) -> bool:
        return self in {
            DecoderType.OPENCV,
            DecoderType.PYAV,
            DecoderType.HYBRID
        }
