"""
app.py — DnD DM display server

Receives text chunks from wrapper.py, detects scene context from keywords,
and pushes both to the browser via Server-Sent Events.

Endpoints:
    GET  /                   → serves index.html
    POST /chunk              → receives text chunk from wrapper.py
    POST /stats              → receives character/combat stat updates (merged, persisted)
    GET  /stream             → SSE stream to browser (text + scene + stats events)
    GET  /ping               → health check
    POST /clear              → wipe text log and broadcast clear event
    POST /player-input         → legacy queue endpoint (check_input.py compat)
    POST /player-input/drain   → drain legacy queue (check_input.py compat)
    POST /player-input/stage   → stage an action for review before firing
    POST /player-input/ready   → mark a staged action as ready
    POST /player-input/unstage → remove a staged action
    POST /player-input/skip    → skip a character's turn (stages + readies a skip entry)
    GET  /srd-lookup           → look up a spell/item/feature/condition by name
"""

import hmac
import json
import os
import queue
import re
import secrets
import subprocess
import sys
import threading
from collections import deque
from typing import Optional
from flask import Flask, Response, request, render_template, jsonify
from flask_cors import CORS

LOG_FILE      = os.path.expanduser("~/.claude/skills/dnd/display/text_log.json")
SCRIPTS_DIR   = os.path.expanduser("~/.claude/skills/dnd/scripts")

# SRD lookup module — degrades silently if dataset not built
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
try:
    import lookup as _lookup
    _SRD_AVAILABLE = True
except Exception:
    _lookup = None          # type: ignore
    _SRD_AVAILABLE = False

# Audio module — degrades silently if numpy not installed
_AUDIO_DIR = os.path.dirname(os.path.abspath(__file__))
import sys as _sys
if _AUDIO_DIR not in _sys.path:
    _sys.path.insert(0, _AUDIO_DIR)
try:
    import audio as _audio
    _audio.init()
except Exception:
    _audio = None   # type: ignore
HELP_LOCK     = os.path.expanduser("~/.claude/skills/dnd/display/.help-lock")
CAMP_FILE     = os.path.expanduser("~/.claude/skills/dnd/display/.campaign")
STATS_FILE    = os.path.expanduser("~/.claude/skills/dnd/display/stats.json")
TOKEN_FILE    = os.path.expanduser("~/.claude/skills/dnd/display/.token")
INPUT_FILE    = os.path.expanduser("~/.claude/skills/dnd/display/player_input.json")
TRIGGER_FILE  = os.path.expanduser("~/.claude/skills/dnd/display/.input_trigger")
QUEUE_FILE    = os.path.expanduser("~/.claude/skills/dnd/display/.input_queue")

# ─── LAN mode ─────────────────────────────────────────────────────────────────
# Pass --lan to bind on 0.0.0.0 and protect write endpoints with a token.
# Without --lan the server binds to localhost only; no token is required.

_LAN_MODE: bool = "--lan" in sys.argv
if _LAN_MODE:
    sys.argv.remove("--lan")   # prevent Flask from seeing an unknown flag


def _get_or_create_token() -> str:
    """Load or generate the LAN token. Upgrades short legacy tokens to 64-char."""
    try:
        token = open(TOKEN_FILE).read().strip()
        if len(token) >= 48:   # 48+ chars = already long enough
            return token
    except FileNotFoundError:
        pass
    token = secrets.token_hex(32)   # 64-char hex — brute force infeasible
    with open(TOKEN_FILE, "w") as f:
        f.write(token)
    os.chmod(TOKEN_FILE, 0o600)
    return token


_lan_token: Optional[str] = _get_or_create_token() if _LAN_MODE else None


# ─── Rate limiting ────────────────────────────────────────────────────────────
# Simple in-process sliding window: max 20 write requests per IP per minute.
# Prevents spam injection and brute-force token guessing on write endpoints.

import time as _time

_rate_buckets: dict[str, list] = {}
_rate_lock = threading.Lock()
_RATE_WINDOW = 60    # seconds
_RATE_MAX    = 20    # requests per window per IP


def _rate_ok(ip: str) -> bool:
    now = _time.time()
    with _rate_lock:
        bucket = [t for t in _rate_buckets.get(ip, []) if now - t < _RATE_WINDOW]
        if len(bucket) >= _RATE_MAX:
            return False
        bucket.append(now)
        _rate_buckets[ip] = bucket
    return True


# ─── Input validation helpers ─────────────────────────────────────────────────

_PRINTABLE    = re.compile(r"[^\x20-\x7E]")
_SHELL_CHARS  = re.compile(r'[$`\\;|&><()\[\]{}!]')
_CHAR_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z '\-]{0,48}[A-Za-z]$|^[A-Za-z]$")


def _sanitize_input(text: str) -> str:
    """Strip control chars and shell metacharacters from player input text."""
    text = _SHELL_CHARS.sub("", text)
    text = _PRINTABLE.sub("", text)
    return text[:500].strip()


def _char_ok(name: str, known: set) -> bool:
    """Return True if character name is syntactically valid and in the party."""
    if not _CHAR_NAME_RE.match(name):
        return False
    if known and name not in known and name != "Everybody":
        return False
    return True


# ─── Device approval system ───────────────────────────────────────────────────
# Each browser generates a UUID device ID (localStorage). On first input attempt
# from an unseen LAN device, the request is held and the DM sees an Approve/Deny
# card on the display. Localhost is auto-approved. Denied devices are blocked for
# the session.

_approved_devices: set[str]       = set()
_denied_devices:   set[str]       = set()
_pending_devices:  dict[str, dict] = {}  # device_id -> {ip, first_seen}
_devices_lock = threading.Lock()


def _device_ok(device_id: str, ip: str) -> str:
    """Return 'approved', 'pending', or 'denied' for a given device."""
    if not device_id:
        return "denied"
    with _devices_lock:
        if device_id in _approved_devices:
            return "approved"
        if device_id in _denied_devices:
            return "denied"
        # Localhost always auto-approved
        if ip in ("127.0.0.1", "::1"):
            _approved_devices.add(device_id)
            return "approved"
        # New LAN device — hold and notify DM
        if device_id not in _pending_devices:
            _pending_devices[device_id] = {
                "id":         device_id,
                "ip":         ip,
                "first_seen": _time.time(),
            }
            _broadcast({"device_request": {"id": device_id, "ip": ip}})
        return "pending"


# ─── Staged input system ──────────────────────────────────────────────────────
# Players stage their actions from the display companion UI. When all expected
# players mark ready, the combined action is written to TRIGGER_FILE for
# wrapper.py to inject into Claude's PTY stdin.

_staged: dict[str, dict] = {}   # {char_name: {text, ready, timestamp}}
_staged_lock = threading.Lock()
_expected_count = 1             # updated when stats arrive; min 1
_autorun_threshold: Optional[int] = None  # overrides _expected_count when set via push_stats --autorun-threshold

# Tracks which character names are currently sitting in .input_queue waiting
# for the DM to press Enter. Set when queue is written, cleared when wrapper
# POSTs /queue/consumed after injection. Persists through page reloads via SSE
# initial data and is broadcast to all connected clients on change.
_queue_status: list = []
_queue_status_lock = threading.Lock()

# Last autorun cycle broadcast — replayed on SSE reconnect so late-joining
# clients start the countdown from the correct elapsed position.
# Cleared when autorun_waiting=false (turn resolved or autorun disabled).
_autorun_cycle: Optional[dict] = None
_autorun_cycle_lock = threading.Lock()


def _staged_snapshot() -> dict:
    """Return a serialisable copy of the staged dict (no IP field)."""
    return {k: {"text": v["text"], "ready": v["ready"]} for k, v in _staged.items()}


def _check_auto_trigger() -> None:
    """Move staged-and-ready actions into the DM-gated queue file (.input_queue).

    .input_queue is NOT injected immediately — wrapper.py picks it up the next
    time the DM presses Enter (or Claude explicitly triggers via .input_trigger).
    This gives the DM control over when player actions enter Claude's context.
    """
    with _staged_lock:
        if not _staged:
            return
        everybody_ready = "Everybody" in _staged and _staged["Everybody"]["ready"]
        all_ready       = all(v["ready"] for v in _staged.values())
        threshold       = _autorun_threshold if _autorun_threshold is not None else _expected_count
        enough          = len(_staged) >= threshold or everybody_ready
        if not (all_ready and enough):
            return
        char_names = list(_staged.keys())
        lines      = [f'[{c}]: {e["text"]}' for c, e in _staged.items()]
        content    = "\n".join(lines)
        _staged.clear()

    try:
        with open(QUEUE_FILE, "w") as f:
            f.write(content)
    except Exception:
        char_names = []

    if char_names:
        with _queue_status_lock:
            _queue_status.clear()
            _queue_status.extend(char_names)
    _broadcast({"staged_inputs": {}, "queue_status": list(char_names)})


def _token_ok() -> bool:
    """Return True if the request carries the correct LAN token (or we're in localhost mode)."""
    if _lan_token is None:
        return True   # localhost mode — no token required
    provided = request.headers.get("X-DND-Token", "")
    return hmac.compare_digest(provided, _lan_token)


app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
CORS(app)

# Wire audio broadcast after _broadcast is defined (see bottom of file)
# — done lazily via set_broadcast() called after app is created.

# ─── Scene definitions ────────────────────────────────────────────────────────
# Each scene: keywords (weighted — more = higher priority hit),
# gradient colors [top, bottom], accent color, particle type, display label.

SCENES: dict[str, dict] = {
    "tavern": {
        "keywords": [
            "tavern", "inn", "guttered", "common room", "hearth",
            "fireplace", "ale", "mead", "barkeep", "innkeeper",
            "candle", "tallow", "flagon", "stool", "bar",
        ],
        "colors": ["#1a0800", "#2e1400"],
        "accent": "#c8601a",
        "particles": "embers",
        "label": "The Inn",
    },
    "dungeon": {
        "keywords": [
            "dungeon", "corridor", "stone floor", "torch", "iron gate",
            "portcullis", "cell", "shackle", "pit", "dank",
        ],
        "colors": ["#080818", "#12082e"],
        "accent": "#6a3aaa",
        "particles": "dust",
        "label": "The Dungeon",
    },
    "mine": {
        "keywords": [
            "mine", "seam", "shaft", "tunnel", "ore", "pickaxe",
            "foreman", "deep seam", "ashstone", "cart", "vein",
        ],
        "colors": ["#0a0a0a", "#1a1008"],
        "accent": "#806040",
        "particles": "dust",
        "label": "The Mine",
    },
    "cave": {
        "keywords": [
            "cave", "cavern", "stalactite", "stalagmite", "underground",
            "grotto", "dripping", "echo", "subterranean",
        ],
        "colors": ["#0a1520", "#0a1030"],
        "accent": "#2060a0",
        "particles": "mist",
        "label": "The Cavern",
    },
    "forest": {
        "keywords": [
            "forest", "wood", "tree", "branch", "leaves", "undergrowth",
            "hollow wood", "canopy", "root", "bark", "moss", "fern",
            "thicket", "grove",
        ],
        "colors": ["#041008", "#081a04"],
        "accent": "#40a040",
        "particles": "leaves",
        "label": "The Forest",
    },
    "castle": {
        "keywords": [
            "castle", "rampart", "battlement", "keep", "parapet",
            "drawbridge", "moat", "throne", "great hall", "manor",
        ],
        "colors": ["#0e0e1a", "#1a1a2e"],
        "accent": "#8080c0",
        "particles": "dust",
        "label": "The Castle",
    },
    "mountain": {
        "keywords": [
            "mountain", "snow", "peak", "blizzard", "frost", "glacier",
            "avalanche", "ridge", "cliff", "altitude", "wind",
        ],
        "colors": ["#0a1020", "#1a2040"],
        "accent": "#a0c0e0",
        "particles": "snow",
        "label": "The Mountains",
    },
    "ocean": {
        "keywords": [
            "ocean", "sea", "ship", "wave", "sailor", "port", "harbour",
            "dock", "tide", "storm", "mast", "hull", "water",
        ],
        "colors": ["#000d1a", "#001a33"],
        "accent": "#0060a0",
        "particles": "ripples",
        "label": "The Sea",
    },
    "desert": {
        "keywords": [
            "desert", "sand", "dune", "oasis", "scorching", "arid",
            "mirage", "camel", "sphinx",
        ],
        "colors": ["#1a0f00", "#2e1a00"],
        "accent": "#c08030",
        "particles": "sand",
        "label": "The Desert",
    },
    "ruins": {
        "keywords": [
            "ruins", "ruin", "crumble", "crumbling", "rubble", "ancient",
            "overgrown", "collapsed", "forgotten", "desolate", "remnant",
        ],
        "colors": ["#100e04", "#1e1a08"],
        "accent": "#806830",
        "particles": "dust",
        "label": "The Ruins",
    },
    "swamp": {
        "keywords": [
            "swamp", "marsh", "bog", "mud", "murky", "fetid", "reed",
            "mire", "sludge", "stagnant",
        ],
        "colors": ["#080e04", "#0e1808"],
        "accent": "#406020",
        "particles": "mist",
        "label": "The Swamp",
    },
    "crypt": {
        "keywords": [
            "crypt", "tomb", "grave", "coffin", "undead", "bones",
            "skeleton", "lich", "mausoleum", "burial", "sarcophagus",
            "dead", "death",
        ],
        "colors": ["#08000a", "#140014"],
        "accent": "#602060",
        "particles": "smoke",
        "label": "The Crypt",
    },
    "fire": {
        "keywords": [
            "fire", "flame", "burn", "blaze", "inferno", "conflagration",
            "ember", "char", "smoke", "ash cloud",
        ],
        "colors": ["#1a0500", "#2e0800"],
        "accent": "#ff4400",
        "particles": "embers",
        "label": "The Fire",
    },
    "arcane": {
        "keywords": [
            "arcane", "magic", "spell", "enchant", "rune", "glyph",
            "mystical", "ritual", "incantation", "ward", "sigil",
            "thaumaturgy", "sorcery",
        ],
        "colors": ["#080020", "#12003a"],
        "accent": "#8040ff",
        "particles": "sparks",
        "label": "The Arcane",
    },
    "city": {
        "keywords": [
            "city", "market", "street", "crowd", "village", "town",
            "square", "cobble", "district", "quarter", "merchant",
            "ashenveil",
        ],
        "colors": ["#0a0f1a", "#15202e"],
        "accent": "#6080a0",
        "particles": "rain",
        "label": "The Town",
    },
    "night": {
        "keywords": [
            "night", "midnight", "moon", "star", "dark sky",
            "constellation", "celestial", "dusk", "twilight",
        ],
        "colors": ["#000008", "#04000f"],
        "accent": "#4060a0",
        "particles": "stars",
        "label": "The Night",
    },
    "temple": {
        "keywords": [
            "temple", "shrine", "altar", "holy", "sacred", "chapel",
            "prayer", "cleric", "incense", "lantern", "pew", "nave",
            "pale flame",
        ],
        "colors": ["#0e0c18", "#1a1428"],
        "accent": "#c0a060",
        "particles": "smoke",
        "label": "The Temple",
    },
}

# Priority order — checked in sequence; first match wins per chunk
SCENE_PRIORITY = [
    "mine", "crypt", "arcane", "fire", "temple", "dungeon", "cave",
    "forest", "swamp", "castle", "ocean", "mountain", "desert", "ruins",
    "tavern", "city", "night",
]

# ─── ANSI / TUI chrome stripping ─────────────────────────────────────────────

class _ANSIState:
    """Character-by-character ANSI escape-sequence state machine.

    Regex approaches fail when the PTY delivers bytes one at a time, splitting
    sequences like \\x1b[4;2m across chunk boundaries.  This state machine
    carries its state across calls so cross-chunk splits are handled correctly.

    States
    ------
    normal   → emitting regular characters
    esc      → saw ESC (0x1B), waiting to see what kind of sequence follows
    csi      → inside CSI sequence (ESC [ … letter)
    osc      → inside OSC sequence (ESC ] … BEL or ST)
    osc_esc  → inside OSC, just saw ESC — might be the ST terminator (ESC \\)
    """

    __slots__ = ("_s",)

    def __init__(self) -> None:
        self._s: str = "normal"

    def feed(self, text: str) -> str:
        out: list[str] = []
        s = self._s
        for ch in text:
            c = ord(ch)
            if s == "normal":
                if c == 0x1B:
                    s = "esc"
                elif c >= 0x20 or c in (0x09, 0x0A):   # printable / tab / newline
                    out.append(ch)
                # else: other control char (bell, etc.) — discard
            elif s == "esc":
                if ch == "[":
                    s = "csi"
                elif ch == "]":
                    s = "osc"
                else:
                    s = "normal"    # 2-char ESC sequence; discard both bytes
            elif s == "csi":
                if 0x40 <= c <= 0x7E:   # final byte of CSI
                    s = "normal"
                elif c == 0x1B:         # unexpected ESC — start fresh
                    s = "esc"
                # else: parameter / intermediate byte, keep consuming
            elif s == "osc":
                if c == 0x07:           # BEL terminates OSC
                    s = "normal"
                elif c == 0x1B:
                    s = "osc_esc"
                # else: OSC payload, keep consuming
            elif s == "osc_esc":
                s = "normal" if ch == "\\" else "osc"
        self._s = s
        return "".join(out)


_ansi = _ANSIState()
_ansi_lock = threading.Lock()

_BOX_CHARS = set("╭╮╰╯│─┌┐└┘├┤┬┴┼━═║╔╗╚╝")
_BOX_CHAR_STRIP = "╭╮╰╯│─┌┐└┘├┤┬┴┼━═║╔╗╚╝"  # same set as string for str.strip()

# Characters used by Claude CLI spinner / prompt / UI
_SPINNER_CHARS = set("✽⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏◐◓◑◒◌◎●")
_PROMPT_STARTS = ("❯", ">", "·", "▸", "ℹ", "✓", "⚠", "✗", "⟳", "↳")


def _handle_cr(text: str) -> str:
    """Handle carriage returns the way a real terminal would.

    Two distinct cases:
      \\r\\n  — a real newline (\\r\\n line ending).  Normalise to \\n first
                so the content is preserved.
      bare \\r — cursor-to-column-0 for in-place token updates.  Claude CLI
                streams each token by rewriting the current line:
                  "The" → \\r"The Gut" → \\r"The Gutte" → …
                Keep only the last segment (= the final written state).
    """
    # Step 1: treat \\r\\n as a real newline — must come before bare-\\r logic
    text = text.replace("\r\n", "\n")

    # Step 2: handle remaining bare \\r (in-place rewrites)
    lines = text.split("\n")
    result = []
    for line in lines:
        if "\r" in line:
            parts = line.split("\r")
            result.append(parts[-1])   # last segment = final state of the line
        else:
            result.append(line)
    return "\n".join(result)


def _strip_ansi(text: str) -> str:
    text = _handle_cr(text)
    with _ansi_lock:
        text = _ansi.feed(text)
    return text


def _is_chrome(line: str) -> bool:
    """Return True for lines that are TUI chrome, not DM narration.

    The Claude CLI wraps responses in a box:
        ╭──────────────────╮
        │ narration text   │
        ╰──────────────────╯
    We strip the border characters from line edges first so that content
    lines like "│ The tavern smells of ale │" are NOT filtered — only pure
    border rows (all box chars, no letters) are treated as chrome.
    """
    stripped = line.strip()

    if not stripped:
        return False   # keep blank lines — they separate paragraphs

    # Strip leading/trailing box-drawing border chars to expose the real content.
    # "│ The tavern smells of ale │" → "The tavern smells of ale"
    content = stripped.strip(_BOX_CHAR_STRIP + " ")

    # If nothing remains, the line was entirely box-drawing chrome (a border row).
    if not content:
        return True

    # All remaining checks operate on content (without box border decoration).
    c = content

    # CLI prompt / spinner lines
    if c[0] in _SPINNER_CHARS:
        return True
    if c.startswith(_PROMPT_STARTS):
        return True

    # Common spinner word patterns (e.g. "Thinking…")
    if re.match(r"^[A-Z][a-z]+ing…?$", c):
        return True

    # Claude branding / metadata
    if "claude.ai" in c.lower():
        return True

    # Session-resume instructions emitted at end of response
    if c.startswith("Resume this session with:") or re.match(r"^claude\s+--resume\s+", c):
        return True

    # Status-bar patterns: cost, token counts, rate-limit bars
    # Note: "Tokens300/0" has no space — use \s* not \s+
    if re.search(r"Tokens\s*\d|5hr:|7d:|Session:|Total:\s*\$", c):
        return True

    # Model/plan header lines ("Sonnet 4.6", "Claude Pro", "Professional", etc.)
    if re.search(r"Sonnet|Haiku|Opus|Claude\s*(Pro|Max|Team|Code)\b|Professional\b|claude-\d", c, re.I):
        return True

    # Tool-use labels emitted by Claude CLI ("Bash command", "Read command", etc.)
    if re.match(r"^(Bash|Read|Write|Edit|Glob|Grep|WebFetch|WebSearch|TaskCreate|TaskUpdate|TaskGet|TaskList|NotebookEdit|Agent|ToolSearch|ExitPlanMode|EnterPlanMode|ScheduleWakeup|Monitor|RemoteTrigger|CronCreate|CronDelete|CronList|AskUserQuestion)(\s+(command|tool|result|call))?$", c, re.I):
        return True

    # Timestamp-prefixed lines ("3ts ago …", "2m ago …") — UI timestamps concatenated with content
    if re.match(r"^\d+\s*[smhdt]+s?\s*(ago\s*)?[A-Z]", c):
        return True

    # Bare numbers (token counts, cursor column positions, etc.)
    if re.match(r"^\d+$", c):
        return True

    # Single stray characters that are ANSI/escape remnants, not real words
    if len(c) == 1 and not c.isalpha():
        return True

    # Very short non-alpha fragments (≤3 chars with no letters = not narration)
    if len(c) <= 3 and not re.search(r"[a-zA-Z]{2}", c):
        return True

    return False


def _clean(text: str) -> str:
    text = _strip_ansi(text)
    lines = text.split("\n")
    kept = []
    for line in lines:
        if _is_chrome(line):
            continue
        # Strip box-border chars from edges so content reaches the browser clean.
        s = line.strip().strip(_BOX_CHAR_STRIP + " ")
        # Blank line → preserve as paragraph separator
        kept.append(s if s else "")
    # Collapse runs of more than two consecutive blank lines
    result = re.sub(r"\n{3,}", "\n\n", "\n".join(kept))
    return result


# ─── Scene detection ──────────────────────────────────────────────────────────

_current_scene_name: str = "tavern"   # default — we start in the inn
_scene_buffer: list[str] = []
_BUFFER_WINDOW = 20   # analyse last N cleaned chunks together


def _detect_scene(text: str) -> Optional[dict]:
    global _current_scene_name, _scene_buffer

    _scene_buffer.append(text.lower())
    if len(_scene_buffer) > _BUFFER_WINDOW:
        _scene_buffer.pop(0)

    window = " ".join(_scene_buffer)

    scores: dict[str, int] = {}
    for scene_name in SCENE_PRIORITY:
        scene = SCENES[scene_name]
        score = sum(window.count(kw) for kw in scene["keywords"])
        if score > 0:
            scores[scene_name] = score

    if not scores:
        return None

    best = max(scores, key=lambda k: scores[k])
    if best == _current_scene_name:
        return None   # no change

    _current_scene_name = best
    return SCENES[best] | {"name": best}


# ─── SSE client registry ─────────────────────────────────────────────────────

_clients: list[queue.Queue] = []
_clients_lock = threading.Lock()

# ─── Text replay log ──────────────────────────────────────────────────────────
# Stores the last N cleaned text chunks so late-connecting browsers can catch up.
# Persisted to LOG_FILE so it survives Flask restarts (Chromecast reconnects, new sessions).
_text_log: deque = deque(maxlen=60)
_text_log_lock = threading.Lock()


def _persist_log() -> None:
    """Write the current text log to disk. Called after every chunk."""
    try:
        with _text_log_lock:
            data = list(_text_log)
        with open(LOG_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _load_log() -> None:
    """Load a previously persisted text log on startup.
    Handles both old string format and new dict format."""
    try:
        with open(LOG_FILE) as f:
            data = json.load(f)
        with _text_log_lock:
            _text_log.clear()
            for item in data[-60:]:
                # Migrate old plain-string entries to dict format
                if isinstance(item, str):
                    item = {"text": item}
                _text_log.append(item)
    except Exception:
        pass


_load_log()


# ─── Character / combat stats ─────────────────────────────────────────────────
# Stored as {"players": [...], "turn_order": {...}|null}
# Players are merged by name so partial updates (just HP, just XP) work.

_current_stats: dict = {}
_stats_lock = threading.Lock()


def _persist_stats() -> None:
    try:
        with _stats_lock:
            data = dict(_current_stats)
        with open(STATS_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _load_stats() -> None:
    try:
        with open(STATS_FILE) as f:
            data = json.load(f)
        with _stats_lock:
            _current_stats.update(data)
    except Exception:
        pass


_load_stats()


# ─── Player input queue ───────────────────────────────────────────────────────
# Stores actions submitted from the display companion (iPad etc.) until the DM
# triggers the next turn. Drained by check_input.py via /player-input/drain.

_input_queue: list[dict] = []
_input_lock = threading.Lock()


def _load_input_queue() -> None:
    global _input_queue
    try:
        with open(INPUT_FILE) as f:
            _input_queue = json.load(f)
    except Exception:
        _input_queue = []


def _persist_input_queue() -> None:
    try:
        with open(INPUT_FILE, "w") as f:
            json.dump(_input_queue, f)
    except Exception:
        pass


_load_input_queue()


def _broadcast(payload: dict) -> None:
    with _clients_lock:
        dead = []
        for q in _clients:
            try:
                q.put_nowait(payload)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _clients.remove(q)


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    # Pass LAN token to template so the browser can authenticate /help-request
    return render_template("index.html", lan_token=_lan_token or "")


@app.route("/srd-lookup")
def srd_lookup():
    """Look up a spell, item, condition, feature, or monster by name.

    Query params:
        name      — the name to look up (required)
        category  — spell | item | equipment | magic_item | condition | monster | feature (optional)
        level     — character level (1–20); collapses scale progressions to the matching entry

    Returns JSON: {"found": bool, "name": str, "category": str, "text": str}
    """
    name     = request.args.get("name", "").strip()[:120]
    category = request.args.get("category", "").strip().lower() or None
    level_s  = request.args.get("level", "").strip()
    level    = int(level_s) if level_s.isdigit() and 1 <= int(level_s) <= 20 else None
    if not name:
        return jsonify({"found": False, "error": "name required"}), 400
    if not _SRD_AVAILABLE or _lookup is None:
        return jsonify({"found": False, "error": "SRD dataset not loaded"}), 503

    text = _lookup.lookup_with_level(name, category=category, level=level)
    if text:
        rec = _lookup.lookup_record(name, category=category)
        resolved_cat = (rec or {}).get("_cat", category or "")
        return jsonify({"found": True, "name": name, "category": resolved_cat, "text": text})
    # Not found — return wikidot fallback URL so the frontend can offer a link
    wurl = _lookup.wikidot_url(name, category=category)
    return jsonify({"found": False, "name": name, "wikidot_url": wurl})


@app.route("/ping")
def ping():
    return "ok", 200


@app.route("/chunk", methods=["POST"])
def chunk():
    if not _token_ok():
        return "Forbidden", 403
    data = request.get_json(silent=True) or {}
    raw = data.get("text", "")
    if not raw:
        return "", 204

    is_action = bool(data.get("action"))
    is_player = bool(data.get("player"))
    is_npc    = bool(data.get("npc"))
    is_dice   = bool(data.get("dice"))
    is_tutor  = bool(data.get("tutor"))

    # Player/npc/dice/tutor/action text comes from send.py (no ANSI/chrome) — light clean only.
    # DM narration may come from wrapper.py — full clean.
    cleaned = raw.strip() if (is_action or is_player or is_npc or is_dice or is_tutor) else _clean(raw)
    if not cleaned.strip():
        return "", 204

    payload: dict = {"text": cleaned}

    if is_action:
        payload["action"] = data["action"]
    elif is_player:
        payload["player"] = data["player"]
    elif is_npc:
        payload["npc"] = data["npc"]
    elif is_dice:
        payload["dice"] = True
    elif is_tutor:
        payload["tutor"] = True
    else:
        # Scene detection only on DM narration
        scene = _detect_scene(cleaned)
        if scene:
            payload["scene"] = scene
            if _audio:
                _audio.on_scene_change(scene["name"])
        # SFX scan on all non-player text
        if _audio:
            _audio.on_text(cleaned)

    # Store full typed payload so replay preserves action/player/npc/dice/tutor context
    log_entry: dict = {"text": cleaned}
    if is_action:
        log_entry["action"] = data["action"]
    elif is_player:
        log_entry["player"] = data["player"]
    elif is_npc:
        log_entry["npc"] = data["npc"]
    elif is_dice:
        log_entry["dice"] = True
    elif is_tutor:
        log_entry["tutor"] = True

    with _text_log_lock:
        _text_log.append(log_entry)

    _persist_log()
    _broadcast(payload)
    return "", 204


@app.route("/stats", methods=["POST"])
def stats():
    """Receive character/combat stat updates. Merges players by name, replaces turn_order.

    Pass replace_players=true to replace the entire player list (use on /dnd load to
    prevent stale characters from a previous campaign persisting in the sidebar).
    """
    if not _token_ok():
        return "Forbidden", 403
    data = request.get_json(silent=True) or {}
    if not data:
        return "", 204

    with _stats_lock:
        if "players" in data:
            # replace_players=true wipes the list first — used on campaign load
            if data.get("replace_players"):
                _current_stats["players"] = []
            existing_players: list = _current_stats.setdefault("players", [])
            for incoming in data["players"]:
                name = incoming.get("name")
                if not name:
                    continue
                match = next((p for p in existing_players if p.get("name") == name), None)
                # Keys prefixed with _ are mutation ops, not stored fields
                _MUTATION_KEYS = {
                    "_inventory_add", "_inventory_remove",
                    "_conditions_add", "_conditions_remove",
                    "_slot_use", "_slot_restore",
                    "_hd_use", "_hd_restore",
                }
                if match:
                    for key, val in incoming.items():
                        if key == "_inventory_add":
                            inv = match.setdefault("sheet", {}).setdefault("inventory", [])
                            if val not in inv:
                                inv.append(val)
                        elif key == "_inventory_remove":
                            sheet = match.get("sheet", {})
                            sheet["inventory"] = [
                                i for i in sheet.get("inventory", [])
                                if i.lower() != str(val).lower()
                            ]
                        elif key == "_conditions_add":
                            conds = match.setdefault("conditions", [])
                            if val not in conds:
                                conds.append(val)
                        elif key == "_conditions_remove":
                            match["conditions"] = [
                                c for c in match.get("conditions", [])
                                if c.lower() != str(val).lower()
                            ]
                        elif key == "_slot_use":
                            slots = match.setdefault("spell_slots", {})
                            lvl = str(val)
                            slot = slots.setdefault(lvl, {"used": 0, "max": 0})
                            slot["used"] = min(slot["used"] + 1, slot.get("max", 99))
                        elif key == "_slot_restore":
                            slots = match.setdefault("spell_slots", {})
                            lvl = str(val)
                            slot = slots.setdefault(lvl, {"used": 0, "max": 0})
                            slot["used"] = max(slot["used"] - 1, 0)
                        elif key == "_hd_use":
                            hd = match.setdefault("hit_dice", {"remaining": 0, "max": 0})
                            hd["remaining"] = max(hd.get("remaining", 0) - 1, 0)
                        elif key == "_hd_restore":
                            hd = match.setdefault("hit_dice", {"remaining": 0, "max": 0})
                            hd["remaining"] = min(
                                hd.get("remaining", 0) + int(val),
                                hd.get("max", 99)
                            )
                        elif isinstance(val, dict) and isinstance(match.get(key), dict):
                            match[key].update(val)
                        else:
                            match[key] = val
                else:
                    # Strip mutation ops — they're meaningless for new players
                    existing_players.append(
                        {k: v for k, v in incoming.items() if k not in _MUTATION_KEYS}
                    )

        # turn_order replaces entirely (None = clear)
        if "turn_order" in data:
            _current_stats["turn_order"] = data["turn_order"]

        # world_time replaces entirely
        if "world_time" in data:
            _current_stats["world_time"] = data["world_time"]

        # factions replaces entirely ([] clears)
        if "factions" in data:
            _current_stats["factions"] = data["factions"]

        current = dict(_current_stats)

    # autorun_waiting / autorun_cycle — display-only signals, not stored in stats
    if "autorun_waiting" in data:
        if not data["autorun_waiting"]:
            # Turn resolved — clear stored cycle so reconnecting clients don't see stale pie
            global _autorun_cycle
            with _autorun_cycle_lock:
                _autorun_cycle = None
        _broadcast({"autorun_waiting": bool(data["autorun_waiting"])})
        if not any(k in data for k in ("players", "turn_order", "world_time", "factions",
                                        "replace_players", "sheet", "autorun_cycle")):
            return "", 204

    if "autorun_cycle" in data:
        with _autorun_cycle_lock:
            _autorun_cycle = data["autorun_cycle"]
        _broadcast({"autorun_cycle": data["autorun_cycle"]})
        if not any(k in data for k in ("players", "turn_order", "world_time", "factions",
                                        "replace_players", "sheet", "autorun_threshold")):
            return "", 204

    if "autorun_threshold" in data:
        global _autorun_threshold
        val = data["autorun_threshold"]
        _autorun_threshold = int(val) if val is not None else None
        _broadcast({"autorun_threshold": _autorun_threshold})
        if not any(k in data for k in ("players", "turn_order", "world_time", "factions",
                                        "replace_players", "sheet")):
            return "", 204

    _persist_stats()
    _broadcast({"stats": current})

    # Update expected player count for staged-input auto-trigger
    global _expected_count
    with _stats_lock:
        players = _current_stats.get("players", [])
    _expected_count = max(1, len(players))

    return "", 204


@app.route("/audio-toggle", methods=["POST"])
def audio_toggle():
    """Enable/disable ambient or SFX from the browser toggle switches.

    Body: {"ambient": true|false, "sfx": true|false}  (either or both keys)
    Response: {"ambient": bool, "sfx": bool, "available": bool}
    Broadcasts audio_state to all connected browsers so every device syncs.
    """
    data = request.get_json(silent=True) or {}
    if _audio:
        if "sfx" in data:
            _audio.set_sfx(bool(data["sfx"]))
        state = _audio.get_state()
    else:
        state = {"sfx": False, "available": False}
    return state, 200


@app.route("/audio/sfx/<name>")
def audio_sfx(name):
    """Serve a synthesized SFX WAV for the given effect name."""
    if not _audio:
        return "Audio not available", 503
    wav = _audio.get_sfx_wav(name)
    if wav is None:
        return "Not found", 404
    return Response(wav, mimetype="audio/wav",
                    headers={"Cache-Control": "public, max-age=3600"})


@app.route("/clear", methods=["POST"])
def clear():
    """Wipe text log AND stats, broadcast clear to all connected browsers.

    Called on /dnd new (fresh campaign). Ensures sidebar shows no stale characters.
    """
    if not _token_ok():
        return "Forbidden", 403
    global _scene_buffer, _current_stats
    with _text_log_lock:
        _text_log.clear()
    with _stats_lock:
        _current_stats = {}
    _scene_buffer = []
    for path in (LOG_FILE, STATS_FILE):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    _broadcast({"clear": True})
    return "", 204


@app.route("/help-request", methods=["POST"])
def help_request():
    """Spawn dm_help.py to generate and send an on-demand DM hint.

    Protected by an O_EXCL lock file — concurrent requests return 409
    so multiple players clicking the button never duplicates execution.
    Lock is released by dm_help.py in its finally block.
    """
    if not _token_ok():
        return "Forbidden", 403

    # Atomic lock: O_EXCL fails if file already exists — no race condition
    try:
        fd = os.open(HELP_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except FileExistsError:
        return "Already running", 409

    # Read active campaign name
    try:
        campaign = open(CAMP_FILE).read().strip()
    except FileNotFoundError:
        os.unlink(HELP_LOCK)
        return "No active campaign", 400

    if not campaign:
        os.unlink(HELP_LOCK)
        return "No active campaign", 400

    dm_help_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dm_help.py")
    subprocess.Popen(
        [sys.executable, dm_help_py, "--campaign", campaign],
        close_fds=True,
        start_new_session=True,
    )
    return "", 202


@app.route("/player-input", methods=["POST"])
def player_input():
    """Queue a player action submitted from the display companion.

    Body: {"character": "Kat", "text": "I draw my rapier", "hold": false}
    Broadcasts pending_input event to all connected browsers.
    """
    if not _token_ok():
        return "Forbidden", 403

    import time
    data = request.get_json(force=True, silent=True) or {}
    character = str(data.get("character", "Party"))[:50]
    text = str(data.get("text", ""))[:500]
    hold = bool(data.get("hold", False))

    # Strip shell metacharacters — input is player dialogue/action, not commands
    text = re.sub(r"[`\\$]", "", text).strip()
    if not text:
        return "empty", 400

    entry = {
        "character": character,
        "text": text,
        "hold": hold,
        "timestamp": time.time(),
    }

    with _input_lock:
        _input_queue.append(entry)
        current = list(_input_queue)

    _persist_input_queue()
    _broadcast({"pending_input": current})
    return "", 204


@app.route("/device/approve", methods=["POST"])
def device_approve():
    """DM approves a pending device. Body: {"id": "<device_id>"}"""
    if not _token_ok():
        return "Forbidden", 403
    device_id = str((request.get_json(force=True, silent=True) or {}).get("id", ""))
    with _devices_lock:
        _pending_devices.pop(device_id, None)
        _approved_devices.add(device_id)
    _broadcast({"device_approved": device_id})
    return "", 204


@app.route("/device/deny", methods=["POST"])
def device_deny():
    """DM denies a pending device. Body: {"id": "<device_id>"}"""
    if not _token_ok():
        return "Forbidden", 403
    device_id = str((request.get_json(force=True, silent=True) or {}).get("id", ""))
    with _devices_lock:
        _pending_devices.pop(device_id, None)
        _denied_devices.add(device_id)
    _broadcast({"device_denied": device_id})
    return "", 204


@app.route("/player-input/stage", methods=["POST"])
def stage_input():
    """Stage a player action for review. Broadcasts staged_inputs to all displays.

    Body: {"character": "Kat", "text": "draws her rapier"}
    """
    if not _token_ok():
        return "Forbidden", 403
    if not _rate_ok(request.remote_addr):
        return "Too Many Requests", 429

    device_id = request.headers.get("X-DND-Device", "")
    status    = _device_ok(device_id, request.remote_addr)
    if status == "denied":
        return "Forbidden", 403
    if status == "pending":
        return jsonify({"status": "pending"}), 202

    data      = request.get_json(force=True, silent=True) or {}
    character = str(data.get("character", ""))[:50].strip()
    text      = _sanitize_input(str(data.get("text", "")))

    if not character or not text:
        return "Bad Request", 400

    with _stats_lock:
        known = {p["name"] for p in _current_stats.get("players", [])}
    if not _char_ok(character, known):
        return "Forbidden", 403

    with _staged_lock:
        _staged[character] = {
            "text":      text,
            "ready":     False,
            "timestamp": _time.time(),
        }
        snap = _staged_snapshot()

    _broadcast({"staged_inputs": snap})
    return "", 204


@app.route("/player-input/ready", methods=["POST"])
def ready_input():
    """Toggle the ready flag for a staged character.

    Body: {"character": "Kat", "ready": true}
    Triggers auto-fire when all expected players are ready.
    """
    if not _token_ok():
        return "Forbidden", 403
    if not _rate_ok(request.remote_addr):
        return "Too Many Requests", 429

    device_id = request.headers.get("X-DND-Device", "")
    status    = _device_ok(device_id, request.remote_addr)
    if status == "denied":
        return "Forbidden", 403
    if status == "pending":
        return jsonify({"status": "pending"}), 202

    data      = request.get_json(force=True, silent=True) or {}
    character = str(data.get("character", ""))[:50].strip()
    ready     = bool(data.get("ready", True))

    with _staged_lock:
        if character not in _staged:
            return "Not Found", 404
        _staged[character]["ready"] = ready
        snap = _staged_snapshot()

    _broadcast({"staged_inputs": snap})

    if ready:
        _check_auto_trigger()

    return "", 204


@app.route("/player-input/unstage", methods=["POST"])
def unstage_input():
    """Remove a character's staged action (e.g. player wants to edit it).

    Body: {"character": "Kat"}
    """
    if not _token_ok():
        return "Forbidden", 403

    device_id = request.headers.get("X-DND-Device", "")
    if _device_ok(device_id, request.remote_addr) != "approved":
        return "Forbidden", 403

    data      = request.get_json(force=True, silent=True) or {}
    character = str(data.get("character", ""))[:50].strip()

    with _staged_lock:
        _staged.pop(character, None)
        snap = _staged_snapshot()

    _broadcast({"staged_inputs": snap})
    return "", 204


@app.route("/player-input/skip", methods=["POST"])
def skip_input():
    """Skip a character's turn — stages a 'skips their turn' entry marked ready.

    Counts toward the auto-trigger threshold and fires auto-trigger if threshold met.
    Body: {"character": "Kat"}
    """
    if not _token_ok():
        return "Forbidden", 403

    device_id = request.headers.get("X-DND-Device", "")
    if _device_ok(device_id, request.remote_addr) != "approved":
        return "Forbidden", 403

    data      = request.get_json(force=True, silent=True) or {}
    character = str(data.get("character", ""))[:50].strip()
    if not character:
        return "Bad Request", 400

    with _stats_lock:
        known = {p["name"] for p in _current_stats.get("players", [])}
    if not _char_ok(character, known):
        return "Forbidden", 403

    with _staged_lock:
        _staged[character] = {
            "text":      "skips their turn",
            "ready":     True,
            "timestamp": _time.time(),
        }
        snap = _staged_snapshot()

    _broadcast({"staged_inputs": snap})
    _check_auto_trigger()
    return "", 204


@app.route("/queue/consumed", methods=["POST"])
def queue_consumed():
    """Called by wrapper.py after it injects .input_queue into the PTY.

    Clears the server-side queue_status and broadcasts to all clients so
    the 'Queued — fires on DM Enter' indicator disappears on every display.
    Token required (called from localhost by the wrapper, but checked for
    consistency).
    """
    if not _token_ok():
        return "Forbidden", 403
    with _queue_status_lock:
        _queue_status.clear()
    _broadcast({"queue_status": [], "dm_processing": True})
    return "", 204


@app.route("/player-input/submit-now", methods=["POST"])
def submit_now():
    """Promote .input_queue → .input_trigger for immediate injection.

    Called by the DM or Claude when they want to process queued player actions
    right now rather than waiting for the DM's next CLI Enter press.
    Token required (DM-only action).
    """
    if not _token_ok():
        return "Forbidden", 403
    try:
        content = open(QUEUE_FILE).read()
        os.unlink(QUEUE_FILE)
    except FileNotFoundError:
        return "No queue", 204
    except Exception:
        return "Error", 500
    try:
        with open(TRIGGER_FILE, "w") as f:
            f.write(content)
    except Exception:
        return "Error", 500
    return "", 204


@app.route("/player-input/drain", methods=["POST"])
def drain_player_input():
    """Read and clear the player input queue. Called by check_input.py at turn start.

    Returns the drained entries as JSON, then broadcasts pending_input: [] to
    clear the indicator on all connected displays.
    """
    if not _token_ok():
        return "Forbidden", 403

    with _input_lock:
        drained = list(_input_queue)
        _input_queue.clear()

    _persist_input_queue()
    _broadcast({"pending_input": []})
    return jsonify(drained), 200


@app.route("/stream")
def stream():
    q: queue.Queue = queue.Queue(maxsize=256)
    with _clients_lock:
        _clients.append(q)

    # Send the current scene immediately on connect so the browser
    # starts with the right background even mid-session.
    initial_scene = SCENES[_current_scene_name] | {"name": _current_scene_name}
    q.put_nowait({"scene": initial_scene})

    # Replay recent entries so late-connecting / reconnecting browsers catch up.
    # Sent as a typed batch so the browser can render each item (dm/player/dice) correctly.
    with _text_log_lock:
        recent = list(_text_log)
    if recent:
        q.put_nowait({"replay_batch": recent})

    # Send current stats so the sidebar is populated immediately on (re)connect.
    with _stats_lock:
        if _current_stats:
            q.put_nowait({"stats": dict(_current_stats)})

    # Send current input queue so the pending indicator is accurate on reconnect.
    with _input_lock:
        if _input_queue:
            q.put_nowait({"pending_input": list(_input_queue)})

    # Send current staged inputs so the panel reflects live state on reconnect.
    with _staged_lock:
        if _staged:
            q.put_nowait({"staged_inputs": _staged_snapshot()})

    # Send current queue status so the 'Queued' indicator survives page reload.
    with _queue_status_lock:
        if _queue_status:
            q.put_nowait({"queue_status": list(_queue_status)})

    # Replay autorun cycle so reconnecting clients resume the countdown from correct elapsed position.
    with _autorun_cycle_lock:
        if _autorun_cycle:
            q.put_nowait({"autorun_cycle": dict(_autorun_cycle)})

    # Replay threshold so the ready counter reflects the correct target on reconnect.
    if _autorun_threshold is not None:
        q.put_nowait({"autorun_threshold": _autorun_threshold})

    # Send any pending device approval requests so the DM sees them on reconnect.
    with _devices_lock:
        for dev in list(_pending_devices.values()):
            q.put_nowait({"device_request": {"id": dev["id"], "ip": dev["ip"]}})

    def generate():
        try:
            while True:
                try:
                    payload = q.get(timeout=5)
                    yield f"data: {json.dumps(payload)}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"   # prevent proxy timeout
        except GeneratorExit:
            with _clients_lock:
                try:
                    _clients.remove(q)
                except ValueError:
                    pass

    resp = Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
        },
    )
    # Force a single authoritative Connection header — Werkzeug otherwise
    # emits both keep-alive (ours) and close (its default), which confuses
    # transparent proxies (e.g. eero mesh routing) into buffering the stream.
    resp.headers["Connection"] = "keep-alive"
    return resp


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Wire audio SFX broadcast now that _broadcast is defined
    if _audio:
        _audio.set_broadcast(_broadcast)

    host = "0.0.0.0" if _LAN_MODE else "localhost"
    # TLS — use cert/key if present, otherwise plain HTTP
    _display_dir = os.path.dirname(os.path.abspath(__file__))
    _cert = os.path.join(_display_dir, "cert.pem")
    _key  = os.path.join(_display_dir, "key.pem")
    ssl_ctx = (_cert, _key) if os.path.exists(_cert) and os.path.exists(_key) else None
    scheme  = "https" if ssl_ctx else "http"

    if _LAN_MODE:
        print(f"DnD DM Display — LAN mode (0.0.0.0:5001) [{scheme.upper()}]")
        print(f"  Local:  {scheme}://localhost:5001")
        print("  Token stored at:", TOKEN_FILE)
        print("  POST endpoints require X-DND-Token header (send.py/push_stats.py handle this automatically)")
        if ssl_ctx:
            print("  TLS: self-signed cert — browser will warn, click through once")
        print()
    else:
        print(f"DnD DM Display — Flask server starting on {scheme}://localhost:5001")
        print(f"Open {scheme}://localhost:5001 in your browser, then Chromecast the tab.")
        print()
    app.run(host=host, port=5001, threaded=True, debug=False, ssl_context=ssl_ctx)
