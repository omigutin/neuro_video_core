class VideoSourceError(Exception):
    """Base exception for video source errors."""


class VideoOpenError(VideoSourceError):
    """Source cannot be opened."""


class VideoReadError(VideoSourceError):
    """Frame cannot be read."""
