"""
audio.py — SFX detection and synthesis for the D&D display companion.

Architecture:
  Python detects SFX triggers from narration text via regex matching and
  broadcasts {"sfx": name} via SSE to all connected browsers.  The browser
  fetches synthesized WAV files from /audio/sfx/<name> and plays them via
  Web Audio API — works on any device with the browser tab open.

Requires: numpy  (pip install numpy)
If numpy is missing the module degrades silently — WAV endpoints return 404.
"""

import io
import re
import struct
from typing import Callable, Optional

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False
    np = None  # type: ignore

SR = 44100   # sample rate

# ── State ──────────────────────────────────────────────────────────────────────

_sfx_on      = False
_wav_cache: dict = {}          # key → WAV bytes
_broadcast_fn: Optional[Callable] = None


# ── Init ───────────────────────────────────────────────────────────────────────

def init() -> bool:
    """No-op — kept for API compatibility. Returns True if numpy is available."""
    return _HAS_NUMPY


# ── Broadcast wiring (called by app.py on startup) ────────────────────────────

def set_broadcast(fn: Callable) -> None:
    """Wire the SSE broadcast function so SFX events reach all browsers."""
    global _broadcast_fn
    _broadcast_fn = fn


# ── Public toggle API ─────────────────────────────────────────────────────────

def set_sfx(enabled: bool) -> None:
    global _sfx_on
    _sfx_on = enabled


def get_state() -> dict:
    return {
        "sfx":       _sfx_on,
        "available": _HAS_NUMPY,
    }


# ── Public event hooks ────────────────────────────────────────────────────────

def on_scene_change(scene_name: str) -> None:
    pass   # ambient removed — kept for API compatibility


def on_text(text: str) -> None:
    """Scan narration text for SFX triggers; broadcast at most one per call."""
    if not _sfx_on or not _broadcast_fn:
        return
    for pattern, sfx_name in _SFX_MAP:
        if pattern.search(text):
            _broadcast_fn({"sfx": sfx_name})
            return


# ── WAV generation ─────────────────────────────────────────────────────────────

def get_sfx_wav(name: str) -> Optional[bytes]:
    """Return cached WAV bytes for the SFX, synthesising on first call."""
    if not _HAS_NUMPY:
        return None
    key = f"sfx_{name}"
    if key not in _wav_cache:
        mono = _synth_sfx(name)
        if mono is None or len(mono) == 0:
            return None
        _wav_cache[key] = _to_wav_bytes(mono, vol=0.55)
    return _wav_cache[key]


def _to_wav_bytes(mono: "np.ndarray", vol: float = 0.42) -> bytes:
    """Convert a float64 mono numpy array to WAV bytes (16-bit PCM, mono)."""
    clipped = np.clip(mono * vol, -1.0, 1.0)
    i16 = (clipped * 32767).astype(np.int16)
    data = i16.tobytes()
    bits  = 16
    chans = 1
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + len(data)))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH",
        16,                         # chunk size
        1,                          # PCM
        chans,                      # channels
        SR,                         # sample rate
        SR * chans * bits // 8,     # byte rate
        chans * bits // 8,          # block align
        bits,                       # bits per sample
    ))
    buf.write(b"data")
    buf.write(struct.pack("<I", len(data)))
    buf.write(data)
    return buf.getvalue()


# ── Synthesis helpers ──────────────────────────────────────────────────────────

def _noise(n: int) -> "np.ndarray":
    return np.random.uniform(-1.0, 1.0, n)


def _sine(n: int, freq: float, phase: float = 0.0) -> "np.ndarray":
    t = np.arange(n, dtype=np.float64) / SR
    return np.sin(2.0 * np.pi * freq * t + phase)


def _lfo_env(n: int, rate_hz: float) -> "np.ndarray":
    t = np.arange(n, dtype=np.float64) / SR
    return 0.5 + 0.5 * np.sin(2.0 * np.pi * rate_hz * t)


def _fft_bp(sig: "np.ndarray", lo: float, hi: float) -> "np.ndarray":
    F     = np.fft.rfft(sig)
    freqs = np.fft.rfftfreq(len(sig), 1.0 / SR)
    F    *= (freqs >= lo) & (freqs <= hi)
    return np.fft.irfft(F, len(sig))


def _fft_lp(sig: "np.ndarray", hi: float) -> "np.ndarray":
    return _fft_bp(sig, 0.0, hi)


def _fft_hp(sig: "np.ndarray", lo: float) -> "np.ndarray":
    return _fft_bp(sig, lo, SR / 2.0)


# ── SFX synthesis ──────────────────────────────────────────────────────────────

def _synth_sfx(name: str) -> Optional["np.ndarray"]:
    if not _HAS_NUMPY:
        return None

    if name == "impact":
        n   = int(SR * 0.35)
        t   = np.arange(n) / SR
        env = np.exp(-t * 16.0)
        return _fft_lp(_noise(n), 420) * env

    if name == "sword":
        n    = int(SR * 0.28)
        t    = np.arange(n) / SR
        ring = _sine(n, 2700) * np.exp(-t * 28.0) * 0.45
        ting = _fft_bp(_noise(int(SR * 0.015)), 2000, 6000)
        ting = np.pad(ting, (0, n - len(ting)))
        return ring + ting * 0.25

    if name == "thud":
        n   = int(SR * 0.45)
        t   = np.arange(n) / SR
        low = _sine(n, 58) * np.exp(-t * 11.0) * 0.50
        bod = _fft_lp(_noise(n), 210) * np.exp(-t * 9.0) * 0.45
        return low + bod

    if name == "arrow":
        n     = int(SR * 0.22)
        sweep = np.linspace(900.0, 180.0, n)
        phase = np.cumsum(2.0 * np.pi * sweep / SR)
        t     = np.arange(n) / SR
        return np.sin(phase) * np.exp(-t * 7.0) * 0.45

    if name == "shout":
        n   = int(SR * 0.30)
        t   = np.arange(n) / SR
        env = np.exp(-t * 5.5) * (1.0 - np.exp(-t * 45.0))
        return _fft_bp(_noise(n), 280, 1300) * env * 0.60

    if name == "magic":
        n   = int(SR * 0.65)
        t   = np.arange(n) / SR
        rng = np.random.default_rng()
        freqs = [523.0, 659.0, 784.0, 1047.0]
        wave  = sum(
            _sine(n, f, phase=rng.uniform(0, 6.28)) * np.exp(-t * (3.5 + i * 0.8))
            for i, f in enumerate(freqs)
        ) / len(freqs) * 0.55
        shimmer = _fft_bp(_noise(n), 2500, 9000) * np.exp(-t * 4.5) * 0.10
        return wave + shimmer

    if name == "low_hum":
        n   = int(SR * 1.2)
        t   = np.arange(n) / SR
        env = np.sin(np.pi * t / t[-1])
        return _sine(n, 48) * env * 0.38

    if name == "coins":
        n   = int(SR * 0.32)
        t   = np.arange(n) / SR
        rng = np.random.default_rng()
        pings = sum(
            _sine(n, f) * np.exp(-t * 32.0) * rng.uniform(0.3, 0.8)
            for f in (1100.0, 1400.0, 1750.0, 2050.0)
        )
        return pings / 4.0 * 0.50

    if name == "door":
        n   = int(SR * 0.55)
        t   = np.arange(n) / SR
        env = np.sin(np.pi * t / t[-1])
        return _fft_bp(_noise(n), 180, 900) * env * 0.50

    if name == "fire":
        n   = int(SR * 0.90)
        lfo = _lfo_env(n, 3.8)
        crk = _fft_bp(_noise(n), 1400, 4500) * lfo * 0.30
        bas = _fft_bp(_noise(n), 80, 350) * 0.45
        return crk + bas

    if name == "breath":
        n   = int(SR * 0.45)
        t   = np.arange(n) / SR
        env = np.sin(np.pi * t / t[-1])
        return _fft_bp(_noise(n), 200, 700) * env * 0.28

    return np.array([], dtype=np.float64)


# ── SFX trigger map ────────────────────────────────────────────────────────────

_SFX_MAP = [
    (re.compile(r'\b(?:strike[sd]?|struck|slam(?:s|med)?|bash(?:es|ed)?|smash(?:es|ed)?)\b', re.I), "impact"),
    (re.compile(r'\b(?:sword|blade|dagger|steel|cleave[sd]?|parr(?:ies|ied|y))\b',            re.I), "sword"),
    (re.compile(r'\b(?:arrow[s]?|bolt[s]?|looses?|shoots?\s+\w+|fires?\s+\w+)\b',             re.I), "arrow"),
    (re.compile(r'\b(?:scream[s]?|screaming|shout[s]?|yell[s]?|roar[s]?|cries?)\b',           re.I), "shout"),
    (re.compile(r'\b(?:falls?\s+to|fell|collapses?|tumbles?|crashes?|drops?\s+to)\b',          re.I), "thud"),
    (re.compile(r'\b(?:hit[s]?|blow[s]?|punch(?:es|ed)?|kick[s]?)\b',                         re.I), "impact"),
    (re.compile(r'\b(?:magic|arcane|spell|cast[s]?|glow[s]?|shimmer[s]?|spark[s]?|crackl)\b', re.I), "magic"),
    (re.compile(r'\b(?:coin[s]?|gold|clink[s]?|jingle[s]?|purse)\b',                          re.I), "coins"),
    (re.compile(r'\b(?:door[s]?\s+(?:open|close|slam|creak)|creak[s]?|hinge[s]?)\b',          re.I), "door"),
    (re.compile(r'\b(?:hum[s]?|humming|vibrat(?:es|ed|ing)|resonat(?:es|ed|ing))\b',           re.I), "low_hum"),
    (re.compile(r'\b(?:fire[s]?|flame[s]?|torch(?:es)?|blaze|burn[s]?)\b',                    re.I), "fire"),
    (re.compile(r'\b(?:breath[s]?|exhale[s]?|inhale[s]?|gasp[s]?)\b',                         re.I), "breath"),
]
