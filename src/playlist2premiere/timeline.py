from dataclasses import dataclass
from fractions import Fraction
from .probe import Media


def frames(seconds: Fraction, fps: Fraction) -> int:
    """Round half up once, without binary floating point."""
    value = seconds * fps
    return (2 * value.numerator + value.denominator) // (2 * value.denominator)


def rate_parts(fps: Fraction) -> tuple[int, bool]:
    if fps.denominator == 1 and fps > 0:
        return int(fps), False
    base = fps * Fraction(1001, 1000)
    if base.denominator == 1 and base > 0:
        return int(base), True
    raise ValueError(f'Cadence non représentable en xmeml : {fps}')


@dataclass(frozen=True)
class Settings:
    width: int
    height: int
    fps: Fraction

    def validate(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError('Résolution strictement positive requise')
        rate_parts(self.fps)


@dataclass(frozen=True)
class Clip:
    media: Media
    start: int
    end: int
    source_end: int


@dataclass(frozen=True)
class Timeline:
    settings: Settings
    clips: tuple[Clip, ...]
    exact_duration: Fraction

    @property
    def duration(self) -> int:
        return self.clips[-1].end


def build_timeline(media: list[Media], settings: Settings | None = None) -> Timeline:
    if not media:
        raise ValueError('Aucun clip')
    settings = settings or Settings(media[0].width, media[0].height, media[0].fps)
    settings.validate()
    elapsed = Fraction(0)
    clips = []
    for item in media:
        rate_parts(item.fps)
        start = frames(elapsed, settings.fps)
        elapsed += item.duration
        end = frames(elapsed, settings.fps)
        source_end = frames(item.duration, item.fps)
        if end <= start or source_end <= 0:
            raise ValueError(f'Clip trop court pour la cadence choisie : {item.path.name}')
        clips.append(Clip(item, start, end, source_end))
    return Timeline(settings, tuple(clips), elapsed)
