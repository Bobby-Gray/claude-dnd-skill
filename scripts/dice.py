#!/usr/bin/env python3
"""
dice.py — D&D 5e dice roller

Routes through the local 3D dice server (~/.dnd-dice/) when reachable so
rolls can be cast physically on the player's phone. Falls back to local
random when the server is down (and the server itself auto-rolls when no
phone is connected — so rolling never blocks).

Usage:
    python3 dice.py <notation> [--silent] [--label "..."] [--auto]

Notation supported:
    d20               single d20
    2d6               2 six-sided dice, sum
    d20+5             roll + flat modifier
    4d6kh3            roll 4d6, keep highest 3 (ability score generation)
    4d6kl3            roll 4d6, keep lowest 3
    d20 adv           advantage: roll twice, take higher  (→ 2d20kh1)
    d20 dis           disadvantage: roll twice, take lower (→ 2d20kl1)
    d20+3 adv         advantage with modifier
    2d6+3             multiple dice + modifier

Env vars:
    DND_DICE_PHYSICAL=1   opt in to physical-roll routing (default: 0, local-random).
                          Auto-enabled when ~/.dnd-dice/ exists (the install-launchd.sh
                          script creates this marker on setup).
    DND_DICE_PORT=7777    server port (default 7777)
    DND_DICE_LABEL=...    label shown on the phone for this roll
"""

import os
import random
import re
import sys
import json
import time
import urllib.request
import urllib.error


# --------------------------------------------------------------------------
# Local-random fallback (unchanged behavior from the original dice.py)
# --------------------------------------------------------------------------

def parse_notation(notation: str):
    notation = notation.strip().lower()
    adv = "adv" in notation or "advantage" in notation
    dis = "dis" in notation or "disadvantage" in notation
    notation = re.sub(r'\s*(adv|dis|advantage|disadvantage)\w*', '', notation).strip()

    pattern = r'^(\d*)d(\d+)(?:(kh|kl)(\d+))?([+-]\d+)?$'
    m = re.match(pattern, notation.replace(' ', ''))
    if not m:
        raise ValueError(f"Cannot parse dice notation: '{notation}'")

    num_dice = int(m.group(1)) if m.group(1) else 1
    die_size = int(m.group(2))
    keep_mode = m.group(3)
    keep_count = int(m.group(4)) if m.group(4) else None
    modifier = int(m.group(5)) if m.group(5) else 0
    return num_dice, die_size, modifier, keep_mode, keep_count, adv, dis


def roll_dice(num_dice, die_size):
    return [random.randint(1, die_size) for _ in range(num_dice)]


def format_modifier(mod):
    if mod == 0:
        return ""
    return f" + {mod}" if mod > 0 else f" - {abs(mod)}"


# --------------------------------------------------------------------------
# Physical-roll bridge to ~/.dnd-dice/ server
# --------------------------------------------------------------------------

_PORT = int(os.environ.get("DND_DICE_PORT", "7777"))
_BASE = f"http://localhost:{_PORT}"


def _server_alive(timeout=0.5) -> bool:
    try:
        with urllib.request.urlopen(_BASE + "/health", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def _post(path, payload, timeout=5):
    req = urllib.request.Request(
        _BASE + path,
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _get(path, timeout=5):
    with urllib.request.urlopen(_BASE + path, timeout=timeout) as r:
        return json.loads(r.read())


def physical_roll(spec: str, label: str = "", wait: float = 180.0, player: str = None):
    """Send a roll to the dice server; block until the result returns.

    Returns the server's result dict ({total, rolls, kept, modifier, spec, ...})
    or None if the server isn't reachable. `player` routes to that player's tab
    (None = DM channel).
    """
    if not _server_alive():
        return None
    payload = {"spec": spec, "label": label, "physical": True}
    if player:
        payload["player"] = player
    try:
        r = _post("/roll", payload)
    except Exception:
        return None

    if r.get("auto"):
        return r["result"]

    rid = r["id"]
    deadline = time.time() + wait
    while time.time() < deadline:
        try:
            res = _get(f"/result/{rid}")
        except Exception:
            time.sleep(0.5)
            continue
        if res.get("result") is not None:
            return res["result"]
        time.sleep(0.4)
    return None  # timed out — caller falls back to local


def _to_server_notation(num_dice: int, die_size: int, mod: int,
                         keep_mode: str, keep_count: int,
                         adv: bool, dis: bool):
    """Translate dice.py's notation into the server's notation.

    adv/dis become 2d{S}kh1 / 2d{S}kl1 (with the modifier appended).
    Returns None if the construct can't be expressed for the server (e.g.
    "2d6 adv" — adv over a sum of multiple dice — falls back to local).
    """
    if (adv or dis) and num_dice != 1:
        return None
    if adv:
        base = f"2d{die_size}kh1"
    elif dis:
        base = f"2d{die_size}kl1"
    elif keep_mode:
        base = f"{num_dice}d{die_size}{keep_mode}{keep_count}"
    else:
        base = f"{num_dice}d{die_size}"
    if mod > 0:
        base += f"+{mod}"
    elif mod < 0:
        base += f"{mod}"
    return base


# --------------------------------------------------------------------------
# Main run() — physical first, local fallback
# --------------------------------------------------------------------------

def run(notation: str, silent: bool = False, label: str = "",
        force_local: bool = False, player: str = None) -> int:
    num_dice, die_size, modifier, keep_mode, keep_count, adv, dis = parse_notation(notation)

    # Physical-roll routing is opt-in. Default behavior is local-random — the
    # original dice.py behavior. The server bridge is only engaged when one of:
    #   - env var DND_DICE_PHYSICAL=1 (explicit opt-in)
    #   - ~/.dnd-dice/ marker directory exists (auto-set by install-launchd.sh)
    # This way `dice.py` adds zero latency for users who haven't installed
    # the optional server.
    env_opt_in = os.environ.get("DND_DICE_PHYSICAL", "0") == "1"
    marker_opt_in = (os.path.expanduser("~/.dnd-dice") and
                     os.path.isdir(os.path.expanduser("~/.dnd-dice")))
    use_physical = not force_local and (env_opt_in or marker_opt_in)
    if use_physical:
        spec = _to_server_notation(num_dice, die_size, modifier, keep_mode, keep_count, adv, dis)
        if spec is not None:
            hud_label = label or os.environ.get("DND_DICE_LABEL", "") or notation.strip()
            target_player = player or os.environ.get("DND_DICE_PLAYER") or None
            result = physical_roll(spec, label=hud_label, player=target_player)
            if result is not None:
                _print_physical(result, num_dice, die_size, modifier, keep_mode, keep_count,
                                adv, dis, silent)
                return result["total"]
        # fall through to local fallback

    # ----- Local random fallback (original dice.py logic) -----
    if adv or dis:
        roll_a = roll_dice(num_dice, die_size)
        roll_b = roll_dice(num_dice, die_size)
        total_a = sum(roll_a) + modifier
        total_b = sum(roll_b) + modifier
        chosen = max(total_a, total_b) if adv else min(total_a, total_b)
        lbl = "ADV" if adv else "DIS"
        if not silent:
            print(f"[{lbl}] Roll A: {roll_a} = {total_a}{format_modifier(modifier)}")
            print(f"[{lbl}] Roll B: {roll_b} = {total_b}{format_modifier(modifier)}")
            taken = "A" if (adv and total_a >= total_b) or (dis and total_a <= total_b) else "B"
            print(f"Takes roll {taken} → Total: {chosen}")
        return chosen

    rolls = roll_dice(num_dice, die_size)

    if keep_mode and keep_count:
        sorted_rolls = sorted(rolls, reverse=(keep_mode == 'kh'))
        kept = sorted_rolls[:keep_count]
        dropped = sorted_rolls[keep_count:]
        result = sum(kept) + modifier
        if not silent:
            kept_str = " + ".join(str(r) for r in kept)
            drop_str = f"  (dropped: {dropped})" if dropped else ""
            print(f"Rolls: {rolls}{drop_str}")
            print(f"Kept ({keep_mode}{keep_count}): [{kept_str}]{format_modifier(modifier)} = {result}")
        return result

    result = sum(rolls) + modifier
    if not silent:
        if num_dice == 1 and die_size == 20:
            raw = rolls[0]
            flag = ""
            if raw == 20:
                flag = "  *** CRITICAL HIT (nat 20)! ***"
            elif raw == 1:
                flag = "  *** FUMBLE (nat 1)! ***"
            print(f"Roll: {raw}{format_modifier(modifier)} = {result}{flag}")
        else:
            print(f"Rolls: {rolls}{format_modifier(modifier)} = {result}")
    return result


def _print_physical(res: dict, num_dice: int, die_size: int, modifier: int,
                    keep_mode: str, keep_count: int, adv: bool, dis: bool, silent: bool):
    """Format the physical-roll result so its output matches the original dice.py
    conventions the skill expects to parse / display."""
    if silent:
        return
    rolls = res["rolls"]
    kept = res.get("kept", rolls)
    total = res["total"]
    auto_tag = " [auto]" if res.get("auto") else ""

    if adv or dis:
        lbl = "ADV" if adv else "DIS"
        a, b = rolls[0], rolls[1]
        ta = a + modifier
        tb = b + modifier
        taken = kept[0]
        print(f"[{lbl}]{auto_tag} Roll A: [{a}] = {ta}{format_modifier(modifier)}")
        print(f"[{lbl}]{auto_tag} Roll B: [{b}] = {tb}{format_modifier(modifier)}")
        which = "A" if a == taken and (adv and a >= b or dis and a <= b) else "B"
        print(f"Takes roll {which} → Total: {total}")
        return

    if keep_mode and keep_count:
        dropped = [r for r in rolls if r not in kept] if len(rolls) != len(kept) else []
        # rough dropped reconstruction — just whatever isn't in kept (in roll order)
        used = list(kept)
        dropped = []
        for r in rolls:
            if r in used:
                used.remove(r)
            else:
                dropped.append(r)
        kept_str = " + ".join(str(r) for r in kept)
        drop_str = f"  (dropped: {dropped})" if dropped else ""
        print(f"Rolls: {rolls}{drop_str}{auto_tag}")
        print(f"Kept ({keep_mode}{keep_count}): [{kept_str}]{format_modifier(modifier)} = {total}")
        return

    if num_dice == 1 and die_size == 20:
        raw = rolls[0]
        flag = ""
        if raw == 20:
            flag = "  *** CRITICAL HIT (nat 20)! ***"
        elif raw == 1:
            flag = "  *** FUMBLE (nat 1)! ***"
        print(f"Roll: {raw}{format_modifier(modifier)} = {total}{flag}{auto_tag}")
    else:
        print(f"Rolls: {rolls}{format_modifier(modifier)} = {total}{auto_tag}")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

if __name__ == "__main__":
    argv = sys.argv[1:]
    silent = "--silent" in argv
    auto = "--auto" in argv
    label = ""
    player = None
    # Extract --label and --player (each followed by a value)
    for flag in ("--label", "--player"):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 < len(argv):
                val = argv[i + 1]
                if flag == "--label":
                    label = val
                else:
                    player = val
                del argv[i:i + 2]
    args = [a for a in argv if a not in ("--silent", "--auto")]

    if not args:
        print("Usage: python3 dice.py <notation>  e.g. d20+5  2d6  4d6kh3  d20 adv")
        sys.exit(1)

    notation = " ".join(args)
    result = run(notation, silent=silent, label=label, force_local=auto, player=player)
    if silent:
        print(result)
