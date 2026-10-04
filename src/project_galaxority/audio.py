"""Централизованное аудио: фон, взрывы, двигатель, boost."""
import math

from raylibpy import (
    close_audio_device,
    init_audio_device,
    load_music_stream,
    load_sound,
    load_sound_alias,
    play_music_stream,
    play_sound,
    set_music_pitch,
    set_music_volume,
    set_sound_pitch,
    set_sound_volume,
    unload_music_stream,
    unload_sound,
    update_music_stream,
)


class AudioManager:
    """Все звуки игры живут здесь.

    Публичное API:
        play_explosion(radius)  — вызвать при столкновении
        update(dt, ship)        — вызывать каждый кадр
        close()                 — при выходе
    """

    __slots__ = (
        "bg_music",
        "explosion_sound", "_explosion_pool", "_explosion_idx",
        "engine_music",
        "boost_music", "_boost_vol",
    )

    def __init__(self) -> None:
        init_audio_device()

        # ---------- Фоновая музыка ----------
        self.bg_music = load_music_stream("assets/audio/music/action_0.mp3")
        self.bg_music.looping = True
        set_music_volume(self.bg_music, 0.8)
        play_music_stream(self.bg_music)

        # ---------- Взрыв: пул перекрывающихся голосов ----------
        self.explosion_sound = load_sound("assets/audio/sfx/Explosions/Medium Length/sfx_exp_medium4.wav")
        set_sound_volume(self.explosion_sound, 0.8)
        # 4 алиаса — 4 одновременных взрыва. Хватает с головой.
        self._explosion_pool = [
            load_sound_alias(self.explosion_sound) for _ in range(4)
        ]
        self._explosion_idx = 0

        # ---------- Двигатель: бесшовный луп, volume/pitch по тяге ----------
        self.engine_music = load_music_stream("assets/audio/sfx/Movement/Vehicles/sfx_vehicle_engineloop.wav")
        self.engine_music.looping = True
        set_music_volume(self.engine_music, 0.0)
        play_music_stream(self.engine_music)

        # ---------- Boost: отдельный луп, плавно подмешиваем ----------
        self.boost_music = load_music_stream("assets/audio/sfx/Movement/Vehicles/sfx_vehicle_carloop1.wav")
        self.boost_music.looping = True
        set_music_volume(self.boost_music, 0.0)
        play_music_stream(self.boost_music)
        self._boost_vol = 0.0

    # ------------------------------------------------------------------
    def play_explosion(self, radius: float = 1.0) -> None:
        """Круглый обход пула → перекрывающиеся взрывы без обрезания."""
        pool = self._explosion_pool
        s = pool[self._explosion_idx]
        self._explosion_idx = (self._explosion_idx + 1) % len(pool)

        # Мелкие — выше и звонче; крупные — ниже и басовитее.
        pitch = 0.85 + 0.4 / max(radius, 0.1)
        volume = min(1.0, 0.45 + 0.35 * radius)
        set_sound_pitch(s, pitch)
        set_sound_volume(s, volume)
        play_sound(s)

    # ------------------------------------------------------------------
    def update(self, dt: float, ship) -> None:
        # Music нужно «двигать» вручную каждый кадр
        update_music_stream(self.bg_music)
        update_music_stream(self.engine_music)
        update_music_stream(self.boost_music)

        # ---- Двигатель: тон и громкость от throttle ----
        t = ship.throttle
        set_music_volume(self.engine_music, 0.02 + 0.25 * t)
        set_music_pitch(self.engine_music, 0.7 + 0.9 * t)

        # ---- Boost: нарастаем/затухаем экспоненциально ----
        target = 0.55 if ship.boost else 0.0
        k = 1.0 - math.exp(-8.0 * dt)
        self._boost_vol += (target - self._boost_vol) * k
        if self._boost_vol < 0.01:
            self._boost_vol = 0.0
        set_music_volume(self.boost_music, self._boost_vol)
        # Чуть «взлетающий» тон по мере набора громкости
        set_music_pitch(self.boost_music, 0.75 + 0.25 * self._boost_vol)

    # ------------------------------------------------------------------
    def close(self) -> None:
        for s in self._explosion_pool:
            unload_sound(s)
        unload_sound(self.explosion_sound)

        unload_music_stream(self.bg_music)
        unload_music_stream(self.engine_music)
        unload_music_stream(self.boost_music)

        close_audio_device()