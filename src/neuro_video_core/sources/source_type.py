from enum import Enum


class SourceType(Enum):
    FILE = "file"
    RTSP = "rtsp"
    HTTP = "http"
    HTTPS = "https"
    CAMERA = "camera"
    RAW_FRAMES = "raw_frames"
    MEMORY_MMAP = "memory_mmap"
    YANDEX_DISK = "yandex_disk"
    GOOGLE_DRIVE = "google_drive"
    S3 = "s3"
    PIPE = "pipe"

    @property
    def is_supported(self) -> bool:
        return self in {
            SourceType.FILE,
            SourceType.RTSP,
            SourceType.CAMERA,
        }
