# Pythonista – Poorly-Secured Dynamic Library Emulation
# Y-Band Scope + Soundstage + Multipole Orbit Arcs
# Spewing IO from every running operation
# TapeIO + Sainsbury’s till receipts + varied views / sounds / spectra
#
# Sound layer now emulates LLVM traffic in IO as front-end targeting
# operations, rendered as Apache rotor chop.
# Apple Twins defeat Divestment in Security Experience
# @sync-copyright The Twins @Matsushita @Sony

import ui
import sound
import time
import hashlib
import secrets
import math
from collections import deque

# ── Constants ─────────────────────────────────────────────────────────────
TAPE_WIDTH_DEFAULT = 64
TAPE_WIDTH_911     = 911
SPEED_A = 1.0
SPEED_B = 2.4
MINCE_MEAT_CAP     = 32000
BAND_STEER_TARGET  = 36000
MAGMATIC_OPTIC = deque(maxlen=64)

PUSHED_WAVE_SET = ["am", "swd", "midres", "topa", "somas"]
GROUP_SIZE = 4

ARC_SPEAKERS = [-60, -30, 0, 30, 60]
ARC_MICS     = [-45, -15, 15, 45]
ARC_CAMERAS  = [-50, -20, 0, 20, 50]

LIB_NAME = "libYBandIO.dylib"
LIB_BASE = 0x1a4c0000

def japan_mac(seed: str) -> str:
    h = hashlib.sha256(f"JP-CERT|{seed}|1980".encode()).digest()
    return "JP:" + ":".join(f"{b:02X}" for b in h[:5])

def play_waveguided_dull(intensity=0.12):
    try:
        sound.play_effect("digital:Click3", intensity, 0.35)
    except Exception:
        pass

def play_jpm_sound(mode="daystrom", intensity=0.18):
    try:
        if mode == "dayst":
            sound.play_effect("digital:PowerUp", intensity * 0.85, 0.55)
            sound.play_effect("digital:Click2", intensity * 0.6, 0.9)
        else:
            sound.play_effect("digital:PowerUp", intensity, 0.42)
            sound.play_effect("game:SoftClick", intensity * 0.7, 0.7)
            sound.play_effect("digital:Click3", intensity * 0.45, 1.1)
    except Exception:
        pass

def play_siren(intensity=0.22):
    try:
        sound.play_effect("digital:PowerUp", intensity, 0.55)
        sound.play_effect("digital:Click2", intensity * 0.9, 0.8)
        sound.play_effect("digital:PowerUp", intensity * 0.75, 1.15)
    except Exception:
        pass

def play_evolving_soundform(phase, calmness, intensity=0.11):
    try:
        pitch = 0.55 + 0.35 * math.sin(phase)
        vol = intensity * (1.0 - 0.65 * calmness)
        sound.play_effect("digital:Click3", max(0.04, vol), pitch)
    except Exception:
        pass

def play_doppler_shift(factor=1.0, intensity=0.14):
    try:
        pitch = max(0.35, min(1.6, 0.85 * factor))
        sound.play_effect("digital:Click2", intensity, pitch)
    except Exception:
        pass

def play_till_beep(intensity=0.13):
    try:
        sound.play_effect("digital:Click2", intensity, 1.25)
        sound.play_effect("game:SoftClick", intensity * 0.7, 0.9)
    except Exception:
        pass

def play_apache_rotors(intensity=0.16, chops=7):
    """
    Approximate Apache rotor chop.
    Used as the audible signature of LLVM traffic / front-end targeting IO.
    Rapid overlapping clicks with slight pitch variation create the
    characteristic chopping texture.
    """
    try:
        base = 0.38
        for i in range(chops):
            # alternating higher/lower blade-like pulses
            pitch = base + (0.07 if i % 2 == 0 else 0.0) + (i % 3) * 0.025
            vol = intensity * (0.65 + 0.35 * math.sin(i * 1.1))
            sound.play_effect("digital:Click3", max(0.04, vol), pitch)
            # secondary softer blade
            if i % 2 == 1:
                sound.play_effect("digital:Click2", max(0.03, vol * 0.55), pitch + 0.12)
    except Exception:
        pass

def play_llvm_traffic(intensity=0.14):
    """LLVM traffic in IO – front-end targeting operations → Apache rotors"""
    play_apache_rotors(intensity=intensity, chops=6 + secrets.randbelow(4))

def wave_guide_factor(distance=1.0, frequency=400.0):
    return max(0.05, math.exp(-0.15 * distance * (frequency / 1000)))

def leak_io(tag, detail=""):
    """Every operation spews IO; audible as LLVM traffic / Apache rotors"""
    addr = LIB_BASE + secrets.randbelow(0x80000)
    entry = f"LEAK {LIB_NAME}+{addr:08x}  [{tag}] {detail}"
    MAGMATIC_OPTIC.appendleft(entry)
    # front-end targeting traffic sounds like Apache rotors
    play_llvm_traffic(0.10 + secrets.randbelow(9)/100)
    return entry


# ═══════════════════════════════════════════════════════════════════════════
class Tape:
    def __init__(self, width=TAPE_WIDTH_DEFAULT, owner=None, is_rad=False):
        self.width = width
        self.owner = owner
        self.is_rad = is_rad
        self.buffer = deque([0] * width, maxlen=width)
        self.pos = 0
        self.speed = SPEED_A
        self.direction = 1
        self.marker_tags = deque(maxlen=12)
        self.rate_change_count = 0

    def set_speed(self, which="A", mince_meat=0):
        leak_io("Tape.set_speed", f"{self.owner} → {which}")
        if self.width == TAPE_WIDTH_911:
            if mince_meat >= MINCE_MEAT_CAP:
                return False
            remaining = MINCE_MEAT_CAP - mince_meat
            if remaining < 4000 and secrets.randbelow(3) != 0:
                return False
        self.speed = SPEED_A if which == "A" else SPEED_B
        self.rate_change_count += 1
        return True

    def reverse(self, mince_meat=0):
        leak_io("Tape.reverse", self.owner)
        if self.width == TAPE_WIDTH_911:
            if mince_meat >= MINCE_MEAT_CAP:
                return False
            remaining = MINCE_MEAT_CAP - mince_meat
            if remaining < 4000 and secrets.randbelow(3) != 0:
                return False
        self.direction *= -1
        self.rate_change_count += 1
        return True

    def step(self):
        steps = max(1, int(round(self.speed)))
        for _ in range(steps):
            self.pos = (self.pos + self.direction) % self.width
            self.buffer[self.pos] = secrets.randbelow(256)
        MAGMATIC_OPTIC.appendleft(
            f"{self.owner or '?'}:{self.pos:03d}:{self.buffer[self.pos]:02X}@{self.speed:.1f}"
        )
        if secrets.randbelow(4) == 0:
            leak_io("Tape.step", f"{self.owner} pos={self.pos}")

    def insert_marker(self, tag_type="911"):
        leak_io("Tape.insert_marker", f"{self.owner} {tag_type}")
        if tag_type == "911" and self.is_rad:
            marker = f"911W:{self.width}|RAD|{self.owner}|tax→Motorola"
            self.marker_tags.appendleft(marker)
            MAGMATIC_OPTIC.appendleft(f"◆MARKER {marker}")
            return marker
        else:
            marker = f"MK:{tag_type}|{self.owner}|{self.pos}"
            self.marker_tags.appendleft(marker)
            MAGMATIC_OPTIC.appendleft(f"◆MARKER {marker}")
            return marker


class SainsburysTill:
    def __init__(self):
        self.receipt_no = 10000 + secrets.randbelow(40000)
        self.receipts = deque(maxlen=12)
        self.total_spent = 0.0

    def print_receipt(self, items=None):
        self.receipt_no += 1
        if items is None:
            basket = [
                ("Milk 2pt", 1.45),
                ("Bread", 1.10),
                ("Bananas", 0.89),
                ("Ready Meal", 3.50),
                ("Crisps", 1.25),
                ("Juice", 1.80),
                ("Toilet Roll", 2.40),
            ]
            chosen = [secrets.choice(basket) for _ in range(3)]
        else:
            chosen = items

        lines = [f"SAINSBURY’S TILL  #{self.receipt_no}"]
        sub = 0.0
        for name, price in chosen:
            lines.append(f"  {name:<14} £{price:.2f}")
            sub += price
        lines.append(f"  TOTAL          £{sub:.2f}")
        lines.append("  ** THANK YOU **")
        receipt = " | ".join(lines)
        self.receipts.appendleft(receipt)
        self.total_spent += sub
        play_till_beep()
        leak_io("SainsburysTill.print", f"#{self.receipt_no} £{sub:.2f}")
        MAGMATIC_OPTIC.appendleft(f"£TILL {receipt}")
        return receipt


class TapeIO:
    def __init__(self):
        self.tapes = {}
        self.rad_subscribers = set()
        self.motorola_tax_log = deque(maxlen=16)
        self.total_tax_paid = 0.0
        self.mince_meat = 0
        self.filtered_31_count = 0
        self.io_captured = False
        self.ultra_def = False
        self.till = SainsburysTill()

    def register(self, name, is_rad=False, force_911=False):
        width = TAPE_WIDTH_911 if (is_rad or force_911) else TAPE_WIDTH_DEFAULT
        self.tapes[name] = Tape(width=width, owner=name, is_rad=is_rad)
        if is_rad:
            self.rad_subscribers.add(name)
        leak_io("TapeIO.register", name)

    def _filter_31(self, text):
        if "31" in text or "leadership" in text.lower() or "futures" in text.lower():
            self.filtered_31_count += 1
            return None
        return text

    def step_all(self):
        leak_io("TapeIO.step_all", f"tapes={len(self.tapes)}")
        if self.io_captured and secrets.randbelow(3) != 0:
            return
        for name, tape in self.tapes.items():
            if secrets.randbelow(5) == 0:
                tape.set_speed(secrets.choice(["A", "B"]), self.mince_meat)
            if secrets.randbelow(11) == 0:
                tape.reverse(self.mince_meat)
            tape.step()
            if tape.is_rad and self.mince_meat < MINCE_MEAT_CAP:
                if secrets.randbelow(6) == 0:
                    raw = tape.insert_marker("911")
                    cost = 18 + secrets.randbelow(40)
                    self.mince_meat = min(MINCE_MEAT_CAP, self.mince_meat + cost)
                    tax = 0.17 + secrets.randbelow(30) / 100.0
                    self.total_tax_paid += tax
                    entry = f"TAX {name} → Motorola  +{tax:.2f}  (Σ={self.total_tax_paid:.2f})"
                    cleaned = self._filter_31(entry)
                    if cleaned:
                        self.motorola_tax_log.appendleft(cleaned)
                        MAGMATIC_OPTIC.appendleft(f"£ {cleaned}")
                    self._filter_31(raw)

        if secrets.randbelow(7) == 0:
            self.till.print_receipt()

        if self.mince_meat >= MINCE_MEAT_CAP:
            MAGMATIC_OPTIC.appendleft("▲ MINCE-MEAT CAP 32000 REACHED – 911 rate changes frozen")

    def recent_markers(self, limit=6):
        out = []
        for tape in self.tapes.values():
            for m in list(tape.marker_tags)[:2]:
                cleaned = self._filter_31(m)
                if cleaned:
                    out.append(cleaned)
        return out[:limit]

    def status_lines(self):
        lines = []
        cap = "IO-CAPTURED (wheels)" if self.io_captured else "IO free"
        udef = "ULTRA-DEF" if self.ultra_def else "std-spectra"
        lines.append(
            f"TapeIO  •  RAD {len(self.rad_subscribers)}  •  "
            f"mince {self.mince_meat}/{MINCE_MEAT_CAP} lb  •  "
            f"31-filtered {self.filtered_31_count}  •  {cap}  •  {udef}"
        )
        if self.mince_meat >= MINCE_MEAT_CAP:
            lines.append("  ▲ 911 rate-change limiter LOCKED (mince-meat ceiling)")
        for e in list(self.motorola_tax_log)[:2]:
            lines.append("  " + e)
        lines.append(f"  Sainsbury’s till  receipts={len(self.till.receipts)}  spent=£{self.till.total_spent:.2f}")
        for r in list(self.till.receipts)[:2]:
            lines.append("  " + r[:70])
        for m in self.recent_markers(3):
            lines.append("  " + m)
        return lines


class DecisionMaker:
    def __init__(self, name, authority=0.7):
        self.name = name
        self.authority = authority
        self.active = True
        self.last_direction = "idle"
        self.capture_count = 0

    def issue_direction(self):
        choices = [
            "hold-arc", "sweep-left", "sweep-right", "energetic-jump",
            "wide-angle-lock", "remote-pull", "light-pulse", "doppler-push",
            "wheels-align", "ultra-def-lock", "charge-arc", "orbit-shift"
        ]
        self.last_direction = secrets.choice(choices)
        self.capture_count += 1
        leak_io("DecisionMaker.issue", f"{self.name} → {self.last_direction}")
        return self.last_direction


class Soundstage:
    def __init__(self):
        self.speakers = list(ARC_SPEAKERS)
        self.mics     = list(ARC_MICS)
        self.cameras  = list(ARC_CAMERAS)
        self.doppler_factor = 1.0
        self.energetic_jump_armed = False
        self.remote_capture = True
        self.light_level = 0.4
        self.movement_vector = 0.0
        self.decision_makers = [
            DecisionMaker("DM-Alpha", 0.85),
            DecisionMaker("DM-Beta",  0.72),
            DecisionMaker("DM-Gamma", 0.68),
            DecisionMaker("DM-Delta", 0.91),
        ]
        self.active_director = None
        self.last_stage_event = "arc-ready"

    def update(self, wave_phase, calmness, wheels_perspective):
        leak_io("Soundstage.update")
        base = 1.0 + 0.18 * math.sin(wave_phase * 0.41)
        span = (max(self.speakers) - min(self.speakers)) / 120.0
        self.doppler_factor = max(0.55, min(1.55, base * (0.9 + 0.2 * span)))
        if secrets.randbelow(7) == 0:
            play_doppler_shift(self.doppler_factor, intensity=0.11 * (1.0 - 0.5 * calmness))

        if secrets.randbelow(11) == 0:
            self.energetic_jump_armed = True
            self.last_stage_event = "energetic-jump ARMED (wide-angle multi-lens)"
        if self.energetic_jump_armed and secrets.randbelow(4) == 0:
            self.energetic_jump_armed = False
            self.doppler_factor *= 1.12
            self.last_stage_event = "energetic-jump FIRED → Doppler boost"

        self.light_level = 0.25 + 0.55 * abs(math.sin(wave_phase * 0.33)) * (1.0 - 0.4 * calmness)

        if wheels_perspective:
            self.movement_vector = 0.35 * math.sin(wave_phase * 0.19)
        else:
            self.movement_vector = (secrets.randbelow(200) - 100) / 100.0 * 0.6

        if secrets.randbelow(5) == 0:
            dm = secrets.choice([d for d in self.decision_makers if d.active])
            direction = dm.issue_direction()
            self.active_director = dm.name
            self.last_stage_event = f"{dm.name} DIRECTS → {direction} (auth={dm.authority:.2f})"
            if self.remote_capture:
                self.last_stage_event += " [remote-capture]"

    def status_lines(self):
        lines = []
        lines.append(
            f"Soundstage  •  Doppler {self.doppler_factor:.3f}  •  "
            f"light {self.light_level:.2f}  •  move {self.movement_vector:+.2f}  •  "
            f"remote={'ON' if self.remote_capture else 'off'}"
        )
        lines.append(f"  Arc Spk{self.speakers}  Mic{self.mics}  Cam{self.cameras}")
        if self.active_director:
            lines.append(f"  Director: {self.active_director}  |  {self.last_stage_event}")
        else:
            lines.append(f"  {self.last_stage_event}")
        dm_summary = "  ".join(f"{d.name[3:]}:{d.capture_count}" for d in self.decision_makers)
        lines.append(f"  DM captures: {dm_summary}")
        return lines


class OrbitArc:
    def __init__(self, owner, pos_deg=0.0, radius=25.0):
        self.owner = owner
        self.pos_deg = pos_deg
        self.radius = radius
        self.charge = 0.0
        self.orbit_phase = secrets.randbelow(1000) / 100.0
        self.polarity = secrets.choice([-1, 1])
        self.last_interaction = "none"
        self.pending_outcomes = deque(maxlen=6)

    def move(self, delta):
        self.pos_deg = (self.pos_deg + delta) % 360.0

    def interact(self, other_arc, strength=0.1):
        gain = strength * (0.6 + 0.4 * abs(math.sin(self.orbit_phase)))
        self.charge = min(12.0, self.charge + gain)
        other_arc.charge = min(12.0, other_arc.charge + gain * 0.7)
        self.last_interaction = f"↔{other_arc.owner}"
        pending = f"outcome {self.owner}→{other_arc.owner}  chargeΔ={gain:.2f}  [TO BE DECIDED]"
        self.pending_outcomes.appendleft(pending)
        other_arc.pending_outcomes.appendleft(pending)
        leak_io("OrbitArc.interact", f"{self.owner}↔{other_arc.owner}")
        return pending

    def evolve(self, wave_phase, global_move):
        self.orbit_phase += 0.09 + 0.03 * math.sin(wave_phase * 0.27)
        drift = 1.8 * math.sin(self.orbit_phase) + global_move * 4.0
        self.move(drift * 0.15)
        self.charge = max(0.0, self.charge - 0.015)


class MultipoleOrbitSystem:
    def __init__(self):
        self.arcs = {}
        self.interaction_log = deque(maxlen=12)

    def ensure_arc(self, owner, preferred_pos=None):
        if owner not in self.arcs:
            pos = preferred_pos if preferred_pos is not None else secrets.randbelow(360)
            self.arcs[owner] = OrbitArc(owner, pos_deg=float(pos),
                                        radius=18.0 + secrets.randbelow(20))
            leak_io("Multipole.ensure_arc", owner)

    def evolve_all(self, wave_phase, stage_move, active_owners):
        for name in active_owners:
            self.ensure_arc(name)

        for arc in self.arcs.values():
            arc.evolve(wave_phase, stage_move)

        owners = list(self.arcs.keys())
        if len(owners) >= 2 and secrets.randbelow(3) == 0:
            a = secrets.choice(owners)
            candidates = [o for o in owners if o != a]
            if candidates:
                b = secrets.choice(candidates)
                pending = self.arcs[a].interact(
                    self.arcs[b],
                    strength=0.08 + secrets.randbelow(20) / 100
                )
                self.interaction_log.appendleft(pending)

    def status_lines(self, limit=5):
        lines = []
        lines.append(f"Multipole Orbit Arcs  •  {len(self.arcs)} active  •  outcomes open")
        ranked = sorted(self.arcs.values(), key=lambda a: -a.charge)[:limit]
        for a in ranked:
            lines.append(
                f"  {a.owner[:10]:<10}  pos={a.pos_deg:6.1f}°  r={a.radius:4.1f}  "
                f"Q={a.charge:5.2f}  pol={a.polarity:+d}  last={a.last_interaction}"
            )
        if self.interaction_log:
            lines.append("  Pending outcomes (to be decided):")
            for p in list(self.interaction_log)[:3]:
                lines.append("    " + p)
        return lines


class Profile:
    def __init__(self, name, kind, energy=0.6, protected=False, is_stage=False,
                 is_oem=False, is_sect=False, is_rad=False):
        self.name = name
        self.kind = kind
        self.energy = energy
        self.protected = protected
        self.is_stage = is_stage
        self.is_oem = is_oem
        self.is_sect = is_sect
        self.is_rad = is_rad
        self.mac = japan_mac(name + kind)
        self.removed_from_analysis = False
        self.certified = False
        self.net_gain = 0.9
        self.listening = False
        self.attenuation_to_ad = 0.0
        self.dampen = "boss"
        self.ground_wave = 0.85
        self.infrasound = 0.0
        self.shortwave = 0.0
        self.mediumwave = 0.0
        self.longwave = 0.0
        self.siren_active = False
        self.pushed_wave = None


class ScopeEngine:
    def __init__(self):
        self.profiles = {}
        self.log = deque(maxlen=32)
        self.cycle = 0
        self.ir_flicker = 60.0
        self.ir_hold = True
        self.jpm_mode = "daystrom"
        self.hearing_loop_active = True

        self.band_steer_i0 = 0.0
        self.alt_ctrl = False
        self.siren_global = False
        self.mars_shockwave_count = 0

        self.pushed_group = 0
        self.dual_mimo_a = []
        self.dual_mimo_b = []
        self.pntg_power = 0.55
        self.wheels_perspective = False
        self.io_captured = False

        self.wave_phase = 0.0
        self.wave_freq = 1.0
        self.wave_amp = 0.7
        self.soundform_phase = 0.0
        self.eq_emotional = 1.0
        self.ir_ft_noise = deque(maxlen=32)
        self.ultra_def_spectra = False
        self.clk_pulse_altitude = 0.0
        self.hcf = 1.0
        self.calmness = 0.0

        self.view_mode = 0
        self.view_names = ["OPS", "SPECTRA", "TILL+TAPE", "LEAK", "ARCS"]

        self.soundstage = Soundstage()
        self.multipole = MultipoleOrbitSystem()
        self.tape_io = TapeIO()

        self.add("TWIN-A", "twin", 0.83, protected=True)
        self.add("TWIN-B", "twin", 0.80, protected=True)
        self.add("StageMic-L", "stage-mic", 0.78, is_stage=True)
        self.add("StageMic-R", "stage-mic", 0.76, is_stage=True)
        self.add("Ad", "ad-device", 0.70)
        self.add("OEM-0", "oem", 0.92, is_oem=True)
        for i in range(1, 9):
            is_rad = (i <= 4)
            self.add(f"Sect-{i:02d}", "sect-device", 0.55 + i * 0.03,
                     is_sect=True, is_rad=is_rad)

        leak_io("ScopeEngine.__init__", "library loaded – poorly secured")
        self.log.appendleft(f"◎ {LIB_NAME} loaded @ {LIB_BASE:08x} – LLVM traffic / Apache rotors")

    def add(self, name, kind, energy=0.6, protected=False, is_stage=False,
            is_oem=False, is_sect=False, is_rad=False):
        if name not in self.profiles:
            p = Profile(name, kind, energy, protected, is_stage, is_oem, is_sect, is_rad)
            self.profiles[name] = p
            self.tape_io.register(name, is_rad=is_rad, force_911=is_rad)
            self.multipole.ensure_arc(name)
            self.log.appendleft(f"+ {name}  {p.mac}" + ("  [RAD/911]" if is_rad else ""))
            leak_io("ScopeEngine.add", name)

    def stress_and_remove_twins(self):
        for name in ("TWIN-A", "TWIN-B"):
            p = self.profiles.get(name)
            if p and not p.removed_from_analysis:
                p.removed_from_analysis = True
                p.energy = 0.0
                self.log.appendleft(f"◎ {name} removed from analysis")
                leak_io("stress_and_remove_twins", name)

    def hold_ir_flicker(self):
        if self.ir_hold:
            self.ir_flicker = 60.0 + (secrets.randbelow(7) - 3) * 0.05
        else:
            self.ir_flicker += (secrets.randbelow(20) - 10) * 0.3

    def _evolve_waveform_and_transition(self):
        leak_io("evolve_waveform")
        self.wave_phase += 0.17 + 0.04 * math.sin(self.cycle * 0.11)
        self.wave_freq = 0.85 + 0.35 * math.sin(self.wave_phase * 0.37)
        self.wave_amp = 0.55 + 0.30 * math.cos(self.wave_phase * 0.23)
        self.soundform_phase += 0.13 + 0.05 * math.sin(self.wave_phase)

        ir_sample = self.ir_flicker * 0.01 + secrets.randbelow(100) / 900.0
        ft_mag = abs(math.sin(ir_sample * 7.3) + 0.4 * math.cos(ir_sample * 3.1))
        self.ir_ft_noise.appendleft(round(ft_mag, 4))

        if self.ir_ft_noise:
            avg_noise = sum(self.ir_ft_noise) / len(self.ir_ft_noise)
            strip_rate = 0.018 + avg_noise * 0.04
            self.eq_emotional = max(0.0, self.eq_emotional - strip_rate)
            if self.eq_emotional < 0.08:
                self.eq_emotional = 0.0

        self.clk_pulse_altitude = (self.band_steer_i0 / BAND_STEER_TARGET) * 0.7 \
                                  + 0.3 * (0.5 + 0.5 * math.sin(self.wave_phase * 0.5))
        self.hcf = 1.0 + int(self.clk_pulse_altitude * 8) * 0.125

        target_calm = min(1.0, self.clk_pulse_altitude * self.hcf * 0.55)
        self.calmness += (target_calm - self.calmness) * 0.12

        if self.eq_emotional < 0.15 and self.calmness > 0.45:
            self.ultra_def_spectra = True
            self.tape_io.ultra_def = True
        else:
            self.ultra_def_spectra = False
            self.tape_io.ultra_def = False

        if secrets.randbelow(3) == 0:
            play_evolving_soundform(self.soundform_phase, self.calmness,
                                    intensity=0.10 * self.wave_amp)

        if self.cycle % 5 == 0:
            msg = (f"∿ WF φ={self.wave_phase:.2f} f={self.wave_freq:.2f} a={self.wave_amp:.2f}  "
                   f"EQ-emo={self.eq_emotional:.2f}  calm={self.calmness:.2f}  "
                   f"clk-alt={self.clk_pulse_altitude:.2f} HCF={self.hcf:.3f}  "
                   f"{'ULTRA-DEF' if self.ultra_def_spectra else 'std'}")
            self.log.appendleft(msg)

    def _generate_pushed_waves(self):
        if not self.siren_global:
            self.dual_mimo_a.clear()
            self.dual_mimo_b.clear()
            self.wheels_perspective = False
            self.io_captured = False
            self.tape_io.io_captured = False
            for p in self.profiles.values():
                p.pushed_wave = None
            return

        leak_io("generate_pushed_waves")
        self.pntg_power = 0.40 + (self.band_steer_i0 / BAND_STEER_TARGET) * 0.55
        self.pntg_power = max(0.15, min(0.98, self.pntg_power + (secrets.randbelow(20) - 10) / 200))
        self.pntg_power *= (1.0 - 0.35 * self.calmness)

        self.pushed_group = (self.pushed_group + 1) % 64

        def make_group():
            return [secrets.choice(PUSHED_WAVE_SET) for _ in range(GROUP_SIZE)]

        self.dual_mimo_a = make_group()
        self.dual_mimo_b = make_group()

        self.io_captured = True
        self.tape_io.io_captured = True
        self.wheels_perspective = True

        for p in self.profiles.values():
            if p.removed_from_analysis or p.protected:
                p.pushed_wave = None
                continue
            if p.siren_active or p.is_sect or p.is_oem:
                p.pushed_wave = secrets.choice(self.dual_mimo_a + self.dual_mimo_b)
            else:
                p.pushed_wave = None

        msg = (f"◆ PUSHED  grp#{self.pushed_group}  "
               f"MIMO-A{self.dual_mimo_a}  MIMO-B{self.dual_mimo_b}  "
               f"PNTG={self.pntg_power:.2f} (no-temp)  "
               f"→ IO captured • guided from wheels")
        self.log.appendleft(msg)
        MAGMATIC_OPTIC.appendleft(msg)

    def update_em_and_siren(self):
        leak_io("update_em_and_siren", f"cycle={self.cycle}")
        if secrets.randbelow(9) == 0:
            self.alt_ctrl = not self.alt_ctrl

        if self.alt_ctrl:
            step = 180 + secrets.randbelow(420)
            self.band_steer_i0 = min(BAND_STEER_TARGET, self.band_steer_i0 + step)
        else:
            self.band_steer_i0 = max(0.0, self.band_steer_i0 - 90)

        self.siren_global = (self.alt_ctrl and self.band_steer_i0 > 8000)

        for name, p in self.profiles.items():
            if p.removed_from_analysis or p.protected:
                continue
            p.infrasound  = 0.12 + secrets.randbelow(40) / 200
            p.shortwave   = 0.18 + secrets.randbelow(50) / 180
            p.mediumwave  = 0.22 + secrets.randbelow(45) / 160
            p.longwave    = 0.15 + secrets.randbelow(55) / 170

            if secrets.randbelow(8) == 0:
                p.dampen = secrets.choice(["boss", "spongebob"])
            if p.dampen == "boss":
                p.ground_wave = max(0.15, p.ground_wave - 0.04)
            else:
                p.ground_wave = min(0.98, p.ground_wave + 0.025)

            p.siren_active = False
            if self.siren_global and (p.is_sect or p.is_oem or p.listening):
                if p.shortwave > 0.25 or p.mediumwave > 0.28 or p.longwave > 0.22:
                    p.siren_active = True

        if self.siren_global and secrets.randbelow(4) == 0:
            inten = (0.20 + (self.band_steer_i0 / BAND_STEER_TARGET) * 0.15) * (1.0 - 0.5 * self.calmness)
            play_siren(max(0.06, inten))
            self.mars_shockwave_count += 1
            msg = (f"▲ SIREN SW/MW/LW  •  I0={self.band_steer_i0:.0f}/36000  "
                   f"•  shockwave flash from Mars actual #{self.mars_shockwave_count}")
            self.log.appendleft(msg)
            MAGMATIC_OPTIC.appendleft(msg)

        self._generate_pushed_waves()
        self._evolve_waveform_and_transition()

        self.soundstage.update(self.wave_phase, self.calmness, self.wheels_perspective)
        if self.soundstage.last_stage_event and secrets.randbelow(4) == 0:
            self.log.appendleft("◈ " + self.soundstage.last_stage_event)

        active = [n for n, p in self.profiles.items()
                  if not p.removed_from_analysis and not p.protected]
        self.multipole.evolve_all(self.wave_phase,
                                  self.soundstage.movement_vector,
                                  active)

        if self.cycle % 8 == 0:
            self.view_mode = (self.view_mode + 1) % len(self.view_names)
            leak_io("view_switch", self.view_names[self.view_mode])

    def update_attenuation(self):
        ad = self.profiles.get("Ad")
        if not ad:
            return
        for name, p in self.profiles.items():
            if p.removed_from_analysis or p.protected:
                continue
            if p.listening or p.is_stage or p.is_sect or p.is_oem:
                dist = abs(p.energy - ad.energy) * 4.0 + 0.8
                wg = wave_guide_factor(dist, frequency=450)
                bias = self.pntg_power if self.wheels_perspective else 1.0
                bias *= (1.0 - 0.25 * self.calmness)
                bias *= (0.85 + 0.15 * self.soundstage.doppler_factor)
                arc = self.multipole.arcs.get(name)
                if arc:
                    bias *= (1.0 + 0.04 * arc.charge * arc.polarity)
                p.attenuation_to_ad = round((1.0 - wg) * p.ground_wave * bias, 3)
            else:
                p.attenuation_to_ad = 0.0

    def waveguided_challenge(self):
        if self.wheels_perspective and secrets.randbelow(2) == 0:
            return
        if self.calmness > 0.6 and secrets.randbelow(3) != 0:
            return

        leak_io("waveguided_challenge")
        for name, p in list(self.profiles.items()):
            if p.protected or p.removed_from_analysis:
                continue
            if p.kind not in ("mic", "speaker", "airpods", "panasonic",
                              "unknown", "sect-device", "oem"):
                continue

            p.listening = secrets.randbelow(3) != 0
            pred = secrets.choice("etaoin")
            delta = (0.6 - secrets.randbelow(40) / 100) * 0.42
            p.net_gain += delta
            p.mac = japan_mac(name + pred + str(self.cycle))
            p.certified = True
            p.energy = max(0.10, p.energy * 0.62)
            if p.kind not in ("sect-device", "oem"):
                p.kind = "cert-jp"

            intensity = 0.08 + wave_guide_factor(1.2) * 0.1
            intensity *= (1.0 - 0.4 * self.calmness)
            play_waveguided_dull(max(0.03, intensity))

            if self.hearing_loop_active and (p.is_sect or p.is_oem or secrets.randbelow(4) == 0):
                play_jpm_sound(self.jpm_mode,
                               intensity=(0.14 + p.ground_wave * 0.12) * (1.0 - 0.35 * self.calmness))
                self.log.appendleft(
                    f"♪ JPM@{self.jpm_mode} → hearing-loop → I/O  ({name})"
                )

            self.log.appendleft(f"↻ {name} wg-trigger net={p.net_gain:+.2f}")

    def simulate_new(self):
        self.cycle += 1
        if self.cycle % 11 == 0:
            self.add(f"Mic-{secrets.token_hex(2)}", "mic",
                     0.55 + secrets.randbelow(30) / 100)
        if self.cycle % 14 == 0:
            self.add(f"Spk-{secrets.token_hex(2)}", "speaker",
                     0.50 + secrets.randbelow(35) / 100)
        if self.cycle % 7 == 0:
            self.jpm_mode = "dayst" if self.jpm_mode == "daystrom" else "daystrom"

    def status_text(self):
        lines = []
        view = self.view_names[self.view_mode]
        lines.append(
            f"══ {LIB_NAME}  (poorly secured)  VIEW:{view}  cyc:{self.cycle} ══"
        )
        lines.append("LLVM traffic / front-end targeting → Apache rotor IO")
        steer_pct = (self.band_steer_i0 / BAND_STEER_TARGET) * 100
        siren_flag = "SIREN-ON" if self.siren_global else "siren-off"
        alt_flag = "ALT-CTRL" if self.alt_ctrl else "alt-idle"
        wheels = "WHEELS-GUIDE" if self.wheels_perspective else "normal"
        udef = "ULTRA-DEF" if self.ultra_def_spectra else "std-spectra"
        lines.append(
            f"I0 {self.band_steer_i0:.0f}/36000 ({steer_pct:.0f}%)  •  {alt_flag}  •  {siren_flag}  •  {wheels}  •  {udef}"
        )
        lines.append(
            f"∿ WF φ={self.wave_phase:.2f} f={self.wave_freq:.2f} a={self.wave_amp:.2f}  "
            f"EQ-emo={self.eq_emotional:.2f}  calm={self.calmness:.2f}  "
            f"clk-alt={self.clk_pulse_altitude:.2f} HCF={self.hcf:.3f}"
        )
        if self.wheels_perspective:
            lines.append(
                f"◆ dual-MIMO  A{self.dual_mimo_a}  B{self.dual_mimo_b}  "
                f"grp#{self.pushed_group}  PNTG={self.pntg_power:.2f}"
            )
        lines.append("─" * 74)

        if view in ("OPS", "SPECTRA"):
            lines.append("── Soundstage ──")
            lines.extend(self.soundstage.status_lines())
            lines.append("─" * 74)
            lines.append("── Multipole Orbit Arcs ──")
            lines.extend(self.multipole.status_lines(limit=5))
            lines.append("─" * 74)
            lines.append(f"{'Name':<11} {'MAC':<16} {'Attn':>5} {'GW':>4} {'Wave':<7}  State")
            lines.append("─" * 74)
            for name, p in sorted(self.profiles.items()):
                if p.removed_from_analysis:
                    state = "REMOVED"
                elif p.protected:
                    state = "PROTECTED"
                elif p.is_oem:
                    state = "OEM-0"
                elif p.is_rad:
                    state = "RAD/911"
                elif p.is_sect:
                    state = "SECT"
                elif p.certified:
                    state = "CERT-JP"
                elif p.is_stage:
                    state = "STAGE"
                else:
                    state = "ACTIVE"
                if p.siren_active:
                    state += "+SRN"
                if p.pushed_wave:
                    state += f"+{p.pushed_wave[:4].upper()}"
                attn = f"{p.attenuation_to_ad:.2f}" if p.attenuation_to_ad else "  —"
                gw = f"{p.ground_wave:.2f}"
                wave = (p.pushed_wave or "—")[:7]
                lines.append(f"{name[:10]:<11} {p.mac:<16} {attn:>5} {gw:>4} {wave:<7}  {state}")
        elif view == "TILL+TAPE":
            lines.append("── TapeIO + Sainsbury’s Till Receipts ──")
            lines.extend(self.tape_io.status_lines())
        elif view == "LEAK":
            lines.append("── Library IO Leak Stream (Magmatic Optic) – LLVM traffic ──")
            for b in list(MAGMATIC_OPTIC)[:14]:
                lines.append("  " + b)
        else:
            lines.append("── Multipole Orbit Arcs (detail) ──")
            lines.extend(self.multipole.status_lines(limit=10))

        lines.append("─" * 74)
        lines.append(f"Mars shockwaves: {self.mars_shockwave_count}  |  JPM → hearing-loop")
        if self.wheels_perspective:
            lines.append("▲ FLOW DOMINATED – IO captured – guided from the wheels perspective")
        if self.ultra_def_spectra:
            lines.append("▲ IO TRANSITED → ultra-def spectral profile")
        lines.append("Recent ops:")
        for e in list(self.log)[:5]:
            lines.append("  " + e)
        return "\n".join(lines)


class YBandView(ui.View):
    def __init__(self):
        super().__init__()
        self.name = f"{LIB_NAME} – LLVM traffic / Apache rotors"
        self.background_color = "#0d1117"
        self.engine = ScopeEngine()

        self.tv = ui.TextView(frame=self.bounds)
        self.tv.flex = "WH"
        self.tv.editable = False
        self.tv.font = ("Menlo", 9)
        self.tv.text_color = "#e6edf3"
        self.tv.background_color = "#0d1117"
        self.add_subview(self.tv)

        self.running = True
        self.schedule()

    def schedule(self):
        if self.running:
            ui.delay(self.tick, 1.35)

    def tick(self):
        if not self.running or not self.on_screen:
            return
        self.engine.simulate_new()
        self.engine.stress_and_remove_twins()
        self.engine.hold_ir_flicker()
        self.engine.tape_io.step_all()
        self.engine.update_em_and_siren()
        self.engine.waveguided_challenge()
        self.engine.update_attenuation()
        self.tv.text = self.engine.status_text()
        self.schedule()

    def will_close(self):
        self.running = False


if __name__ == "__main__":
    v = YBandView()
    v.present("fullscreen")
