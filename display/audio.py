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
import os
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


# ── Broadcast wiring (called by dnd-display-app.py on startup) ────────────────

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


# ── SFX language packs ──────────────────────────────────────────────────────────
# Each language contributes trigger phrases per SFX category.
# Convention:
#   "word"       → literal match (with auto-suffix for Latin scripts)
#   "word1 word2" → words must appear in sequence (whitespace between)
#   "word +"     → word followed by exactly one other token
# Add a language by adding a new top-level key — zero code changes needed.

_SFX_TRIGGERS: dict[str, dict[str, list[str]]] = {
    # English (en-IN, en-US share the pack)
    "en": {
        "impact":  ["strike", "strikes", "struck", "slam", "slams", "slammed",
                    "bash", "bashes", "bashed", "smash", "smashes", "smashed",
                    "hit", "hits", "blow", "blows", "punch", "punches", "punched",
                    "kick", "kicks"],
        "sword":   ["sword", "blade", "dagger", "steel", "cleave", "cleaves", "cleaved",
                    "parry", "parries", "parried"],
        "arrow":   ["arrow", "arrows", "bolt", "bolts", "loose", "looses",
                    "shoot +", "fire +"],
        "shout":   ["scream", "screams", "screaming", "shout", "shouts",
                    "yell", "yells", "roar", "roars", "cry", "cries"],
        "thud":    ["falls to", "fell", "collapse", "collapses", "tumble", "tumbles",
                    "crash", "crashes", "drops to"],
        "magic":   ["magic", "arcane", "spell", "cast", "casts",
                    "glow", "glows", "shimmer", "shimmers", "spark", "sparks", "crackle"],
        "coins":   ["coin", "coins", "gold", "clink", "clinks", "jingle", "jingles", "purse"],
        "door":    ["door open", "door close", "door slam", "door creak",
                    "creak", "creaks", "hinge", "hinges"],
        "low_hum": ["hum", "hums", "humming", "vibrate", "vibrates", "vibrating",
                    "resonate", "resonates", "resonating"],
        "fire":    ["fire", "fires", "flame", "flames", "torch", "torches",
                    "blaze", "burn", "burns"],
        "breath":  ["breath", "breaths", "exhale", "exhales", "inhale", "inhales",
                    "gasp", "gasps"],
    },

    # Spanish (es-US)
    "es": {
        "impact":  ["golpe", "golpea", "golpeó", "embiste", "aplasta", "rompe", "estrella"],
        "sword":   ["espada", "hoja", "daga", "acero", "parar", "paró", "estoque"],
        "arrow":   ["flecha", "flechas", "saeta", "dispara", "tensa", "ballesta"],
        "shout":   ["grita", "grito", "chilla", "ruge", "rugido", "aúlla"],
        "thud":    ["cae", "se desploma", "tropieza", "se derrumba"],
        "magic":   ["magia", "arcano", "hechizo", "conjura", "lanza el hechizo", "destella"],
        "coins":   ["moneda", "monedas", "oro", "tintinea", "bolsa"],
        "door":    ["puerta", "cruje", "bisagra", "portón"],
        "low_hum": ["zumba", "zumbido", "vibra", "resuena"],
        "fire":    ["fuego", "llama", "llamas", "antorcha", "arde", "incendia"],
        "breath":  ["respira", "aliento", "exhala", "inhala", "jadea"],
    },

    # French (fr-FR)
    "fr": {
        "impact":  ["frappe", "frappes", "frappa", "cogne", "écrase", "brise", "percute"],
        "sword":   ["épée", "lame", "dague", "acier", "para", "pare", "parade"],
        "arrow":   ["flèche", "flèches", "carreau", "décoche", "bande l'arc"],
        "shout":   ["crie", "cri", "hurle", "rugit", "rugissement", "beugle"],
        "thud":    ["tombe", "s'effondre", "trébuche", "s'écrase"],
        "magic":   ["magie", "arcane", "sort", "incantation", "lance le sort", "scintille"],
        "coins":   ["pièce", "pièces", "or", "tintent", "bourse"],
        "door":    ["porte", "grince", "gond", "portail"],
        "low_hum": ["bourdonne", "vibre", "résonne"],
        "fire":    ["feu", "flamme", "flammes", "torche", "brûle", "embrase"],
        "breath":  ["respire", "souffle", "expire", "inspire", "halète"],
    },

    # German (de-DE)
    "de": {
        "impact":  ["schlägt", "schlug", "trifft", "kracht", "zerschmettert", "prallt"],
        "sword":   ["schwert", "klinge", "dolch", "stahl", "pariert", "schneide"],
        "arrow":   ["pfeil", "pfeile", "bolzen", "schießt", "spannt den bogen"],
        "shout":   ["schreit", "brüllt", "ruft", "kreischt", "heult"],
        "thud":    ["fällt", "stürzt", "kollabiert", "taumelt", "knallt"],
        "magic":   ["magie", "arkan", "zauber", "wirkt", "spricht den zauber", "funkelt"],
        "coins":   ["münze", "münzen", "gold", "klimpert", "beutel"],
        "door":    ["tür", "knarrt", "scharnier", "tor"],
        "low_hum": ["summt", "vibriert", "schwingt"],
        "fire":    ["feuer", "flamme", "flammen", "fackel", "brennt", "lodert"],
        "breath":  ["atmet", "atem", "haucht", "keucht", "japst"],
    },

    # Italian (it-IT)
    "it": {
        "impact":  ["colpisce", "colpo", "schianta", "spacca", "sbatte"],
        "sword":   ["spada", "lama", "pugnale", "acciaio", "para", "parata"],
        "arrow":   ["freccia", "frecce", "dardo", "scocca", "tende l'arco"],
        "shout":   ["grida", "urla", "ruggisce", "ringhia", "strilla"],
        "thud":    ["cade", "crolla", "stramazza", "inciampa"],
        "magic":   ["magia", "arcano", "incantesimo", "lancia l'incantesimo", "scintilla"],
        "coins":   ["moneta", "monete", "oro", "tintinna", "borsa"],
        "door":    ["porta", "scricchiola", "cardine", "portone"],
        "low_hum": ["ronza", "vibra", "risuona"],
        "fire":    ["fuoco", "fiamma", "fiamme", "torcia", "brucia", "arde"],
        "breath":  ["respira", "respiro", "espira", "inspira", "ansima"],
    },

    # Portuguese (pt-BR)
    "pt": {
        "impact":  ["golpe", "golpeia", "atinge", "esmaga", "estilhaça", "soca"],
        "sword":   ["espada", "lâmina", "adaga", "aço", "apara", "estoque"],
        "arrow":   ["flecha", "flechas", "virote", "atira", "retesa o arco"],
        "shout":   ["grita", "grito", "berra", "ruge", "uiva"],
        "thud":    ["cai", "desaba", "tropeça", "tomba"],
        "magic":   ["magia", "arcano", "feitiço", "lança o feitiço", "brilha", "cintila"],
        "coins":   ["moeda", "moedas", "ouro", "tilinta", "bolsa"],
        "door":    ["porta", "range", "dobradiça", "portão"],
        "low_hum": ["zumbe", "vibra", "ressoa"],
        "fire":    ["fogo", "chama", "chamas", "tocha", "queima", "arde"],
        "breath":  ["respira", "respiração", "expira", "inspira", "ofega"],
    },

    # Dutch (nl-NL)
    "nl": {
        "impact":  ["slaat", "ramt", "verbrijzelt", "beukt", "smeert"],
        "sword":   ["zwaard", "kling", "dolk", "staal", "pareert"],
        "arrow":   ["pijl", "pijlen", "schiet", "spant de boog"],
        "shout":   ["schreeuwt", "brult", "krijst", "roept"],
        "thud":    ["valt", "stort", "zakt in elkaar", "tuimelt"],
        "magic":   ["magie", "arcaan", "spreuk", "spreekt de spreuk", "glinstert"],
        "coins":   ["munt", "munten", "goud", "rinkelt", "buidel"],
        "door":    ["deur", "kraakt", "scharnier", "poort"],
        "low_hum": ["zoemt", "trilt", "resoneert"],
        "fire":    ["vuur", "vlam", "vlammen", "fakkel", "brandt"],
        "breath":  ["ademt", "adem", "ademt uit", "hijgt"],
    },

    # Polish (pl-PL)
    "pl": {
        "impact":  ["uderza", "uderzył", "wali", "rąbie", "miażdży"],
        "sword":   ["miecz", "ostrze", "sztylet", "stal", "paruje"],
        "arrow":   ["strzała", "strzały", "bełt", "strzela", "napina łuk"],
        "shout":   ["krzyczy", "krzyk", "ryczy", "wrzeszczy"],
        "thud":    ["upada", "wali się", "potyka się", "runął"],
        "magic":   ["magia", "tajemny", "zaklęcie", "rzuca zaklęcie", "iskrzy"],
        "coins":   ["moneta", "monety", "złoto", "brzęczy", "sakiewka"],
        "door":    ["drzwi", "skrzypią", "zawias", "brama"],
        "low_hum": ["buczy", "wibruje", "rezonuje"],
        "fire":    ["ogień", "płomień", "płomienie", "pochodnia", "płonie"],
        "breath":  ["oddycha", "oddech", "wydycha", "wdycha", "dyszy"],
    },

    # Romanian (ro-RO)
    "ro": {
        "impact":  ["lovește", "lovi", "izbește", "zdrobește", "sfărâmă"],
        "sword":   ["sabie", "lamă", "pumnal", "oțel", "parează"],
        "arrow":   ["săgeată", "săgeți", "trage", "încordează arcul"],
        "shout":   ["strigă", "țipă", "urlă", "răcnește"],
        "thud":    ["cade", "se prăbușește", "se împiedică"],
        "magic":   ["magie", "arcan", "vrajă", "aruncă vraja", "sclipește"],
        "coins":   ["monedă", "monede", "aur", "zornăie", "pungă"],
        "door":    ["ușa", "scârțâie", "balama", "poartă"],
        "low_hum": ["bâzâie", "vibrează", "rezonează"],
        "fire":    ["foc", "flacără", "flăcări", "torță", "arde"],
        "breath":  ["respiră", "respirație", "expiră", "inspiră", "gâfâie"],
    },

    # Russian (ru-RU)
    "ru": {
        "impact":  ["удар", "ударяет", "бьёт", "сокрушает", "врезается"],
        "sword":   ["меч", "клинок", "кинжал", "сталь", "парирует"],
        "arrow":   ["стрела", "стрелы", "болт", "стреляет", "натягивает лук"],
        "shout":   ["кричит", "крик", "ревёт", "вопит", "рычит"],
        "thud":    ["падает", "рушится", "спотыкается", "повалился"],
        "magic":   ["магия", "тайный", "заклинание", "произносит заклинание", "искрится"],
        "coins":   ["монета", "монеты", "золото", "звенит", "кошелёк"],
        "door":    ["дверь", "скрипит", "петля", "ворота"],
        "low_hum": ["гудит", "вибрирует", "резонирует"],
        "fire":    ["огонь", "пламя", "факел", "горит", "пылает"],
        "breath":  ["дышит", "дыхание", "выдыхает", "вдыхает", "задыхается"],
    },

    # Ukrainian (uk-UA)
    "uk": {
        "impact":  ["удар", "ударяє", "б'є", "трощить", "врізається"],
        "sword":   ["меч", "клинок", "кинджал", "сталь", "парирує"],
        "arrow":   ["стріла", "стріли", "болт", "стріляє", "натягує лук"],
        "shout":   ["кричить", "крик", "реве", "волає", "гарчить"],
        "thud":    ["падає", "валиться", "спотикається"],
        "magic":   ["магія", "арканний", "закляття", "промовляє закляття", "іскриться"],
        "coins":   ["монета", "монети", "золото", "дзвенить", "гаманець"],
        "door":    ["двері", "скрипить", "завіса", "ворота"],
        "low_hum": ["гуде", "вібрує", "резонує"],
        "fire":    ["вогонь", "полум'я", "смолоскип", "горить", "палає"],
        "breath":  ["дихає", "дихання", "видихає", "вдихає", "задихається"],
    },

    # Turkish (tr-TR)
    "tr": {
        "impact":  ["vurur", "darbe", "çarpar", "ezer", "kırar"],
        "sword":   ["kılıç", "bıçak", "hançer", "çelik", "savuşturur"],
        "arrow":   ["ok", "oklar", "atar", "yayı gerer"],
        "shout":   ["bağırır", "haykırır", "kükrer", "çığlık"],
        "thud":    ["düşer", "yığılır", "tökezler", "çöker"],
        "magic":   ["büyü", "gizemli", "büyü yapar", "büyüyü okur", "parlar"],
        "coins":   ["sikke", "altın", "şıngırdar", "kese"],
        "door":    ["kapı", "gıcırdar", "menteşe"],
        "low_hum": ["uğuldar", "titrer", "rezonans"],
        "fire":    ["ateş", "alev", "alevler", "meşale", "yanar"],
        "breath":  ["nefes", "nefes alır", "nefes verir", "soluk"],
    },

    # Indonesian (id-ID)
    "id": {
        "impact":  ["pukul", "memukul", "menghantam", "menghancurkan", "membenturkan"],
        "sword":   ["pedang", "bilah", "belati", "baja", "menangkis"],
        "arrow":   ["panah", "anak panah", "menembak", "merentangkan busur"],
        "shout":   ["berteriak", "menjerit", "mengaum", "memekik"],
        "thud":    ["jatuh", "tumbang", "tersandung", "ambruk"],
        "magic":   ["sihir", "arkana", "mantra", "merapal mantra", "berkilau"],
        "coins":   ["koin", "emas", "gemerincing", "kantong uang"],
        "door":    ["pintu", "berderit", "engsel", "gerbang"],
        "low_hum": ["bergumam", "bergetar", "beresonansi"],
        "fire":    ["api", "nyala", "obor", "membakar", "berkobar"],
        "breath":  ["napas", "bernapas", "menghela napas", "terengah"],
    },

    # Vietnamese (vi-VN)
    "vi": {
        "impact":  ["đánh", "đập", "tông", "đập tan", "nện"],
        "sword":   ["kiếm", "lưỡi kiếm", "dao găm", "thép", "đỡ đòn"],
        "arrow":   ["mũi tên", "tên", "bắn", "giương cung"],
        "shout":   ["hét", "gào", "rống", "thét"],
        "thud":    ["ngã", "đổ sụp", "vấp", "sụp xuống"],
        "magic":   ["phép thuật", "huyền bí", "thần chú", "niệm chú", "lấp lánh"],
        "coins":   ["đồng tiền", "vàng", "leng keng", "túi tiền"],
        "door":    ["cửa", "cọt kẹt", "bản lề", "cổng"],
        "low_hum": ["vo ve", "rung", "vang vọng"],
        "fire":    ["lửa", "ngọn lửa", "đuốc", "cháy", "bốc cháy"],
        "breath":  ["hơi thở", "thở", "thở ra", "hít vào", "thở gấp"],
    },

    # Hindi (hi-IN) — Devanagari
    "hi": {
        "impact":  ["प्रहार", "मारता", "टकराता", "तोड़ता"],
        "sword":   ["तलवार", "खंजर", "इस्पात", "धार"],
        "arrow":   ["तीर", "बाण", "चलाता", "धनुष"],
        "shout":   ["चिल्लाता", "गरजता", "हुंकार", "दहाड़"],
        "thud":    ["गिरता", "गिर पड़ा", "लड़खड़ाता"],
        "magic":   ["जादू", "मंत्र", "तंत्र", "जादू करता", "चमकता"],
        "coins":   ["सिक्का", "स्वर्ण", "खनकता", "थैली"],
        "door":    ["दरवाज़ा", "चरमराता", "कब्ज़ा"],
        "low_hum": ["गुंजन", "कांपता", "गूंजता"],
        "fire":    ["आग", "लौ", "ज्वाला", "मशाल", "जलता"],
        "breath":  ["सांस", "सांस लेता", "हांफता"],
    },

    # Marathi (mr-IN) — Devanagari, distinct vocabulary
    "mr": {
        "impact":  ["आघात", "मारतो", "ठोकतो", "तोडतो"],
        "sword":   ["तलवार", "कट्यार", "पोलाद", "धार"],
        "arrow":   ["बाण", "तीर", "धनुष्य"],
        "shout":   ["ओरडतो", "गर्जतो", "हाक"],
        "thud":    ["पडतो", "कोसळतो", "अडखळतो"],
        "magic":   ["जादू", "मंत्र", "जादू करतो", "चमकतो"],
        "coins":   ["नाणे", "सोनं", "किणकिणतो"],
        "door":    ["दार", "करकरतो", "बिजागिरी"],
        "low_hum": ["गुणगुणतो", "थरथरतो"],
        "fire":    ["अग्नी", "ज्वाला", "मशाल", "जळतो"],
        "breath":  ["श्वास", "श्वास घेतो", "धापा"],
    },

    # Bengali (bn-BD)
    "bn": {
        "impact":  ["আঘাত", "মারে", "ধাক্কা", "ভেঙে দেয়"],
        "sword":   ["তরবারি", "ছুরি", "ইস্পাত", "ধার"],
        "arrow":   ["তীর", "বাণ", "ছোঁড়ে", "ধনুক"],
        "shout":   ["চিৎকার", "গর্জন", "হুঙ্কার"],
        "thud":    ["পড়ে", "ধসে পড়ে", "হোঁচট"],
        "magic":   ["যাদু", "মন্ত্র", "যাদু করে", "ঝিকমিক"],
        "coins":   ["মুদ্রা", "স্বর্ণ", "ঝংকার", "থলি"],
        "door":    ["দরজা", "ক্যাঁচ", "কব্জা"],
        "low_hum": ["গুঞ্জন", "কাঁপে", "অনুরণন"],
        "fire":    ["আগুন", "শিখা", "মশাল", "জ্বলে"],
        "breath":  ["শ্বাস", "শ্বাস নেয়", "হাঁপায়"],
    },

    # Tamil (ta-IN)
    "ta": {
        "impact":  ["தாக்கு", "அறை", "மோதி", "உடைக்கிறது"],
        "sword":   ["வாள்", "கத்தி", "எஃகு"],
        "arrow":   ["அம்பு", "வில்", "எய்கிறது"],
        "shout":   ["கூச்சல்", "கர்ஜனை", "அலறுகிறது"],
        "thud":    ["விழுகிறது", "சரிகிறது"],
        "magic":   ["மந்திரம்", "மாயம்", "மந்திரம் செய்கிறது", "ஒளிர்கிறது"],
        "coins":   ["நாணயம்", "தங்கம்", "மணி", "பை"],
        "door":    ["கதவு", "சத்தம்", "கீல்"],
        "low_hum": ["ஒலி", "அதிர்வு"],
        "fire":    ["தீ", "சுடர்", "தீப்பந்தம்", "எரிகிறது"],
        "breath":  ["மூச்சு", "மூச்சு விடுகிறது", "மூச்சிரைக்கிறது"],
    },

    # Telugu (te-IN)
    "te": {
        "impact":  ["దెబ్బ", "కొడుతుంది", "ఢీకొంటుంది", "విరిగిపోతుంది"],
        "sword":   ["కత్తి", "ఖడ్గం", "ఉక్కు"],
        "arrow":   ["బాణం", "విల్లు", "వదులుతుంది"],
        "shout":   ["అరుపు", "గర్జన", "కేక"],
        "thud":    ["పడిపోతుంది", "కూలిపోతుంది"],
        "magic":   ["మంత్రం", "మాయ", "మంత్రం వేస్తుంది", "మెరుస్తుంది"],
        "coins":   ["నాణెం", "బంగారం", "మోతిస్తుంది", "సంచి"],
        "door":    ["తలుపు", "క్రీచ్", "బందు"],
        "low_hum": ["హుంకారం", "కంపన"],
        "fire":    ["అగ్ని", "మంట", "కాగడా", "మండుతుంది"],
        "breath":  ["శ్వాస", "ఊపిరి", "రొప్పుతుంది"],
    },

    # Thai (th-TH) — no inter-word spaces, treated as unspaced
    "th": {
        "impact":  ["โจมตี", "ฟาด", "ทุบ", "ปะทะ", "ทำลาย"],
        "sword":   ["ดาบ", "ใบมีด", "มีดสั้น", "เหล็กกล้า"],
        "arrow":   ["ลูกธนู", "ธนู", "ยิง", "ขึ้นคันธนู"],
        "shout":   ["ตะโกน", "คำราม", "ร้อง", "กรีดร้อง"],
        "thud":    ["ล้ม", "ทรุดลง", "สะดุด"],
        "magic":   ["เวทมนตร์", "เวท", "ร่ายเวท", "ส่องประกาย"],
        "coins":   ["เหรียญ", "ทอง", "กรุ๊งกริ๊ง", "ถุงเงิน"],
        "door":    ["ประตู", "เสียงเอี๊ยด", "บานพับ"],
        "low_hum": ["หึ่ง", "สั่น", "ก้อง"],
        "fire":    ["ไฟ", "เปลว", "คบเพลิง", "เผา"],
        "breath":  ["หายใจ", "ลมหายใจ", "หอบ"],
    },

    # Japanese (ja-JP) — unspaced script
    "ja": {
        "impact":  ["殴る", "殴った", "叩く", "ぶつかる", "粉砕", "砕く"],
        "sword":   ["剣", "刃", "短剣", "鋼", "受け流す", "刀"],
        "arrow":   ["矢", "弓", "射る", "弓を引く"],
        "shout":   ["叫ぶ", "怒鳴る", "咆哮", "悲鳴"],
        "thud":    ["倒れる", "崩れ落ちる", "つまずく"],
        "magic":   ["魔法", "秘術", "呪文", "詠唱", "煌めく", "輝く"],
        "coins":   ["硬貨", "金貨", "ちゃりん", "金", "袋"],
        "door":    ["扉", "ドア", "きしむ", "蝶番"],
        "low_hum": ["唸る", "振動", "共鳴"],
        "fire":    ["火", "炎", "焔", "松明", "燃える"],
        "breath":  ["息", "呼吸", "吐息", "あえぐ"],
    },

    # Korean (ko-KR) — Hangul, mostly spaced but treated as unspaced for literal substring
    "ko": {
        "impact":  ["때리다", "친다", "박살", "충돌", "강타"],
        "sword":   ["검", "칼", "단검", "강철", "받아치다"],
        "arrow":   ["화살", "활", "쏘다", "활시위"],
        "shout":   ["외치다", "비명", "포효", "고함"],
        "thud":    ["쓰러진다", "무너진다", "비틀거린다"],
        "magic":   ["마법", "비술", "주문", "주문을 외운다", "반짝인다"],
        "coins":   ["동전", "금화", "쨍그랑", "주머니"],
        "door":    ["문", "삐걱", "경첩"],
        "low_hum": ["윙윙", "진동", "공명"],
        "fire":    ["불", "불꽃", "횃불", "타오른다"],
        "breath":  ["숨", "호흡", "내쉰다", "헐떡인다"],
    },

    # Chinese (zh-CN) — original PR #32 pack, unchanged
    "zh": {
        "impact":  ["猛击", "重击", "砸", "撞", "轰", "粉碎", "劈砍"],
        "sword":   ["拔剑", "挥剑", "剑", "格挡", "招架", "利刃", "刀刃", "劈砍"],
        "arrow":   ["射箭", "放箭", "离弦", "拉弓", "箭矢", "弩箭"],
        "shout":   ["咆哮", "怒吼", "尖叫", "大喊", "呐喊", "嘶吼"],
        "thud":    ["倒地", "倒下", "摔倒", "坠落", "跌落"],
        "magic":   ["施法", "魔力", "奥术", "法术", "噼啪", "魔法阵", "符文", "闪烁", "秘法"],
        "coins":   ["叮当", "金币", "银币", "铜币", "钱袋"],
        "door":    ["吱呀", "咯吱", "推开门", "门轴", "嘎吱"],
        "low_hum": ["嗡嗡", "嗡鸣", "低鸣", "共鸣", "震颤"],
        "fire":    ["火焰", "烈焰", "火球", "火把", "燃烧", "烈火", "点燃"],
        "breath":  ["呼吸", "吐息", "喘息", "喘气", "深吸"],
    },

    # Arabic (ar-EG) — RTL, connected script, treated as unspaced literal match
    "ar": {
        "impact":  ["يضرب", "ضربة", "يصدم", "يحطم", "يدق"],
        "sword":   ["سيف", "نصل", "خنجر", "فولاذ"],
        "arrow":   ["سهم", "سهام", "يطلق", "قوس"],
        "shout":   ["يصرخ", "صرخة", "يزأر", "يهتف"],
        "thud":    ["يسقط", "ينهار", "يتعثر"],
        "magic":   ["سحر", "تعويذة", "يلقي تعويذة", "يتلألأ"],
        "coins":   ["عملة", "ذهب", "يرن", "كيس"],
        "door":    ["باب", "يصرّ", "مفصلة", "بوابة"],
        "low_hum": ["يطن", "يهتز", "يرن"],
        "fire":    ["نار", "لهب", "مشعل", "يحترق"],
        "breath":  ["نفس", "يتنفس", "يلهث"],
    },
}

# Languages whose scripts are unspaced (or where literal substring matching
# is the right semantic): no \b word boundaries; phrases match anywhere.
# Includes CJK, Thai, Arabic (RTL, connected glyphs).
_UNSPACED_LANGS = frozenset(["zh", "ja", "ko", "th", "ar"])

# Backwards-compat alias — pre-existing code referenced _CJK_LANGS.
_CJK_LANGS = _UNSPACED_LANGS
_CJK_START = "一"
_CJK_END   = "鿿"

# All language codes we ship packs for. Used for validation in set_sfx_languages.
_AVAILABLE_LANGS = frozenset(_SFX_TRIGGERS.keys())


def _compile_trigger_list(triggers: list[str], is_unspaced: bool) -> str:
    """Build a regex alternation string from a list of trigger phrases.

    `is_unspaced` languages (CJK, Thai, Arabic) use literal substring matching
    because there are no word-boundary tokens to anchor on (or, in Arabic's
    case, the glyphs connect rather than separate cleanly).
    """
    parts: list[str] = []
    for t in triggers:
        t = t.strip()
        if not t:
            continue
        if is_unspaced:
            parts.append(re.escape(t))
        elif t.endswith(" +"):
            word = re.escape(t[:-2].strip())
            parts.append(r"\b" + word + r"\s+\w+")
        elif " " in t:
            words = [re.escape(w) for w in t.split()]
            parts.append(r"\b" + r"\s+".join(words) + r"\b")
        else:
            parts.append(r"\b" + re.escape(t) + r"\b")

    return "|".join(parts)


def _rebuild_sfx_map() -> None:
    """Rebuild _SFX_MAP from active language packs."""
    global _SFX_MAP
    _SFX_MAP.clear()
    for lang in _SFX_LANGUAGES:
        pack = _SFX_TRIGGERS.get(lang)
        if not pack:
            continue
        is_unspaced = lang in _UNSPACED_LANGS
        # Latin / Cyrillic / Greek / Indic etc. → case-insensitive match.
        # Unspaced scripts → no flag; case isn't meaningful in those scripts.
        flag = re.UNICODE if is_unspaced else (re.IGNORECASE | re.UNICODE)
        for sfx_name, triggers in pack.items():
            regex = _compile_trigger_list(triggers, is_unspaced)
            if regex:
                _SFX_MAP.append((re.compile(regex, flag), sfx_name))


# ── Active language configuration ──────────────────────────────────────────────

_SFX_LANGUAGES: list[str] = ["en"]
_SFX_MAP: list = []


def set_sfx_languages(langs: list[str]) -> None:
    """Set active language packs for SFX detection. Rebuilds compiled patterns.

    Unknown codes are skipped silently. Example:
        set_sfx_languages(["en", "zh"]) — English first, then Chinese.
        set_sfx_languages(["es", "en"]) — Spanish first, English fallback.
    """
    global _SFX_LANGUAGES
    _SFX_LANGUAGES = [l.strip() for l in langs if l.strip()]
    _rebuild_sfx_map()


def available_languages() -> list[str]:
    """Return the sorted list of language codes we ship SFX packs for."""
    return sorted(_AVAILABLE_LANGS)


def _load_languages_from_env() -> None:
    """Read DND_SFX_LANGUAGES (comma-separated, e.g. 'en,zh') and apply.

    Falls back to English-only if unset or empty.
    """
    raw = os.environ.get("DND_SFX_LANGUAGES", "").strip()
    if not raw:
        return  # keep the English-only default
    requested = [l.strip() for l in raw.split(",") if l.strip()]
    valid = [l for l in requested if l in _AVAILABLE_LANGS]
    if valid:
        set_sfx_languages(valid)


# Build default (English-only) on import, then apply env override if set
_rebuild_sfx_map()
_load_languages_from_env()
