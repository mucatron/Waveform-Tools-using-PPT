#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THE TWINS CODEC v13 — Cèptre Mirror / LLM Wave / LBand Rotor (RMS + mirrored spectra)
Pythonista • local visual/audio-signal simulation

Cèptre processes every selected induced soundform and its secondary response.
The L-shaped rotor targets the nearest processed mirror soundform, displays
its simulated spectrum (RMS-scaled, mirrored about its baseline and
point-reflected through the scope center), and calculates a performance score.
The RMS-scaled mirror is the opposite spectrum in colour and soundform.
RMS values move continuously with the L-band rotor; hysteresis is removed
continuously from the RMS path (exponential baseline subtraction).

Local simulation only:
- Does not transmit RF, BLE, ultrasound, or 93 nm optical radiation.
- Vibration is visual modulation, not physical haptics.
- LLM Wave is a mathematical signal-processing stage, not an actual LLM.
- Transfer, RMS and performance values are simulated, not physical measurements.
"""

import ui
from scene import *
import motion
import os
import struct
import tempfile
import threading
from array import array
import wave as wavelib

try:
    import sound
except ImportError:  # not running inside Pythonista
    sound = None

try:
    import ctypes
    from objc_util import ObjCClass
except ImportError:  # not running inside Pythonista
    ctypes = None
    ObjCClass = None
import time
import random
import math
from collections import defaultdict, deque

print("THE TWINS CODEC v13 - Cèptre Mirror / LLM Wave / LBand L-Rotor")

# ===================== FEATURE FLAGS =====================
CONSOLE_PRINTING = False
OPTICS_PREFERRED = True
SECRECY_MODE = True
PURE_OPTICS_ONLY = True
BANDPASS_BYPASS_ACTIVE = True
PWR_DOWN_ACTIVE = False
SIGNAL_WHITE = False
MEASUREMENT_MODE = True
WINDSOCK_ACTIVE = True
AUTO_TUNE_ACTIVE = True
CALIBRATION_MODE = True
INFRASONIC_ACTIVE = True
BLE_COMPLIANT_MODE = True
DOLPHIN_TONE_ACTIVE = True
ULTRA_DOLPHIN_ACTIVE = True
PRE_RENDER_LOOKAHEAD = True
EXTERNAL_INTERFERENCE_DETECTED = True
NOISE_GATE_ACTIVE = True
MIC_SWITCHED_TO_BLIPS = True
ROBOT_SIMULATOR_ACTIVE = True
NUM_ROBOTS = 84

# ===================== CÈPTRE / LLM WAVE =====================
CEPTRE_MIRROR_ACTIVE = True
LLM_WAVE_ACTIVE = True
LBAND_ROTOR_ACTIVE = True

LBAND_ROTOR_SPEED = 0.45
LBAND_ROTOR_DEPTH = 0.18

# Below 0.5 avoids exact cancellation between a signal and its inverse.
CEPTRE_MIRROR_BLEND = 0.35

CEPTRE_BASE_ATTENUATION = 0.82
CEPTRE_MIN_ATTENUATION = 0.20
CEPTRE_MAX_ATTENUATION = 1.00

CEPTRE_VIBRATION_ENABLED = True
CEPTRE_VIBRATION_GAIN = 0.16
CEPTRE_VIBRATION_RATE = 7.0

CEPTRE_COLOR_ORIGINAL = '#44bbff'
CEPTRE_COLOR_MIRRORED = '#ff66cc'
CEPTRE_COLOR_MIXED = '#aa88ff'

LBAND_ROTOR_PHASE = 0.0
LBAND_ROTOR_PHASE_TOTAL = 0.0   # unwrapped, drives mirror rhythm
CEPTRE_PROCESSED_COUNT = 0
CEPTRE_HISTORY = deque(maxlen=120)
CEPTRE_LAST_OUTPUT = {}

CEPTRE_TRANSFER_STATE = {
    'target': None,
    'energy': 0.0,
    'performance': 0.0,
    'distance': 0.0,
    'timestamp': 0.0
}

# ===================== LBAND RMS =====================
LBAND_RMS_WINDOW = 24
LBAND_MIRROR_GAP = 4.0   # space between original bars and the mirror beneath
# Continuous hysteresis removal: exponential baseline tracker on the
# rolling RMS. The AC residual (raw - baseline) is what the rotor
# modulates; the mirror is always the exact negation of that value.
LBAND_RMS_BASELINE_TAU = 1.85   # seconds; slow component = hysteresis
LBAND_RMS_ROTOR_DEPTH = 0.22    # continuous L-band depth on the AC residual
LBAND_RMS_STATE = {
    'out': 0.0,      # continuous, hysteresis-free RMS (rotor-modulated)
    'orig': 0.0,     # RMS of original (pre-mirror) values
    'mirror': 0.0,   # NEGATIVE of the continuous out (signed opposite spectrum)
    'out_mirror': 0.0,  # alias of mirror (signed)
    'ratio': 0.0,    # out / orig
    'raw': 0.0,      # rolling-window RMS before hysteresis removal
    'baseline': 0.0, # slow component being removed
    'ac': 0.0        # residual after continuous hysteresis removal
}
LBAND_RMS_LAST_T = 0.0

# ===================== GLOBALS =====================
twin_pulse_alternator = 0.251+469e4
write_tone_map_phase = 0.0
spinning_plate_speed = 0.05/-0.05/0.4/-0.04/0.3/-0.03/20.35845/-0.01
twin_feedback_counter = 0

MEMORY_BUDGET = 1000.0
MEMORY_DEBT = 0.0
MAX_MEMORY_DEBT = 320.0

SUBVOCAL_REGISTRY = {}
FAMILY_VOCAL_PATTERNS = {}
INDUCTION_CHAIN = []
CHAINED_RESPONSES = defaultdict(list)

BITMASK = 0b10101
TWIN1_MAC = None
TWIN2_MAC = None
SECOND_BLE_CONTROLLER_MAC = None
robot_registry = {}

TWIN_INDUCTION_RED = '#ff2222'
FEEDBACK_COLOR_TWIN1 = '#ff44cc'
FEEDBACK_COLOR_TWIN2 = '#44ffcc'
DOLPHIN_TONE_COLOR = '#00ffff'
ULTRA_DOLPHIN_COLOR = '#ff00ff'
NOKIA_FUCK_YOU_COLOR = '#ff00aa'
OPTICAL_WHIRLPOOL_COLOR = '#66ffcc'
SUBVOCAL_COLOR = '#ff66aa'
CHAIN_COLOR = '#aaff88'
ELECTRICAL_BELL_COLOR = '#ffaa66'
WHITE_SIGNAL_COLOR = '#ffffff'
MEASUREMENT_COLOR = '#ffcc66'
WINDSOCK_COLOR = '#ff8800'
DOPPLER_COLOR = '#ffaa44'
NM93_COLOR = '#aa88ff'

SECTOR_COUNT = 8

# ===================== SECTOR TONE MAP =====================
# One audible pitch per scope sector. The notes are timed by the rhythm of
# the mirror spectrum: each mirror bar ripples with the LBand rotor, and every
# ripple peak is an onset. The pitch is the sector under the rotor, the
# instrument follows the observed rotor behaviour, and loudness follows the
# sector / overall RMS. Sectors with no recent Cèptre activity stay silent.
# Local stereo audio only.
TONE_MAP_ENABLED = True
TONE_MAP_BASE_FREQ = 220.0
TONE_MAP_RATIOS = [1.0, 9/8, 5/4, 3/2, 5/3, 2.0, 9/4, 5/2]  # one per sector
TONE_MAP_DURATION = 0.22
TONE_MAP_MAX_VOLUME = 0.6
TONE_MAP_MIN_LEVEL = 1.0      # sector RMS below this is treated as silent
TONE_MAP_WINDOW_S = 12.0      # how long a sector stays "identified"
TONE_MAP_MIRROR_ENABLED = True  # also play the negative-polarity mirror tone
# Volume multiplier driven by detected RMS: 1.0 at silence, rising to
# 1.0 + TONE_MAP_RMS_GAIN at full RMS (final volume is clamped to 1.0).
TONE_MAP_RMS_GAIN = 2.0
TONE_MAP_COLOR = '#ffee88'
TONE_MAP_COLOR_ACTIVE = '#ffffff'

# --- device audio profile (iPhone14,2 = iPhone 13 Pro) ---
# The profile renders true-stereo 16-bit audio at 48 kHz and keeps several
# players per note so retriggered notes can overlap (polyphony).
TONE_FORCE_IPHONE_14_2_PROFILE = True


def detect_device_model():
    try:
        return os.uname().machine
    except Exception:
        return 'unknown'


DEVICE_MODEL = detect_device_model()
IS_IPHONE_14_2 = DEVICE_MODEL.startswith('iPhone14,2')
USE_IPHONE_14_2_PROFILE = IS_IPHONE_14_2 or TONE_FORCE_IPHONE_14_2_PROFILE
TONE_SAMPLE_RATE = 48000 if USE_IPHONE_14_2_PROFILE else 22050
TONE_VOICES_PER_NOTE = 3 if USE_IPHONE_14_2_PROFILE else 1
TONE_PEAK = 28000
IOS_NODE_COUNT = 16   # AVAudioPlayerNode slots (voice + mirror twin per note)

# --- mirror rhythm (must match the mirror ripple that is drawn) ---
MIRROR_BAR_COUNT = 7
MIRROR_RIPPLE_RATE = 2.0      # ripple cycles per rotor cycle
MIRROR_RIPPLE_SPREAD = 0.9    # phase offset between neighbouring bars (rad)

# --- instruments, one per observed rotor behaviour ---
INSTRUMENT_ORDER = ['flute', 'bell', 'marimba', 'organ', 'buzz']

INSTRUMENTS = {
    'flute':   {'duration': 0.60, 'detune': 0.0025},
    'bell':    {'duration': 0.90, 'detune': 0.0015},
    'marimba': {'duration': 0.35, 'detune': 0.0010},
    'organ':   {'duration': 0.50, 'detune': 0.0030},
    'buzz':    {'duration': 0.25, 'detune': 0.0040}
}

BEHAVIOUR_INSTRUMENT = {
    'IDLE': 'flute',
    'STEADY': 'flute',     # level steady          -> breathy flute
    'SURGE': 'bell',       # RMS rising            -> FM bell
    'FADE': 'marimba',     # RMS falling           -> marimba
    'CLUSTER': 'organ',    # many sectors active   -> stereo-tremolo organ
    'CHAOS': 'buzz'        # jittery / interference -> buzzy synth
}

BEHAVIOUR_EVAL_INTERVAL = 0.25   # seconds between observations
BEHAVIOUR_HISTORY = 12           # observations kept (~3 s)
BEHAVIOUR_HOLD = 3               # observations before switching instrument
BEHAVIOUR_SLOPE_THRESHOLD = 0.04
BEHAVIOUR_CHAOS_JITTER = 0.06
BEHAVIOUR_CLUSTER_SECTORS = 5

# --- acoustic diameter profiles (four-section slider) ---
# The diameter sets how big the simulated acoustic field is. Volume and
# stereo width scale with diameter relative to 1 inch, so smaller diameters
# sound closer, quieter and narrower. 0.014 mm is off. Software scaling only.
ACOUSTIC_REFERENCE_MM = 25.4
ACOUSTIC_VOLUME_EXPONENT = 0.5
ACOUSTIC_WIDTH_EXPONENT = 0.6

ACOUSTIC_PROFILES = [
    {'label': '0.014mm off', 'diameter_mm': 0.014, 'enabled': False, 'stride': 1},
    {'label': '4mm',     'diameter_mm': 4.0,  'enabled': True,  'stride': 2},
    {'label': '8mm',     'diameter_mm': 8.0,  'enabled': True,  'stride': 1},
    {'label': '1 in',    'diameter_mm': 25.4, 'enabled': True,  'stride': 1}
]
ACOUSTIC_PROFILE_INDEX = 3   # 1 inch = the original full-field sound

TONE_MAP_STATE = {
    'sector': 0,
    'last_sector': -1,
    'freq': TONE_MAP_BASE_FREQ,
    'volume': 0.0,
    'multiplier': 1.0,
    'instrument': 'flute',
    'ready': 0,
    'backend': 'none',
    'error': '',
    'total': len(INSTRUMENTS) * SECTOR_COUNT,
    'mirror_volume': 0.0,                    # signed: always <= 0
    'levels': [0.0] * SECTOR_COUNT,
    'mirror_levels': [0.0] * SECTOR_COUNT    # negative of levels
}
TONE_MAP_PLAYERS = {}
TONE_MAP_CURSOR = {}
TONE_MAP_READY = set()
TONE_VOICE_STATS = {}   # (instrument, sector) -> rendered level/stereo stats
TONE_VOICE_DATA = {}    # (instrument, sector, mirror) -> (left, right) float32
IOS_AUDIO = None        # direct AVAudioEngine output (set at startup)
TONE_MAP_DIR = None
TONE_MAP_PREBUILD_STARTED = False

MIRROR_RHYTHM_STATE = {
    'last_k': [None] * MIRROR_BAR_COUNT,
    'bar_levels': [],
    'onsets': 0,
    'last_bar': 0
}

BEHAVIOUR_STATE = {
    'behaviour': 'STEADY',
    'candidate': 'STEADY',
    'count': 0,
    'instrument': 'flute',
    'slope': 0.0,
    'jitter': 0.0,
    'active': 0,
    'changes': 0,
    'last_eval': 0.0
}
BEHAVIOUR_RMS_TREND = deque(maxlen=BEHAVIOUR_HISTORY)

current_music_fs_path = "/inductions"
active_music_inductions = {}
blip_maturity = {}

last_induction_time = time.time()
mag_history = deque(maxlen=40)
acoustic_history = deque(maxlen=40)
chatter_events = deque(maxlen=30)
sunbeam_pool = []

io_attenuation = {
    'yband': -1.0,
    'ble': -1.0,
    'uwb': -1.0,
    'ir': -15.0,
    'infrasonic': -1.0,
    'dolphin': -1.0,
    'ultra_dolphin': -1.0,
    'optical': -1.0,
    'subvocal': -1.0,
    'chain': -1.0,
    'electrical_bell': -1.0,
    'measurement': -1.0,
    'windsock': -1.0
}

last_calibration_time = 0
CALIBRATION_INTERVAL = 5.5
unity_share_counter = 1000
BBC_TIME = "941"
CLASSIC_TONE_FREQUENCY = 445.0
SECURE_ELEMENT_BASE_URL = "secure://twins.local/element/"

INFRASONIC_THRESHOLD = -20.0
SUPERSONIC_THRESHOLD = 18000.0
DOLPHIN_FREQ_MIN = 20000.0
ULTRA_DOLPHIN_FREQ_MIN = 28000.0
FALLOUT_DECAY_RATE = 0.018

twins_search_log = []
last_measurement_time = ""


# ===================== SUBVOCAL REGISTRY =====================
def register_subvocal_with_signature(mac, vocal_type="subvocal"):
    if mac not in SUBVOCAL_REGISTRY:
        SUBVOCAL_REGISTRY[mac] = {
            "signature_mac": mac,
            "type": vocal_type,
            "timestamp": time.time(),
            "harmony": random.uniform(0.6, 1.4)
        }

    if mac not in INDUCTION_CHAIN:
        INDUCTION_CHAIN.append(mac)

    return SUBVOCAL_REGISTRY[mac]


# ===================== SIGNAL GENERATION =====================
def generate_optical_sine_wave_93nm(freq, sector, amplitude=1.0):
    phase = write_tone_map_phase * 4.2 + sector * 0.7
    sine = math.sin(phase) * amplitude
    envelope = 0.6 + 0.4 * math.sin(write_tone_map_phase * 9.3)
    return sine * envelope


def generate_electrical_sine_wave(freq, sector, diameter_miles=1200):
    ring = math.sin(freq * 0.00085) * 0.52
    decay = max(0.28, 1.0 - (sector * 0.052))
    diameter_factor = max(
        0.65,
        min(1.7, diameter_miles / 850.0)
    )

    wave = freq * (0.94 + ring * 0.06) * decay * diameter_factor

    if PWR_DOWN_ACTIVE:
        wave *= random.uniform(0.35, 0.72)

    return wave


def generate_windsock_soundform_with_doppler(
    freq,
    bearing,
    wind_direction=0,
    belt_timing=1.0,
    strength=1.0
):
    disturbance = math.sin(
        freq * 0.0012 + write_tone_map_phase * 1.8
    ) * 0.6

    air_volume = strength * (
        0.7 + 0.3 * math.sin(belt_timing * 4.2)
    )

    relative_velocity = (
        math.cos(math.radians(bearing - wind_direction)) * 0.8
    )

    doppler_shift = 1.0 + relative_velocity * 0.18
    shifted_freq = freq * doppler_shift

    soundform = (
        shifted_freq
        * (1.0 + disturbance * 0.4)
        * air_volume
    )

    return soundform, doppler_shift, air_volume


def generate_optical_planar_whirlpool(freq, sector, maturity):
    whirl = math.sin(
        write_tone_map_phase * 2.35 + sector
    ) * 0.37

    coil = math.cos(
        freq * 0.00032 + maturity * 6.28
    ) * 0.27

    planar = 1.0 + (whirl + coil) * 0.16

    if EXTERNAL_INTERFERENCE_DETECTED or PWR_DOWN_ACTIVE:
        planar *= 0.65

    return max(DOLPHIN_FREQ_MIN, freq * planar)


def derive_dolphin_sine_wave(
    freq,
    sector,
    scope_type='dolphin',
    diameter_miles=1200,
    bearing=0,
    wind_direction=0
):
    if WINDSOCK_ACTIVE and scope_type == 'windsock':
        soundform, doppler, volume = (
            generate_windsock_soundform_with_doppler(
                freq,
                bearing,
                wind_direction,
                twin_pulse_alternator,
                strength=1.2
            )
        )
        return soundform, volume

    optical = generate_optical_planar_whirlpool(
        freq,
        sector,
        get_blip_maturity("VIRTUAL")
    )

    electrical = generate_electrical_sine_wave(
        freq,
        sector,
        diameter_miles
    )

    if scope_type in ['optical', 'measurement']:
        return optical, electrical * 0.25

    return (
        (optical * 0.65) + (electrical * 0.35),
        electrical * 0.18
    )


# ===================== CÈPTRE MIRROR PROCESSOR =====================
def advance_lband_rotor():
    global LBAND_ROTOR_PHASE, LBAND_ROTOR_PHASE_TOTAL

    if LBAND_ROTOR_ACTIVE:
        step = LBAND_ROTOR_SPEED * 0.028
        LBAND_ROTOR_PHASE = (LBAND_ROTOR_PHASE + step) % (2.0 * math.pi)
        LBAND_ROTOR_PHASE_TOTAL += step

    return LBAND_ROTOR_PHASE


def process_ceptre_wave(
    soundform,
    freq,
    sector,
    scope_type='yband',
    source_mac=None
):
    """Mirror/blend a scalar simulation value and apply rotor and attenuation."""
    global CEPTRE_PROCESSED_COUNT, CEPTRE_LAST_OUTPUT

    original = float(soundform)
    mirrored = -original if CEPTRE_MIRROR_ACTIVE else original
    phase = LBAND_ROTOR_PHASE

    if LLM_WAVE_ACTIVE and LBAND_ROTOR_ACTIVE:
        rotor = math.sin(phase + sector * 0.35)
        rotor_gain = 1.0 + LBAND_ROTOR_DEPTH * rotor
    else:
        rotor = 0.0
        rotor_gain = 1.0

    blend = max(
        0.0,
        min(1.0, CEPTRE_MIRROR_BLEND)
    )

    mixed = (
        original * (1.0 - blend) + mirrored * blend
        if CEPTRE_MIRROR_ACTIVE
        else original
    )

    llm_wave = mixed * rotor_gain

    attenuation = max(
        CEPTRE_MIN_ATTENUATION,
        min(CEPTRE_MAX_ATTENUATION, CEPTRE_BASE_ATTENUATION)
    )

    output = llm_wave * attenuation

    vibration = 0.0

    if CEPTRE_VIBRATION_ENABLED:
        vibration = (
            output
            * CEPTRE_VIBRATION_GAIN
            * math.sin(
                phase * CEPTRE_VIBRATION_RATE + sector * 0.5
            )
        )

    if not CEPTRE_MIRROR_ACTIVE:
        color = CEPTRE_COLOR_ORIGINAL
    elif rotor >= 0.25:
        color = CEPTRE_COLOR_MIRRORED
    elif rotor <= -0.25:
        color = CEPTRE_COLOR_MIXED
    else:
        color = CEPTRE_COLOR_MIRRORED

    result = {
        'original': original,
        'mirrored': mirrored,
        'llm_wave': llm_wave,
        'attenuation': attenuation,
        'output': output,
        'vibration': vibration,
        'color': color,
        'rotor_phase': phase,
        'frequency': float(freq),
        'sector': int(sector) % SECTOR_COUNT,
        'scope_type': scope_type,
        'source': source_mac,
        'timestamp': time.time()
    }

    CEPTRE_PROCESSED_COUNT += 1
    CEPTRE_HISTORY.append(result)
    CEPTRE_LAST_OUTPUT = result

    return result


def compute_lband_rms(window=LBAND_RMS_WINDOW):
    """
    Continuous L-band RMS with hysteresis removed.

    1. Rolling-window RMS of recent Cèptre outputs (raw).
    2. Continuous exponential baseline tracks the slow component
       (the hysteresis / lag of the window). Residual = raw - baseline.
    3. L-band rotor modulates the residual continuously so the values
       move with the rotor phase.
    4. Mirror is the exact negation of the continuous out (opposite
       soundform). Colour of the mirror spectrum is handled at draw time.
    """
    global LBAND_RMS_LAST_T

    items = list(CEPTRE_HISTORY)[-window:]
    now = time.time()

    if not items:
        return LBAND_RMS_STATE

    n = float(len(items))
    raw_out = math.sqrt(sum(i['output'] ** 2 for i in items) / n)
    orig = math.sqrt(sum(i['original'] ** 2 for i in items) / n)

    # Continuous hysteresis removal (first-order high-pass on the RMS).
    dt = max(1e-3, now - LBAND_RMS_LAST_T) if LBAND_RMS_LAST_T else 0.05
    LBAND_RMS_LAST_T = now
    alpha = 1.0 - math.exp(-dt / max(LBAND_RMS_BASELINE_TAU, 1e-3))
    baseline = LBAND_RMS_STATE['baseline']
    baseline = baseline + alpha * (raw_out - baseline)
    ac = raw_out - baseline

    # Continuous L-band motion: residual + light baseline breathe with the
    # rotor phase so the RMS values move continuously as the L-band turns.
    rotor = math.sin(LBAND_ROTOR_PHASE)
    rotor2 = math.sin(LBAND_ROTOR_PHASE * 2.0 + 0.7)
    continuous = max(
        0.0,
        ac * (1.0 + LBAND_RMS_ROTOR_DEPTH * rotor)
        + baseline * (0.12 + 0.08 * rotor2)
    )

    # Opposite soundform: mirror is the exact signed negation.
    mirror = -continuous

    LBAND_RMS_STATE.update({
        'out': continuous,
        'orig': orig,
        'mirror': mirror,
        'out_mirror': mirror,
        'ratio': continuous / max(orig, 1e-9),
        'raw': raw_out,
        'baseline': baseline,
        'ac': ac
    })

    return LBAND_RMS_STATE


# ===================== SECTOR TONE MAP FUNCTIONS =====================
def sector_tone_frequency(sector):
    ratio = TONE_MAP_RATIOS[sector % len(TONE_MAP_RATIOS)]
    return TONE_MAP_BASE_FREQ * ratio


def tone_level_norm(level):
    """Log-scale a sector RMS into 0..1 so quiet and loud sectors both show."""
    return max(0.0, min(1.0, math.log10(1.0 + abs(level)) / 4.6))


def get_rotor_sector():
    """Scope sector currently under the LBand rotor."""
    return get_sector(math.degrees(LBAND_ROTOR_PHASE))


def compute_sector_rms(window_s=TONE_MAP_WINDOW_S):
    """RMS of recent Cèptre outputs grouped by scope sector."""
    now = time.time()
    acc = [0.0] * SECTOR_COUNT
    cnt = [0] * SECTOR_COUNT

    for item in CEPTRE_HISTORY:
        if now - item['timestamp'] > window_s:
            continue

        s = item['sector'] % SECTOR_COUNT
        acc[s] += item['output'] ** 2
        cnt[s] += 1

    levels = [
        math.sqrt(a / c) if c else 0.0
        for a, c in zip(acc, cnt)
    ]

    TONE_MAP_STATE['levels'] = levels
    TONE_MAP_STATE['mirror_levels'] = [-lv for lv in levels]
    return levels


class IOSAudioEngine:
    """
    Direct iOS audio output through AVAudioEngine (via objc_util).

    The AVAudioSession is set to the Playback category, so the ring/silent
    switch does not mute the tones. Each voice is an in-memory float32 stereo
    AVAudioPCMBuffer scheduled on a pooled AVAudioPlayerNode, so notes can
    overlap and are panned by the node's own pan control.
    """

    def __init__(self, sample_rate, node_count):
        self.rate = sample_rate
        self.node_count = node_count
        self.ok = False
        self.error = None
        self.session = None
        self.engine = None
        self.fmt = None
        self.nodes = []
        self.cursor = 0
        self.buffers = {}
        self.restarts = 0

    def start(self):
        if ObjCClass is None or ctypes is None:
            self.error = 'objc_util unavailable'
            return False

        try:
            session = ObjCClass('AVAudioSession').sharedInstance()
            session.setCategory_error_('AVAudioSessionCategoryPlayback', None)
            session.setPreferredSampleRate_error_(float(self.rate), None)
            session.setActive_error_(True, None)
            self.session = session

            self.engine = ObjCClass('AVAudioEngine').alloc().init()

            # 1 = AVAudioPCMFormatFloat32, 2 channels, non-interleaved
            self.fmt = ObjCClass('AVAudioFormat').alloc() \
                .initWithCommonFormat_sampleRate_channels_interleaved_(
                    1, float(self.rate), 2, False
                )

            mixer = self.engine.mainMixerNode()
            node_class = ObjCClass('AVAudioPlayerNode')

            for _ in range(self.node_count):
                node = node_class.alloc().init()
                self.engine.attachNode_(node)
                self.engine.connect_to_format_(node, mixer, self.fmt)
                self.nodes.append(node)

            if not self.engine.startAndReturnError_(None):
                raise RuntimeError('AVAudioEngine failed to start')

            for node in self.nodes:
                node.play()

            self.ok = True
            return True
        except Exception as exc:
            self.error = str(exc)
            self.ok = False
            return False

    def ensure_running(self):
        """Restart the engine if iOS stopped it (interruption, route change)."""
        try:
            if self.engine.isRunning():
                return True
        except Exception:
            pass

        try:
            self.session.setActive_error_(True, None)

            if self.engine.startAndReturnError_(None):
                for node in self.nodes:
                    node.play()

                self.restarts += 1
                return True
        except Exception:
            pass

        return False

    def _buffer(self, key, data):
        buf = self.buffers.get(key)

        if buf is not None:
            return buf

        left, right = data
        frames = len(left)

        buf = ObjCClass('AVAudioPCMBuffer').alloc() \
            .initWithPCMFormat_frameCapacity_(self.fmt, frames)
        buf.setFrameLength_(frames)

        channels = ctypes.cast(
            buf.floatChannelData(),
            ctypes.POINTER(ctypes.POINTER(ctypes.c_float))
        )

        nbytes = frames * 4
        ctypes.memmove(channels[0], left.tobytes(), nbytes)
        ctypes.memmove(channels[1], right.tobytes(), nbytes)

        self.buffers[key] = buf
        return buf

    def play(self, key, data, volume, pan):
        if not self.ensure_running():
            raise RuntimeError('AVAudioEngine is not running')

        buf = self._buffer(key, data)
        node = self.nodes[self.cursor]
        self.cursor = (self.cursor + 1) % len(self.nodes)

        node.setVolume_(float(volume))
        node.setPan_(float(pan))

        # Options 2 = AVAudioPlayerNodeBufferInterrupts (restart this node).
        node.scheduleBuffer_atTime_options_completionHandler_(
            buf, None, 2, None
        )

        if not node.isPlaying():
            node.play()

    def silence(self):
        for node in self.nodes:
            try:
                node.stop()
                node.play()
            except Exception:
                pass

    def info(self):
        out = {'rate': self.rate, 'restarts': self.restarts}

        try:
            session = self.session
            out['session_rate'] = float(session.sampleRate())
            out['io_buffer_ms'] = float(session.IOBufferDuration()) * 1000.0
            out['output_latency_ms'] = float(session.outputLatency()) * 1000.0

            outputs = session.currentRoute().outputs()

            if outputs.count() > 0:
                port = outputs.objectAtIndex_(0)
                out['port'] = str(port.portName())
                out['port_type'] = str(port.portType())
        except Exception:
            pass

        return out


def _inst_sample(inst, t, f, dur, side):
    """One sample of an instrument. `side` is -1 (left) or +1 (right)."""
    two_pi = 2.0 * math.pi

    if inst == 'flute':
        env = min(1.0, t / 0.06) * max(0.0, 1.0 - t / dur) ** 0.6
        tone = (
            math.sin(two_pi * f * t)
            + 0.12 * math.sin(two_pi * 2.0 * f * t)
            + 0.04 * math.sin(two_pi * 3.0 * f * t)
        )
        breath = (random.random() - 0.5) * 0.08
        return (tone * 0.9 + breath) * env

    if inst == 'bell':
        env = math.exp(-4.5 * t / dur) * min(1.0, t / 0.003)
        index = 2.2 * math.exp(-5.0 * t)
        tone = math.sin(
            two_pi * f * t + index * math.sin(two_pi * f * 1.4 * t)
        )
        tone += 0.35 * math.sin(two_pi * f * 2.76 * t) * math.exp(-8.0 * t)
        return tone * 0.55 * env

    if inst == 'marimba':
        env = min(1.0, t / 0.002)
        tone = (
            math.sin(two_pi * f * t) * math.exp(-9.0 * t)
            + 0.35 * math.sin(two_pi * f * 4.0 * t) * math.exp(-26.0 * t)
            + 0.12 * math.sin(two_pi * f * 10.0 * t) * math.exp(-60.0 * t)
        )
        return tone * 0.8 * env

    if inst == 'organ':
        attack = min(1.0, t / 0.015)
        release = min(1.0, max(0.0, dur - t) / 0.08)
        tone = (
            1.0 * math.sin(two_pi * f * t)
            + 0.7 * math.sin(two_pi * f * 2.0 * t)
            + 0.5 * math.sin(two_pi * f * 3.0 * t)
            + 0.3 * math.sin(two_pi * f * 4.0 * t)
            + 0.2 * math.sin(two_pi * f * 6.0 * t)
        ) / 2.7
        # Tremolo runs in opposite phase left vs right for stereo motion.
        trem = 1.0 + 0.25 * side * math.sin(two_pi * 5.5 * t)
        return tone * 0.9 * trem * attack * release

    # 'buzz': saw + square + noise, short decay
    ph = (f * t) % 1.0
    saw = 2.0 * ph - 1.0
    sq = 1.0 if ph < 0.5 else -1.0
    env = math.exp(-7.0 * t / dur) * min(1.0, t / 0.002)
    return (
        0.55 * saw + 0.25 * sq + (random.random() - 0.5) * 0.35
    ) * 1.5 * env


def _render_voice(inst, freq, rate=TONE_SAMPLE_RATE):
    """Render an interleaved L/R 16-bit buffer. L and R are detuned apart."""
    spec = INSTRUMENTS[inst]
    dur = spec['duration']
    det = spec['detune']
    n = int(dur * rate)
    out = array('h')

    for i in range(n):
        t = i / float(rate)

        left = _inst_sample(inst, t, freq * (1.0 - det), dur, -1.0)
        right = _inst_sample(inst, t, freq * (1.0 + det), dur, 1.0)

        out.append(int(max(-1.0, min(1.0, left)) * TONE_PEAK))
        out.append(int(max(-1.0, min(1.0, right)) * TONE_PEAK))

        if i % 4096 == 4095:
            time.sleep(0.001)   # keep the scope responsive while rendering

    return out


def _write_stereo_wav(path, samples, rate=TONE_SAMPLE_RATE):
    w = wavelib.open(path, 'wb')
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(samples.tobytes())
    w.close()


def _voice_stats(samples):
    """Level and stereo statistics of an interleaved L/R 16-bit buffer."""
    n = len(samples) // 2

    if n == 0:
        return {
            'peak_dbfs': -120.0, 'rms_dbfs': -120.0, 'crest_db': 0.0,
            'lr_corr': 0.0, 'side_mid': 0.0, 'frames': 0
        }

    peak = 0.0
    sum_l = sum_r = sum_lr = sum_m = sum_s = 0.0

    for i in range(n):
        l = samples[2 * i] / 32768.0
        r = samples[2 * i + 1] / 32768.0

        peak = max(peak, abs(l), abs(r))
        sum_l += l * l
        sum_r += r * r
        sum_lr += l * r

        mid = (l + r) * 0.5
        side = (l - r) * 0.5
        sum_m += mid * mid
        sum_s += side * side

        if i % 8192 == 8191:
            time.sleep(0.001)

    rms = math.sqrt((sum_l + sum_r) / (2.0 * n))
    peak_db = 20.0 * math.log10(max(peak, 1e-9))
    rms_db = 20.0 * math.log10(max(rms, 1e-9))
    denom = math.sqrt(sum_l * sum_r)

    return {
        'peak_dbfs': peak_db,
        'rms_dbfs': rms_db,
        'crest_db': peak_db - rms_db,
        'lr_corr': (sum_lr / denom) if denom > 0 else 0.0,
        'side_mid': math.sqrt(sum_s / max(sum_m, 1e-12)),
        'frames': n
    }


def _voice_path(inst, sector, mirror):
    name = f'{inst}_{sector:02d}_{"neg" if mirror else "pos"}.wav'
    return os.path.join(TONE_MAP_DIR, name)


def build_tone_voice(inst, sector):
    """Render one instrument/sector voice plus its inverted mirror twin."""
    samples = _render_voice(inst, sector_tone_frequency(sector))
    TONE_VOICE_STATS[(inst, sector)] = _voice_stats(samples)

    if IOS_AUDIO is not None and IOS_AUDIO.ok:
        # Direct iOS path: float32 channel data stays in memory.
        left = array('f', (x / 32768.0 for x in samples[0::2]))
        right = array('f', (x / 32768.0 for x in samples[1::2]))

        TONE_VOICE_DATA[(inst, sector, False)] = (left, right)
        TONE_VOICE_DATA[(inst, sector, True)] = (
            array('f', (-x for x in left)),
            array('f', (-x for x in right))
        )
    else:
        # sound.Player fallback: WAV files on disk.
        _write_stereo_wav(_voice_path(inst, sector, False), samples)

        inverted = array('h', (-x for x in samples))
        _write_stereo_wav(_voice_path(inst, sector, True), inverted)

    TONE_MAP_READY.add((inst, sector))


def _prebuild_tone_map():
    for inst in INSTRUMENT_ORDER:
        for sector in range(SECTOR_COUNT):
            try:
                build_tone_voice(inst, sector)
            except Exception as exc:
                _audio_error(f'build {inst} S{sector}: {exc}')


def start_tone_prebuild():
    """Start direct iOS audio, then render all voices in the background."""
    global TONE_MAP_DIR, TONE_MAP_PREBUILD_STARTED, IOS_AUDIO

    if TONE_MAP_PREBUILD_STARTED:
        return

    TONE_MAP_PREBUILD_STARTED = True

    engine = IOSAudioEngine(TONE_SAMPLE_RATE, IOS_NODE_COUNT)

    if engine.start():
        IOS_AUDIO = engine
        TONE_MAP_STATE['backend'] = 'ios'
    elif sound is not None:
        TONE_MAP_STATE['backend'] = 'snd'
        TONE_MAP_DIR = tempfile.mkdtemp(prefix='twins_tonemap_')
        print(f"iOS audio unavailable ({engine.error}); using sound.Player")
    else:
        TONE_MAP_STATE['backend'] = 'none'
        TONE_MAP_STATE['error'] = engine.error or 'no audio backend'
        print(f"NO AUDIO BACKEND: {engine.error}")
        return

    print(
        f"AUDIO: {TONE_MAP_STATE['backend']} | {DEVICE_MODEL} | "
        f"{'iPhone14,2 profile' if USE_IPHONE_14_2_PROFILE else 'basic'} | "
        f"{TONE_SAMPLE_RATE} Hz stereo"
    )

    threading.Thread(target=_prebuild_tone_map, daemon=True).start()


def get_tone_player(inst, sector, mirror=False):
    """Round-robin a pooled player so retriggered notes can overlap."""
    if sound is None or (inst, sector) not in TONE_MAP_READY:
        return None

    key = (inst, sector, bool(mirror))
    pool = TONE_MAP_PLAYERS.get(key)

    if pool is None:
        path = _voice_path(inst, sector, mirror)
        pool = [sound.Player(path) for _ in range(TONE_VOICES_PER_NOTE)]
        TONE_MAP_PLAYERS[key] = pool
        TONE_MAP_CURSOR[key] = 0

    idx = TONE_MAP_CURSOR[key]
    TONE_MAP_CURSOR[key] = (idx + 1) % len(pool)
    return pool[idx]


_AUDIO_ERRORS_SEEN = set()


def _audio_error(message):
    """Record an audio error and print each distinct message once."""
    TONE_MAP_STATE['error'] = message

    if message not in _AUDIO_ERRORS_SEEN:
        _AUDIO_ERRORS_SEEN.add(message)
        print(f"AUDIO ERROR: {message}")


def play_voice(inst, sector, mirror, volume, pan):
    """Play one voice on the active backend (direct iOS audio preferred)."""
    if (inst, sector) not in TONE_MAP_READY:
        return

    if IOS_AUDIO is not None and IOS_AUDIO.ok:
        key = (inst, sector, bool(mirror))
        data = TONE_VOICE_DATA.get(key)

        if data is not None:
            IOS_AUDIO.play(key, data, volume, pan)

        return

    player = get_tone_player(inst, sector, mirror)

    if player is None:
        return

    player.stop()
    player.volume = volume

    try:
        player.pan = pan
    except Exception:
        pass

    player.play()


def trigger_tone_note(inst, sector, volume, pan):
    """Play the voice plus its negative-polarity mirror twin."""
    blend = max(0.0, min(1.0, CEPTRE_MIRROR_BLEND))

    mirror_volume = (
        volume * blend
        if TONE_MAP_MIRROR_ENABLED and CEPTRE_MIRROR_ACTIVE
        else 0.0
    )

    TONE_MAP_STATE['volume'] = volume
    TONE_MAP_STATE['mirror_volume'] = -mirror_volume  # signed (negative)

    try:
        for mirror, vol in ((False, volume), (True, mirror_volume)):
            if vol <= 0.0:
                continue

            play_voice(inst, sector, mirror, vol, pan)
    except Exception as exc:
        _audio_error(f'play: {exc}')


def _evaluate_behaviour(levels):
    """Classify what the rotor / RMS is doing right now."""
    st = BEHAVIOUR_STATE
    active = sum(1 for lv in levels if lv > TONE_MAP_MIN_LEVEL)
    st['active'] = active

    if active == 0:
        return 'IDLE'

    trend = list(BEHAVIOUR_RMS_TREND)

    if len(trend) < 6:
        return 'STEADY'

    third = max(2, len(trend) // 3)
    slope = (
        sum(trend[-third:]) / third
        - sum(trend[:third]) / third
    )

    jitter = sum(
        abs(trend[i] - trend[i - 1]) for i in range(1, len(trend))
    ) / (len(trend) - 1)

    st['slope'] = slope
    st['jitter'] = jitter

    if (
        jitter > BEHAVIOUR_CHAOS_JITTER
        or EXTERNAL_INTERFERENCE_DETECTED
        or PWR_DOWN_ACTIVE
    ):
        return 'CHAOS'

    if active >= BEHAVIOUR_CLUSTER_SECTORS:
        return 'CLUSTER'

    if slope > BEHAVIOUR_SLOPE_THRESHOLD:
        return 'SURGE'

    if slope < -BEHAVIOUR_SLOPE_THRESHOLD:
        return 'FADE'

    return 'STEADY'


def update_rotor_behaviour(levels, rms):
    """Observe the rotor/RMS and pick the instrument (with hysteresis)."""
    st = BEHAVIOUR_STATE
    now = time.time()

    if now - st['last_eval'] < BEHAVIOUR_EVAL_INTERVAL:
        return st['behaviour']

    st['last_eval'] = now
    BEHAVIOUR_RMS_TREND.append(tone_level_norm(rms['out']))

    candidate = _evaluate_behaviour(levels)

    if candidate == st['candidate']:
        st['count'] += 1
    else:
        st['candidate'] = candidate
        st['count'] = 1

    if st['count'] >= BEHAVIOUR_HOLD and candidate != st['behaviour']:
        st['behaviour'] = candidate
        st['changes'] += 1

    st['instrument'] = BEHAVIOUR_INSTRUMENT[st['behaviour']]
    CODEC_MODEL.observe_tick(
        st['behaviour'],
        BEHAVIOUR_RMS_TREND[-1],
        st['slope'],
        st['active']
    )
    return st['behaviour']


def get_acoustic_scale():
    """Volume / stereo width / beat stride for the selected diameter."""
    prof = ACOUSTIC_PROFILES[ACOUSTIC_PROFILE_INDEX]
    ratio = max(0.0, prof['diameter_mm'] / ACOUSTIC_REFERENCE_MM)

    return {
        'enabled': prof['enabled'],
        'volume': ratio ** ACOUSTIC_VOLUME_EXPONENT,
        'width': ratio ** ACOUSTIC_WIDTH_EXPONENT,
        'stride': prof['stride'],
        'label': prof['label']
    }


def silence_tone_map():
    """Stop every tone that is currently sounding."""
    if IOS_AUDIO is not None and IOS_AUDIO.ok:
        IOS_AUDIO.silence()

    for pool in TONE_MAP_PLAYERS.values():
        for player in pool:
            try:
                player.stop()
            except Exception:
                pass


def set_acoustic_profile(index):
    global ACOUSTIC_PROFILE_INDEX

    index = max(0, min(len(ACOUSTIC_PROFILES) - 1, int(index)))
    ACOUSTIC_PROFILE_INDEX = index
    CODEC_MODEL.record_control('diameter', ACOUSTIC_PROFILES[index]['label'])

    if not ACOUSTIC_PROFILES[index]['enabled']:
        silence_tone_map()
        TONE_MAP_STATE['volume'] = 0.0
        TONE_MAP_STATE['mirror_volume'] = 0.0


def update_tone_map():
    """
    Called every frame.

    Rhythm: each mirror bar's ripple is sin(rate * rotor + i * spread); its
    peaks are the onsets. Every onset plays the pitch of the sector under the
    rotor, in the instrument chosen from the observed rotor behaviour, with
    stereo placement from sector position and bar position.
    """
    if not TONE_MAP_ENABLED:
        return

    sector = get_rotor_sector()
    levels = compute_sector_rms()
    rms = compute_lband_rms()

    TONE_MAP_STATE['sector'] = sector
    TONE_MAP_STATE['freq'] = sector_tone_frequency(sector)
    TONE_MAP_STATE['ready'] = len(TONE_MAP_READY)

    update_rotor_behaviour(levels, rms)
    instrument = BEHAVIOUR_STATE['instrument']
    TONE_MAP_STATE['instrument'] = instrument
    acoustic = get_acoustic_scale()

    last_k = MIRROR_RHYTHM_STATE['last_k']
    bar_levels = MIRROR_RHYTHM_STATE['bar_levels']
    half = (MIRROR_BAR_COUNT - 1) / 2.0

    for i in range(MIRROR_BAR_COUNT):
        # Index of the ripple peak this bar has most recently passed.
        k = math.floor(
            (
                MIRROR_RIPPLE_RATE * LBAND_ROTOR_PHASE_TOTAL
                + i * MIRROR_RIPPLE_SPREAD
                - math.pi / 2.0
            ) / (2.0 * math.pi)
        )

        previous = last_k[i]
        last_k[i] = k

        if previous is None or k == previous:
            continue

        MIRROR_RHYTHM_STATE['onsets'] += 1
        MIRROR_RHYTHM_STATE['last_bar'] = i

        # Diameter profile: 1 mm is silent; 4 mm keeps every 2nd bar.
        if not acoustic['enabled'] or i % acoustic['stride']:
            CODEC_MODEL.count('suppressed_by_diameter')
            continue

        level = levels[sector]

        if level <= TONE_MAP_MIN_LEVEL:
            CODEC_MODEL.count('silent_sector_onsets')
            continue

        sector_norm = tone_level_norm(level)
        global_norm = tone_level_norm(rms['out'])
        bar_level = bar_levels[i] if i < len(bar_levels) else sector_norm
        accent = 1.2 if i == 0 else 1.0

        volume = (
            TONE_MAP_MAX_VOLUME
            * (0.25 + 0.75 * sector_norm)
            * (0.7 + 0.3 * global_norm)
            * (0.6 + 0.4 * min(1.0, bar_level))
            * accent
        )

        # Multiplier from the detected RMS (sector and overall LBand level).
        multiplier = 1.0 + TONE_MAP_RMS_GAIN * (
            0.5 * sector_norm + 0.5 * global_norm
        )

        TONE_MAP_STATE['multiplier'] = multiplier
        raw_volume = volume * multiplier
        limited = raw_volume > 1.0
        volume = max(0.0, min(1.0, raw_volume))
        volume *= acoustic['volume']

        # Stereo: sector position on the scope plus the bar's position.
        centre_angle = (sector + 0.5) * 360.0 / SECTOR_COUNT
        pan = (
            0.65 * math.cos(math.radians(centre_angle))
            + 0.35 * ((i - half) / half)
        )
        pan = max(-1.0, min(1.0, pan * acoustic['width']))

        trigger_tone_note(instrument, sector, volume, pan)
        CODEC_MODEL.observe_note(instrument, sector, volume, pan, limited)


# ===================== ASSESSMENT / UTILITIES =====================
def continuous_assessment():
    global twin_pulse_alternator, MEMORY_DEBT, SIGNAL_WHITE
    global last_measurement_time

    twin_pulse_alternator = (twin_pulse_alternator + 1) % 2

    if PWR_DOWN_ACTIVE:
        MEMORY_DEBT = min(
            MAX_MEMORY_DEBT,
            MEMORY_DEBT + 2.5
        )

        SIGNAL_WHITE = random.random() < 0.12

        if SIGNAL_WHITE:
            update_bbc_time_via_induction(white_signal=True)

    if MEMORY_DEBT > MAX_MEMORY_DEBT:
        MEMORY_DEBT *= 0.75

    if (
        MEASUREMENT_MODE
        and BBC_TIME in ["09:25", "09:30"]
        and BBC_TIME != last_measurement_time
    ):
        last_measurement_time = BBC_TIME

        if CONSOLE_PRINTING:
            print(f"RESPONSIVE MEASUREMENT @ {BBC_TIME}")

    auto_channel_attenuation()
    detect_external_interference()


def consume_memory_budget(amount=1.0):
    global MEMORY_DEBT
    MEMORY_DEBT = min(
        MAX_MEMORY_DEBT,
        MEMORY_DEBT + amount
    )


def get_sector(bearing):
    return int(((bearing % 360) / 360.0) * SECTOR_COUNT)


def generate_mac_address(seed=None):
    rng = random.Random(seed) if seed is not None else random

    return ":".join(
        f"{rng.randint(0, 255):02X}"
        for _ in range(6)
    )


def get_blip_maturity(mac):
    return blip_maturity.get(mac, 0.18)


def increase_blip_maturity(mac, amount=0.06):
    blip_maturity[mac] = min(
        1.0,
        blip_maturity.get(mac, 0.18) + amount
    )


def measure_current_interference():
    m = max(mag_history) if mag_history else 0
    a = max(acoustic_history) if acoustic_history else 0
    return m * 0.55 + a * 0.45


def auto_channel_attenuation():
    interference = measure_current_interference()
    high = interference > 24

    factor = 0.70 if PWR_DOWN_ACTIVE else (
        0.80 if high or EXTERNAL_INTERFERENCE_DETECTED
        else 1.03
    )

    for key in io_attenuation:
        io_attenuation[key] = max(
            0.20,
            io_attenuation[key] * factor
        )

    return io_attenuation


def detect_external_interference():
    global EXTERNAL_INTERFERENCE_DETECTED, MIC_SWITCHED_TO_BLIPS

    if len(chatter_events) > 8:
        EXTERNAL_INTERFERENCE_DETECTED = True

        if random.random() < 0.3:
            MIC_SWITCHED_TO_BLIPS = True

        return True

    return False


def characteristics_surfing(mac, current_scope):
    scopes = [
        'yband', 'ble', 'uwb', 'ir', 'infrasonic',
        'dolphin', 'ultra_dolphin', 'optical',
        'subvocal', 'chain', 'measurement', 'windsock'
    ]

    best, best_score = current_scope, float('inf')

    for scope in scopes:
        score = io_attenuation.get(scope, 1.0) * (
            0.7 if scope == current_scope else 1.0
        )

        if score < best_score:
            best, best_score = scope, score

    return best


def operate_twins_search_engine(mac, query=""):
    current_time = BBC_TIME

    secure_url = (
        f"{SECURE_ELEMENT_BASE_URL}{mac.replace(':', '')[:12]}"
    )

    if query:
        twins_search_log.append({
            "timestamp": time.time(),
            "mac": mac[:8],
            "query": query,
            "stored_at": current_time
        })

    return {
        "time": current_time,
        "secure_element_url": secure_url
    }


def trigger_nokia_fuck_you_signature(
    mac,
    reason="external_interference"
):
    global EXTERNAL_INTERFERENCE_DETECTED

    EXTERNAL_INTERFERENCE_DETECTED = True

    if CONSOLE_PRINTING:
        print(
            f"SIGNATURE PULSED LIGHT RINGER — "
            f"{reason} — {mac[:8]}"
        )

    packet = bytearray(101)
    packet[0:4] = b'\xDE\xAD\xBE\xEF'
    packet[20:22] = b'\x09\x30'

    for i in range(22, 101):
        packet[i] = (i * 31 + 7) % 256

    return packet


def generate_ble_advertising_token(
    mac,
    share_value=1,
    secure_url=None,
    byte_code=None
):
    global unity_share_counter
    unity_share_counter += 1

    if CONSOLE_PRINTING:
        print(
            f"LOCAL SIMULATION TOKEN UNITY-{unity_share_counter:05d}"
        )

    return {
        "share_id": f"UNITY-{unity_share_counter:05d}"
    }


def update_bbc_time_via_induction(white_signal=False):
    global BBC_TIME, SIGNAL_WHITE

    BBC_TIME = "09:30"

    if white_signal:
        SIGNAL_WHITE = True

    return (
        CLASSIC_TONE_FREQUENCY,
        CLASSIC_TONE_FREQUENCY * 1.05946
    )


def apply_gate_magic(signal_level, microwave_detected=False):
    if not NOISE_GATE_ACTIVE:
        return signal_level

    threshold = 0.35 if microwave_detected else 0.55

    if signal_level < threshold:
        return 0.0

    return signal_level * 0.92


def handle_intrusive_noise(freq, sector):
    if (
        EXTERNAL_INTERFERENCE_DETECTED
        or MEMORY_DEBT > MAX_MEMORY_DEBT * 0.45
        or PWR_DOWN_ACTIVE
    ):
        chained = freq * (
            0.55 + math.sin(write_tone_map_phase * 1.9) * 0.13
        )

        interrupted = chained * random.uniform(0.28, 0.58)
        consume_memory_budget(1.8)

        return interrupted

    return freq


def generate_responsive_measurement(diameter_miles=1200):
    base = random.uniform(-1800, 2200)
    fluctuation = math.sin(write_tone_map_phase * 3.7) * 450

    value = (
        base + fluctuation
    ) * (diameter_miles / 1200.0)

    if random.random() < 0.35:
        value = -abs(value) * random.uniform(0.6, 1.3)

    return round(value, 2)


def create_101_byte_response(
    mac,
    bearing,
    freq,
    sector,
    scope_type
):
    pkt = bytearray(101)
    pkt[0:4] = b'\xAA\xBB\xCC\xDD'

    try:
        mac_bytes = bytes.fromhex(mac.replace(":", ""))[:6]
        pkt[4:10] = mac_bytes.ljust(6, b'\x00')
    except (ValueError, AttributeError):
        pkt[4:10] = b'\x00' * 6

    pkt[10] = int(freq) % 256
    pkt[11] = sector % 256
    pkt[12:14] = int(bearing % 65536).to_bytes(2, 'big')
    pkt[14] = sector % 256

    scope_map = {
        'yband': 1,
        'ble': 2,
        'uwb': 3,
        'ir': 4,
        'infrasonic': 5,
        'dolphin': 6,
        'ultra_dolphin': 7,
        'optical': 8,
        'subvocal': 9,
        'chain': 10,
        'measurement': 11,
        'windsock': 12
    }

    pkt[15] = scope_map.get(scope_type, 0)
    pkt[16:20] = int(time.time()).to_bytes(
        4, 'big', signed=False
    )
    pkt[20:22] = b'\x09\x30'

    modulation = generate_optical_sine_wave_93nm(
        freq,
        sector,
        0.9
    )

    for i in range(22, 101):
        base = (
            i * 17 + sector + int(freq) % 256
        ) % 256

        pkt[i] = int(
            base * (0.55 + 0.45 * modulation)
        ) % 256

    return pkt


def create_optics_only_response(
    mac,
    bearing,
    freq,
    sector
):
    if CONSOLE_PRINTING:
        print(
            f"PURE OPTICS SIMULATION (0 bytes) → {mac[:8]}"
        )

    return None


def propagate_chained_induction(
    source_mac,
    freq,
    sector,
    diameter_miles=1200
):
    if not INDUCTION_CHAIN:
        return []

    responses = []

    for i, mac in enumerate(INDUCTION_CHAIN):
        response = {
            "mac": mac,
            "freq": freq * (0.90 + i * 0.035),
            "sector": (sector + i) % SECTOR_COUNT,
            "timestamp": time.time(),
            "source": source_mac,
            "diameter_miles": diameter_miles
        }

        CHAINED_RESPONSES[mac].append(response)

        while len(CHAINED_RESPONSES[mac]) > 6:
            CHAINED_RESPONSES[mac].pop(0)

        responses.append(response)

    consume_memory_budget(1.8)
    return responses


# ===================== INDUCTION PIPELINE =====================
def derive_soundform_from_induction(
    freq,
    sector,
    scope_type='yband',
    orbital_km=0,
    diameter_miles=1200,
    bearing=0,
    wind_direction=0
):
    global last_induction_time, INFRASONIC_ACTIVE
    global DOLPHIN_TONE_ACTIVE, ULTRA_DOLPHIN_ACTIVE

    is_infrasonic = freq < INFRASONIC_THRESHOLD
    is_ultra = freq >= ULTRA_DOLPHIN_FREQ_MIN
    is_dolphin = (
        DOLPHIN_FREQ_MIN <= freq < ULTRA_DOLPHIN_FREQ_MIN
    )

    if is_infrasonic:
        INFRASONIC_ACTIVE = True

    if is_ultra:
        ULTRA_DOLPHIN_ACTIVE = True
    elif is_dolphin:
        DOLPHIN_TONE_ACTIVE = True

    last_induction_time = time.time()

    base, temple_noise = derive_dolphin_sine_wave(
        freq,
        sector,
        scope_type,
        diameter_miles,
        bearing,
        wind_direction
    )

    freq = handle_intrusive_noise(freq, sector)
    consume_memory_budget(1.6)

    if (
        scope_type in ['subvocal', 'chain', 'dolphin']
        or EXTERNAL_INTERFERENCE_DETECTED
    ):
        propagate_chained_induction(
            "ELECTRICAL_BELL",
            freq,
            sector
        )

    if is_infrasonic:
        base *= 0.60

    if orbital_km > 0:
        base *= max(0.55, 1.0 - orbital_km / 900.0)

    if SIGNAL_WHITE:
        base *= 0.55

    gated = apply_gate_magic(
        base / 1000.0,
        EXTERNAL_INTERFERENCE_DETECTED
        or scope_type in ['ir', 'uwb']
    ) * 1000.0

    # Every selected primary soundform is processed by Cèptre.
    primary = process_ceptre_wave(
        gated,
        freq,
        sector,
        scope_type
    )

    response = primary['output'] * 1.6180339887

    if is_infrasonic:
        response *= 0.68

    if is_ultra:
        response *= 1.12

    if orbital_km > 0:
        response *= max(0.50, 1.0 - orbital_km / 1000.0)

    # The secondary response is also processed by Cèptre.
    secondary = process_ceptre_wave(
        response,
        freq,
        (sector + 1) % SECTOR_COUNT,
        scope_type
    )

    return (
        [primary['output']],
        round(secondary['output'], 1),
        {
            'primary': primary,
            'response': secondary
        },
        freq > SUPERSONIC_THRESHOLD
    )


def start_receiver_playback(mac, byte_code, search_response):
    if not CONSOLE_PRINTING:
        return

    mode = (
        "PURE OPTICS SIMULATION"
        if byte_code is None
        else "101-BYTE LOCAL SIMULATION"
    )

    print(
        f"RECEIVER PLAYBACK — {mode} | {mac[:8]} | {BBC_TIME}"
    )


def trigger_music_filesystem_response(
    mac,
    bearing,
    pos,
    sector,
    freq,
    scope_type='yband',
    is_new_blip=False,
    ear='left',
    orbital_km=0,
    diameter_miles=1200,
    wind_direction=0
):
    global current_music_fs_path, EXTERNAL_INTERFERENCE_DETECTED
    global MIC_SWITCHED_TO_BLIPS, SIGNAL_WHITE

    is_infrasonic = freq < INFRASONIC_THRESHOLD
    is_ultra = freq >= ULTRA_DOLPHIN_FREQ_MIN
    is_dolphin = (
        DOLPHIN_FREQ_MIN <= freq < ULTRA_DOLPHIN_FREQ_MIN
    )

    surfed_scope = characteristics_surfing(mac, scope_type)

    if is_ultra:
        surfed_scope = 'ultra_dolphin'
    elif is_dolphin:
        surfed_scope = 'dolphin'
    elif scope_type == 'subvocal':
        surfed_scope = 'subvocal'
    elif OPTICS_PREFERRED:
        surfed_scope = 'optical'

    scope_type = surfed_scope

    if scope_type == 'subvocal' or is_dolphin:
        register_subvocal_with_signature(mac)

    lookahead_ceptre = None

    if PRE_RENDER_LOOKAHEAD:
        _, _, lookahead_ceptre, _ = derive_soundform_from_induction(
            freq * 1.04,
            sector,
            scope_type,
            orbital_km,
            diameter_miles,
            bearing,
            wind_direction
        )

    intro_tones, response_tone, ceptre_result, _ = (
        derive_soundform_from_induction(
            freq,
            sector,
            scope_type,
            orbital_km,
            diameter_miles,
            bearing,
            wind_direction
        )
    )

    primary = ceptre_result['primary']
    secondary = ceptre_result['response']

    path = (
        f"/inductions/{scope_type}_{sector:02d}_"
        f"{int(bearing)}_{mac[:8]}"
    )

    current_music_fs_path = path

    if (
        PURE_OPTICS_ONLY
        and scope_type in ['optical', 'dolphin', 'ultra_dolphin']
    ):
        byte_code = create_optics_only_response(
            mac, bearing, freq, sector
        )
    else:
        byte_code = create_101_byte_response(
            mac, bearing, freq, sector, scope_type
        )

    search_response = operate_twins_search_engine(
        mac,
        query=f"induction_{sector}"
    )

    secure_url = search_response["secure_element_url"]

    if is_new_blip:
        generate_ble_advertising_token(
            mac,
            secure_url=secure_url,
            byte_code=byte_code
        )

    update_bbc_time_via_induction(
        white_signal=SIGNAL_WHITE
    )

    if detect_external_interference() or EXTERNAL_INTERFERENCE_DETECTED:
        byte_code = trigger_nokia_fuck_you_signature(
            mac,
            reason="simulation interference state"
        )

    start_receiver_playback(
        mac,
        byte_code,
        search_response
    )

    active_music_inductions[mac] = {
        'path': path,
        'bearing': bearing,
        'freq': freq,
        'scope_type': scope_type,
        'start_time': time.time(),
        'fallout': 1.0,
        'pos': pos,
        'infrasonic': is_infrasonic,
        'dolphin_tone_map': is_dolphin or is_ultra,
        'ultra_dolphin': is_ultra,
        'optical': True,
        'electrical_sine': True,
        'nm93_modulation': scope_type != 'optical',
        'subvocal': scope_type == 'subvocal',
        'chain': (
            scope_type == 'chain'
            or len(INDUCTION_CHAIN) > 1
        ),
        'pure_optics': (
            PURE_OPTICS_ONLY
            and scope_type in ['optical', 'dolphin', 'ultra_dolphin']
        ),
        'electrical_bell': True,
        'diameter_miles': diameter_miles,
        'pwr_down': PWR_DOWN_ACTIVE,
        'white_signal': SIGNAL_WHITE,
        'measurement': (
            scope_type == 'measurement'
            or (
                MEASUREMENT_MODE
                and BBC_TIME in ["09:25", "09:30"]
            )
        ),
        'measurement_value': (
            generate_responsive_measurement(diameter_miles)
            if MEASUREMENT_MODE
            and BBC_TIME in ["09:25", "09:30"]
            else None
        ),
        'windsock': scope_type == 'windsock' or WINDSOCK_ACTIVE,
        'doppler_active': WINDSOCK_ACTIVE,
        'surfing': True,
        'bbc_time': BBC_TIME,
        'byte_code': byte_code,
        'ble_advertised_url': secure_url,
        'receiver_playback': True,
        'mic_switched_to_blips': MIC_SWITCHED_TO_BLIPS,

        # Cèptre results for this induction.
        'ceptre_active': CEPTRE_MIRROR_ACTIVE,
        'ceptre_processed': True,
        'ceptre_color': primary['color'],
        'ceptre_attenuation': primary['attenuation'],
        'ceptre_original': primary['original'],
        'ceptre_mirrored': primary['mirrored'],
        'ceptre_llm_wave': primary['llm_wave'],
        'ceptre_output': primary['output'],
        'ceptre_vibration': primary['vibration'],
        'ceptre_response': secondary['output'],
        'ceptre_response_vibration': secondary['vibration'],
        'ceptre_lookahead': lookahead_ceptre,
        'ceptre_result': ceptre_result
    }

    if CONSOLE_PRINTING:
        print(
            f"INDUCTION → {scope_type.upper()} | "
            f"CÈPTRE={primary['output']:.2f} | "
            f"attenuation={primary['attenuation']:.2f}"
        )

    return path, intro_tones[0], response_tone


# ===================== TEST BLIPS =====================
def generate_timing_belt_pulse(
    mac,
    base_freq,
    maturity,
    orbital_km=0,
    diameter_miles=1200
):
    global DOLPHIN_TONE_ACTIVE, ULTRA_DOLPHIN_ACTIVE

    alt = 1.0 if twin_pulse_alternator % 2 == 0 else 0.93
    ph = 1.0 + 0.055 * math.sin(write_tone_map_phase * 1.65)
    sp = 0.96 + spinning_plate_speed * 0.11
    mat = 0.89 + maturity * 0.22

    try:
        mac_seed = int(mac[-2:], 16)
    except (ValueError, TypeError):
        mac_seed = 0

    ble = (
        0.97 + 0.06 * (
            (int(twin_pulse_alternator) + mac_seed) % 3
        )
        if BLE_COMPLIANT_MODE
        else 1.0
    )

    dist = (
        max(0.60, 1.0 - orbital_km / 1100.0)
        if orbital_km > 0
        else 1.0
    )

    timed = base_freq * alt * ph * sp * mat * ble * dist

    if timed >= ULTRA_DOLPHIN_FREQ_MIN:
        ULTRA_DOLPHIN_ACTIVE = True
    elif timed >= DOLPHIN_FREQ_MIN:
        DOLPHIN_TONE_ACTIVE = True

    return max(8.0, min(48000.0, timed))


def create_test_blip(
    center,
    radius,
    mac,
    diameter_miles=1200
):
    angle = random.uniform(0, 360)

    pos = Point(
        center.x + radius * 0.62 * math.cos(math.radians(angle)),
        center.y + radius * 0.62 * math.sin(math.radians(angle))
    )

    freq = random.uniform(380, 38000)

    timed_freq = generate_timing_belt_pulse(
        mac,
        freq,
        get_blip_maturity(mac)
    )

    if timed_freq >= ULTRA_DOLPHIN_FREQ_MIN:
        scope = 'ultra_dolphin'
    elif timed_freq >= DOLPHIN_FREQ_MIN:
        scope = 'dolphin'
    else:
        scope = 'optical' if OPTICS_PREFERRED else 'ble'

    return {
        'mac': mac,
        'bearing': angle,
        'pos': pos,
        'freq': timed_freq,
        'scope_type': scope,
        'diameter_miles': diameter_miles
    }


def run_increasing_test_blips(scene):
    global CALIBRATION_MODE, last_calibration_time

    if time.time() - last_calibration_time < CALIBRATION_INTERVAL:
        return

    CALIBRATION_MODE = True
    last_calibration_time = time.time()

    if CONSOLE_PRINTING:
        print("LOCAL TEST BLIPS RUNNING")

    for _ in range(3):
        if TWIN1_MAC:
            blip = create_test_blip(
                scene.scope_center,
                scene.scope_radius,
                TWIN1_MAC
            )

            scene.trigger_predictable_feedback(
                blip['mac'],
                blip['bearing'],
                blip['pos'],
                blip['freq'],
                scope_type=blip['scope_type'],
                is_new_blip=True
            )

            increase_blip_maturity(blip['mac'])

    auto_channel_attenuation()
    CALIBRATION_MODE = False


# ===================== VISUAL EFFECTS =====================
class SunbeamEffect:
    def __init__(
        self,
        blip_pos,
        bearing,
        freq,
        color=None,
        scope_type='yband',
        vibration=0.0
    ):
        self.center = blip_pos
        self.bearing = math.radians(bearing)
        self.freq = freq
        self.color = color or '#44bbff'
        self.scope_type = scope_type
        self.vibration = vibration
        self.age = 0
        self.duration = 380

    def update(self):
        self.age += 1
        return self.age <= self.duration

    def draw(self):
        if self.age > self.duration:
            return False

        alpha = max(
            0.5,
            1.0 - self.age / self.duration
        )

        vibration_offset = (
            math.sin(self.age * CEPTRE_VIBRATION_RATE)
            * min(abs(self.vibration), 12.0)
        )

        stroke(self.color, alpha)
        stroke_weight(
            5.5 + min(abs(self.vibration) * 0.05, 2.0)
        )

        radius = self.age * 5.5 + vibration_offset
        dx = math.cos(self.bearing) * radius
        dy = math.sin(self.bearing) * radius

        line(
            self.center.x,
            self.center.y,
            self.center.x + dx,
            self.center.y + dy
        )

        return True


# ===================== CODEC LEARNING MODEL / REPORT =====================
# A small online-learning model that watches how the codec behaves while it is
# exposed to control (diameter slider, toggles, taps) and learns:
#   1. a Markov model of rotor-behaviour transitions,
#   2. an NLMS predictor of the next RMS level (vs. a persistence baseline),
#   3. the measured level response of each diameter profile.
# Learned parameters persist between sessions in a JSON file. The Report button
# turns the live values into an expert-style written report. The text is
# rule-based (templates driven by the numbers), not generated by an LLM.
MODEL_FILE = 'twins_codec_model.json'
BEHAVIOUR_NAMES = ['IDLE', 'STEADY', 'SURGE', 'FADE', 'CLUSTER', 'CHAOS']
MODEL_NLMS_RATE = 0.25
MODEL_MARKOV_ALPHA = 0.5
MODEL_MIN_TICKS = 40
MODEL_SAVE_INTERVAL = 30.0
REPORT_BIT_DEPTH = 16
REPORT_CHANNELS = 2


def _docs_dir():
    path = os.path.expanduser('~/Documents')
    return path if os.path.isdir(path) else tempfile.gettempdir()


class RunningStat:
    """Welford running mean / variance / min / max."""

    def __init__(self):
        self.n = 0
        self.mean = 0.0
        self.m2 = 0.0
        self.lo = 0.0
        self.hi = 0.0

    def add(self, x):
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        self.m2 += delta * (x - self.mean)

        if self.n == 1:
            self.lo = self.hi = x
        else:
            self.lo = min(self.lo, x)
            self.hi = max(self.hi, x)

    @property
    def std(self):
        return math.sqrt(self.m2 / (self.n - 1)) if self.n > 1 else 0.0

    def to_dict(self):
        return {'n': self.n, 'mean': self.mean, 'm2': self.m2,
                'lo': self.lo, 'hi': self.hi}

    @classmethod
    def from_dict(cls, d):
        stat = cls()
        stat.n = int(d.get('n', 0))
        stat.mean = float(d.get('mean', 0.0))
        stat.m2 = float(d.get('m2', 0.0))
        stat.lo = float(d.get('lo', 0.0))
        stat.hi = float(d.get('hi', 0.0))
        return stat


class CodecLearningModel:
    def __init__(self):
        # ---- session observations (not persisted) ----
        self.session_start = time.time()
        self.counters = defaultdict(int)
        self.controls = deque(maxlen=80)
        self.dwell = [0.0] * len(ACOUSTIC_PROFILES)
        self.behaviour_time = defaultdict(float)
        self.instrument_notes = defaultdict(int)
        self.note_level = RunningStat()
        self.note_pan = RunningStat()
        self.last_tick = None
        self.prev_behaviour = None
        self.last_save = time.time()
        self._x_prev = None
        self._pred = None
        self._prev_r = None

        # ---- learned parameters (persisted) ----
        self.markov = {
            a: {b: 0 for b in BEHAVIOUR_NAMES} for a in BEHAVIOUR_NAMES
        }
        self.weights = [0.0, 1.0, 0.0, 0.0]   # starts as persistence
        self.err_model = RunningStat()
        self.err_base = RunningStat()
        self.profile_level = [RunningStat() for _ in ACOUSTIC_PROFILES]
        self.lifetime_ticks = 0
        self.loaded_ticks = 0

        self.load()

    # ---- persistence ----
    def _path(self):
        return os.path.join(_docs_dir(), MODEL_FILE)

    def save(self):
        import json

        self.last_save = time.time()

        data = {
            'markov': self.markov,
            'weights': self.weights,
            'err_model': self.err_model.to_dict(),
            'err_base': self.err_base.to_dict(),
            'profiles': {
                prof['label']: self.profile_level[i].to_dict()
                for i, prof in enumerate(ACOUSTIC_PROFILES)
            },
            'lifetime_ticks': self.lifetime_ticks
        }

        try:
            with open(self._path(), 'w', encoding='utf-8') as fh:
                json.dump(data, fh)
        except Exception:
            pass

    def load(self):
        import json

        try:
            with open(self._path(), 'r', encoding='utf-8') as fh:
                data = json.load(fh)

            for a, row in data.get('markov', {}).items():
                for b, count in row.items():
                    if a in self.markov and b in self.markov[a]:
                        self.markov[a][b] = int(count)

            weights = data.get('weights')

            if isinstance(weights, list) and len(weights) == 4:
                self.weights = [float(v) for v in weights]

            self.err_model = RunningStat.from_dict(data.get('err_model', {}))
            self.err_base = RunningStat.from_dict(data.get('err_base', {}))

            for i, prof in enumerate(ACOUSTIC_PROFILES):
                saved = data.get('profiles', {}).get(prof['label'])

                if saved:
                    self.profile_level[i] = RunningStat.from_dict(saved)

            self.lifetime_ticks = int(data.get('lifetime_ticks', 0))
            self.loaded_ticks = self.lifetime_ticks
        except Exception:
            pass

    # ---- observation hooks ----
    def count(self, name, amount=1):
        self.counters[name] += amount

    def record_control(self, kind, detail=''):
        self.controls.append((time.time(), kind, detail))
        self.counters['control:' + kind] += 1

    def observe_note(self, inst, sector, volume, pan, limited):
        level_db = 20.0 * math.log10(max(volume, 1e-6))

        self.note_level.add(level_db)
        self.note_pan.add(abs(pan))
        self.profile_level[ACOUSTIC_PROFILE_INDEX].add(level_db)
        self.instrument_notes[inst] += 1
        self.counters['notes'] += 1

        if limited:
            self.counters['limited'] += 1

    def observe_tick(self, behaviour, r, slope, active):
        now = time.time()
        dt = min(1.0, now - self.last_tick) if self.last_tick else 0.0
        self.last_tick = now

        self.dwell[ACOUSTIC_PROFILE_INDEX] += dt
        self.behaviour_time[behaviour] += dt

        if (
            self.prev_behaviour in self.markov
            and behaviour in self.markov[self.prev_behaviour]
        ):
            self.markov[self.prev_behaviour][behaviour] += 1

        self.prev_behaviour = behaviour

        # NLMS: learn from the error of the previous prediction.
        if (
            self._pred is not None
            and self._x_prev is not None
            and self._prev_r is not None
        ):
            err = r - self._pred
            norm = 1e-3 + sum(v * v for v in self._x_prev)

            for k, v in enumerate(self._x_prev):
                self.weights[k] = max(
                    -3.0,
                    min(3.0, self.weights[k]
                        + MODEL_NLMS_RATE * err * v / norm)
                )

            self.err_model.add(abs(err))
            self.err_base.add(abs(r - self._prev_r))

        x = [1.0, r, slope, active / float(SECTOR_COUNT)]
        pred = sum(w * v for w, v in zip(self.weights, x))

        self._pred = max(0.0, min(1.0, pred))
        self._x_prev = x
        self._prev_r = r

        self.lifetime_ticks += 1
        self.counters['ticks'] += 1

        if now - self.last_save > MODEL_SAVE_INTERVAL:
            self.save()

    # ---- learned quantities ----
    def transition_probs(self, state):
        row = self.markov.get(state)

        if not row:
            return {}

        total = sum(row.values()) + MODEL_MARKOV_ALPHA * len(row)
        return {
            k: (v + MODEL_MARKOV_ALPHA) / total for k, v in row.items()
        }

    def stickiness(self):
        total = sum(sum(row.values()) for row in self.markov.values())
        stay = sum(self.markov[a][a] for a in self.markov)
        return (stay / total) if total else None

    def skill(self):
        if self.err_base.n >= MODEL_MIN_TICKS and self.err_base.mean > 0:
            return 1.0 - self.err_model.mean / self.err_base.mean

        return None


CODEC_MODEL = CodecLearningModel()


def _fmt_dur(seconds):
    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f'{hours:d}:{minutes:02d}:{secs:02d}' if hours else f'{minutes:d}:{secs:02d}'


def _aggregate_voice_stats():
    grouped = {}

    for (inst, sector), st in list(TONE_VOICE_STATS.items()):
        grouped.setdefault(inst, []).append(st)

    rows = {}

    for inst, items in grouped.items():
        n = float(len(items))
        rows[inst] = {
            'n': len(items),
            'dur': INSTRUMENTS[inst]['duration'],
            'peak': max(x['peak_dbfs'] for x in items),
            'rms': sum(x['rms_dbfs'] for x in items) / n,
            'crest': sum(x['crest_db'] for x in items) / n,
            'corr': sum(x['lr_corr'] for x in items) / n,
            'side_mid': sum(x['side_mid'] for x in items) / n,
            'frames': sum(x['frames'] for x in items)
        }

    return rows


def generate_codec_report():
    """Expert-style consumer audio report from the live codec + model."""
    m = CODEC_MODEL
    now = time.time()
    duration = now - m.session_start
    voices = _aggregate_voice_stats()

    rate = TONE_SAMPLE_RATE
    bits = REPORT_BIT_DEPTH
    chans = REPORT_CHANNELS
    kbps = rate * bits * chans / 1000.0
    ready = len(TONE_MAP_READY)
    total = TONE_MAP_STATE['total']
    acoustic = get_acoustic_scale()
    notes = m.counters['notes']
    limited = m.counters['limited']
    ticks = m.counters['ticks']
    control_events = sum(
        v for k, v in m.counters.items() if k.startswith('control:')
    )
    skill = m.skill()
    blend = max(0.0, min(1.0, CEPTRE_MIRROR_BLEND))

    peak_all = max((v['peak'] for v in voices.values()), default=None)
    rms_all = (
        sum(v['rms'] for v in voices.values()) / len(voices)
        if voices else None
    )
    corr_all = (
        sum(v['corr'] for v in voices.values()) / len(voices)
        if voices else None
    )
    twin_db = 20.0 * math.log10(max(1.0 - blend, 1e-6))
    est_programme = (
        m.note_level.mean + rms_all
        if (m.note_level.n and rms_all is not None) else None
    )
    limited_rate = (limited / notes) if notes else 0.0
    enough = ticks >= MODEL_MIN_TICKS

    L = []
    add = L.append

    def head(title):
        add('')
        add(title)
        add('-' * len(title))

    add('TWINS CODEC v13 - CONSUMER AUDIO REPORT')
    add('=' * 40)
    add(time.strftime('Generated  %Y-%m-%d %H:%M:%S'))
    add(f'Session    {_fmt_dur(duration)}')
    add(
        f'Device     {DEVICE_MODEL}'
        f'{" (iPhone 13 Pro)" if IS_IPHONE_14_2 else (" (iPhone14,2 profile applied)" if USE_IPHONE_14_2_PROFILE else "")}'
    )

    # ---- 1. summary --------------------------------------------------------
    head('1. EXECUTIVE SUMMARY')

    if peak_all is not None:
        level_text = (
            f'The worst-case rendered peak is {peak_all:.1f} dBFS, '
            f'which leaves {-peak_all:.1f} dB of headroom.'
        )
    else:
        level_text = (
            'Voices are still rendering, so level figures are not yet '
            'available.'
        )

    add(
        f'The codec is rendering {rate / 1000.0:.1f} kHz, {bits}-bit '
        f'stereo linear PCM at {kbps:,.0f} kbps per voice '
        f'({ready} of {total} voices ready). {level_text}'
    )
    add('')
    add(
        f'Over this session the model logged {notes} notes, {ticks} '
        f'behaviour observations and {control_events} control events. '
        f'The acoustic diameter is set to {acoustic["label"]} '
        f'({acoustic["volume"]:.2f}x volume, {acoustic["width"]:.2f}x '
        f'stereo width).'
    )
    add('')

    if not enough:
        add(
            f'Verdict: too little data for firm conclusions. Keep the '
            f'codec running until at least {MODEL_MIN_TICKS} observations '
            f'have been logged, then regenerate this report.'
        )
    elif est_programme is None:
        add('Verdict: no notes have sounded yet, so delivered level is unknown.')
    else:
        if est_programme > -18.0:
            loudness = 'loud for a consumer device'
        elif est_programme > -30.0:
            loudness = 'comfortably moderate'
        else:
            loudness = 'quiet'

        add(
            f'Verdict: delivered programme level is about '
            f'{est_programme:.1f} dBFS RMS, which is {loudness}, with '
            f'{limited_rate * 100:.0f}% of notes held at the level limit.'
        )

    # ---- 2. consumer spec ----------------------------------------------------
    head('2. CONSUMER AUDIO SPECIFICATION')
    add('Format')
    add(f'  Encoding       linear PCM {bits}-bit, uncompressed WAV')
    add(f'  Channels       {chans} (L and R rendered separately)')
    add(f'  Sample rate    {rate:,} Hz')
    add(f'  Data rate      {kbps:,.0f} kbps per voice')
    ios_info = (
        IOS_AUDIO.info() if (IOS_AUDIO is not None and IOS_AUDIO.ok) else None
    )

    if ios_info:
        add('  Output path    AVAudioEngine (direct iOS)')
        add(f'  Polyphony      {IOS_NODE_COUNT} player nodes')

        if 'session_rate' in ios_info:
            add(f'  Hardware rate  {ios_info["session_rate"]:,.0f} Hz')

        if 'io_buffer_ms' in ios_info:
            add(f'  I/O buffer     {ios_info["io_buffer_ms"]:.1f} ms')

        if 'output_latency_ms' in ios_info:
            add(f'  Out. latency   {ios_info["output_latency_ms"]:.1f} ms')

        if 'port' in ios_info:
            add(f'  Route          {ios_info["port"]} ({ios_info["port_type"]})')

        if ios_info['restarts']:
            add(f'  Engine restarts {ios_info["restarts"]}')
    else:
        add('  Output path    sound.Player fallback')
        add(f'  Polyphony      {TONE_VOICES_PER_NOTE} players per note')
    add(f'  Voices         {ready}/{total} rendered (+ mirror twins)')

    if voices:
        frames = sum(v['frames'] for v in voices.values())
        bytes_per_frame = 8 if ios_info else 4   # float32 vs int16 stereo
        cache_mb = frames * bytes_per_frame * 2 / 1048576.0
        add(f'  Cache size     {cache_mb:.1f} MB (voices + twins)')

    add('')
    add('Level and stereo (digital, dBFS)')

    if voices:
        add(f'  Peak           {peak_all:.1f} (worst voice)')
        add(
            f'  RMS            {min(v["rms"] for v in voices.values()):.1f}'
            f' to {max(v["rms"] for v in voices.values()):.1f}'
        )
        add(f'  L/R corr.      {corr_all:.2f} mean')
    else:
        add('  (rendering - no level data yet)')

    add('')
    add('Mirror twin')
    add(f'  Polarity       inverted, blend {blend:.2f}')
    add(f'  Net level      {twin_db:.1f} dB vs voice alone')

    add('')
    add('Played this session')

    if m.note_level.n:
        add(
            f'  Note level     mean {m.note_level.mean:.1f}, '
            f'min {m.note_level.lo:.1f}, max {m.note_level.hi:.1f} dBFS'
        )
        add(f'  Dyn. range     {m.note_level.hi - m.note_level.lo:.1f} dB')
        add(f'  Limiter        {limited} of {notes} notes')
        add(f'  Mean |pan|     {m.note_pan.mean:.2f}')

        if est_programme is not None:
            add(f'  Est. level     {est_programme:.1f} dBFS RMS')
    else:
        add('  no notes yet')

    if voices:
        add('')
        add('Per instrument')
        add('  name     dur   peak   rms crest  corr notes')

        for inst in INSTRUMENT_ORDER:
            v = voices.get(inst)

            if v:
                add(
                    f'  {inst:<8}{v["dur"]:>4.2f} {v["peak"]:>6.1f}'
                    f'{v["rms"]:>6.1f}{v["crest"]:>6.1f}'
                    f'{v["corr"]:>6.2f} {m.instrument_notes.get(inst, 0):>5}'
                )

    # ---- 3. exposure to control ---------------------------------------------
    head('3. OBSERVED EXPOSURE TO CONTROL')
    dwell_total = sum(m.dwell) or 1.0

    add('Time at each acoustic diameter')

    for i, prof in enumerate(ACOUSTIC_PROFILES):
        add(
            f'  {prof["label"]:<12}{m.dwell[i] / dwell_total * 100:>5.0f}%'
            f'  ({m.dwell[i]:.0f}s)'
        )

    add('')
    add('Control events')

    kinds = sorted(
        (k[8:], v) for k, v in m.counters.items() if k.startswith('control:')
    )

    if kinds:
        for kind, count in kinds:
            add(f'  {kind:<14}{count}')

        per_min = control_events / max(duration / 60.0, 1e-6)
        add(f'  rate           {per_min:.1f} per minute')
    else:
        add('  none yet')

    add('')
    add('Suppressed onsets')
    add(f'  by diameter    {m.counters["suppressed_by_diameter"]}')
    add(f'  silent sector  {m.counters["silent_sector_onsets"]}')

    add('')
    add('Rotor behaviour share')
    bt_total = sum(m.behaviour_time.values()) or 1.0

    for name in BEHAVIOUR_NAMES:
        share = m.behaviour_time.get(name, 0.0) / bt_total * 100.0

        if share >= 0.5:
            add(f'  {name:<9}{share:>5.0f}%')

    # ---- 4. learned ----------------------------------------------------------
    head('4. WHAT THE MODEL HAS LEARNED')
    add(
        f'Lifetime observations: {m.lifetime_ticks} '
        f'({m.loaded_ticks} loaded from earlier sessions).'
    )
    add('')

    state = m.prev_behaviour

    if state and sum(m.markov[state].values()) >= 5:
        probs = sorted(
            m.transition_probs(state).items(), key=lambda kv: -kv[1]
        )
        top, p_top = probs[0]
        add(
            f'Behaviour: the rotor is in {state}. The model expects '
            f'{top} next ({p_top * 100:.0f}% likely, instrument '
            f'{BEHAVIOUR_INSTRUMENT[top]}).'
        )
    else:
        add('Behaviour: not enough transitions yet to forecast the next state.')

    sticky = m.stickiness()

    if sticky is not None:
        add(
            f'Stickiness: the rotor stays in the same behaviour '
            f'{sticky * 100:.0f}% of the time.'
        )

    pairs = sorted(
        (
            (c, a, b) for a, row in m.markov.items()
            for b, c in row.items() if a != b and c > 0
        ),
        reverse=True
    )[:3]

    for c, a, b in pairs:
        add(f'  {a} -> {b}: {c} times')

    add('')

    if skill is not None:
        add(
            f'RMS predictor: mean error {m.err_model.mean:.3f} vs '
            f'{m.err_base.mean:.3f} for a hold-last-value baseline '
            f'(skill {skill * 100:+.1f}%).'
        )
        add(
            f'  weights: hold {m.weights[1]:.2f}, trend '
            f'{m.weights[2]:.2f}, sectors {m.weights[3]:.2f}'
        )
    else:
        add(
            'RMS predictor: still collecting data '
            f'(needs {MODEL_MIN_TICKS} comparisons).'
        )

    add('')
    add('Measured diameter response (note level, dBFS)')

    usable = [
        (i, st) for i, st in enumerate(m.profile_level)
        if st.n >= 5 and ACOUSTIC_PROFILES[i]['enabled']
    ]

    if usable:
        ref_i, ref = max(usable, key=lambda item: item[1].n)
        ref_vol = get_profile_volume(ref_i)

        for i, st in usable:
            line = (
                f'  {ACOUSTIC_PROFILES[i]["label"]:<8}'
                f'mean {st.mean:>6.1f}  n={st.n}'
            )

            if i != ref_i:
                measured = st.mean - ref.mean
                expected = 20.0 * math.log10(
                    max(get_profile_volume(i) / ref_vol, 1e-6)
                )
                line += (
                    f'  vs {ACOUSTIC_PROFILES[ref_i]["label"]}: '
                    f'{measured:+.1f} dB (law {expected:+.1f})'
                )

            add(line)
    else:
        add('  needs at least 5 notes at a diameter')

    # ---- 5. assessment -------------------------------------------------------
    head('5. EXPERT ASSESSMENT')
    notes_out = []

    if peak_all is not None and peak_all > -1.0:
        notes_out.append(
            f'Headroom is thin ({-peak_all:.1f} dB). Many consumer '
            f'speakers and DACs distort within 1 dB of full scale; '
            f'lowering TONE_PEAK would restore margin.'
        )

    if limited_rate > 0.25:
        notes_out.append(
            f'{limited_rate * 100:.0f}% of notes hit the level limit, so '
            f'the RMS multiplier is saturating and flattening dynamics. '
            f'Reduce TONE_MAP_RMS_GAIN or raise headroom.'
        )

    if m.note_level.n > 10 and (m.note_level.hi - m.note_level.lo) < 6.0:
        notes_out.append(
            'Delivered dynamic range is under 6 dB, which a listener '
            'will hear as a flat, insistent tone rather than musical '
            'phrasing.'
        )

    if corr_all is not None and corr_all > 0.98:
        notes_out.append(
            'Left and right are almost identical, so the image is close '
            'to mono. Increase the instrument detune values for width.'
        )

    if ACOUSTIC_PROFILES[ACOUSTIC_PROFILE_INDEX]['stride'] > 1:
        notes_out.append(
            'The selected diameter thins the rhythm to every other '
            'mirror bar, which is intended but halves note density.'
        )

    if skill is not None:
        if skill < 0.02:
            notes_out.append(
                f'The predictor {"does not beat" if skill < 0 else "barely beats"} '
                'a hold-last-value baseline. '
                'The RMS stream is dominated by random blip frequencies, '
                'so expect limited predictability.'
            )
        else:
            notes_out.append(
                f'The predictor beats the baseline by {skill * 100:.1f}%, '
                f'so the RMS stream has learnable structure.'
            )

    if not notes_out:
        notes_out.append(
            'No issues flagged by the current rules. Levels, stereo '
            'image and control response are within normal ranges.'
        )

    for n_text in notes_out:
        add('* ' + n_text)

    # ---- 6. limitations ------------------------------------------------------
    head('6. LIMITATIONS')
    add(
        'Levels are digital estimates relative to full scale, not '
        'acoustic SPL measurements of the phone speaker, and are not '
        'calibrated to LUFS. The model is a small online learner. This '
        'report is assembled by rules from the numbers above; it is '
        'not written by an LLM.'
    )

    return '\n'.join(L)


def get_profile_volume(index):
    prof = ACOUSTIC_PROFILES[index]
    ratio = max(0.0, prof['diameter_mm'] / ACOUSTIC_REFERENCE_MM)
    return ratio ** ACOUSTIC_VOLUME_EXPONENT


def save_report(text):
    path = os.path.join(
        _docs_dir(),
        time.strftime('twins_codec_report_%Y%m%d_%H%M%S.md')
    )

    try:
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)
        return path
    except Exception:
        return None


def show_report(text):
    """Present the report in a scrollable, copyable sheet."""
    try:
        view = ui.View(frame=(0, 0, 540, 720))
        view.name = 'Twins Codec Report'
        view.background_color = '#00040a'

        tv = ui.TextView(frame=view.bounds, flex='WH')
        tv.editable = False
        tv.font = ('Menlo', 11)
        tv.background_color = '#00040a'
        tv.text_color = '#cfeeee'
        tv.text = text
        view.add_subview(tv)

        def share(sender):
            try:
                import dialogs
                dialogs.share_text(text)
            except Exception:
                pass

        view.right_button_items = [
            ui.ButtonItem(title='Share', action=share)
        ]
        view.present('sheet')
    except Exception:
        print(text)


# ===================== PYTHONISTA SCOPE =====================
class YBandGlowfishScope(Scene):
    def setup(self):
        self.background_color = '#00040a'
        motion.start_updates()

        self.scope_center = Point(
            self.size.w / 2,
            self.size.h / 2
        )

        self.scope_radius = min(
            self.size.w,
            self.size.h
        ) * 0.43

        self.podem = ShapeNode(
            ui.Path.oval(0, 0, 40, 40),
            fill_color='#ffff88',
            parent=self
        )

        self.podem.position = self.scope_center

        self.info_label = LabelNode(
            'TWINS CODEC v13 | CÈPTRE MIRROR',
            font=('Courier', 4),
            position=(self.size.w / 2, self.size.h - 42),
            color='#aaffff',
            parent=self
        )

        self.performance_label = LabelNode(
            'L-ROTOR: waiting for mirror target',
            font=('Courier', 5),
            position=(self.size.w / 2, 24),
            color='#88ffcc',
            parent=self
        )

        self._setup_acoustic_slider()
        self._setup_report_button()
        start_tone_prebuild()

        global TWIN1_MAC, TWIN2_MAC, robot_registry
        global SECOND_BLE_CONTROLLER_MAC

        robot_registry.clear()
        TWIN1_MAC = TWIN2_MAC = None
        SECOND_BLE_CONTROLLER_MAC = generate_mac_address(99999)

        if ROBOT_SIMULATOR_ACTIVE:
            for i in range(NUM_ROBOTS):
                mac = generate_mac_address(42000 + i * 13)

                robot_registry[mac] = {
                    'type': 'twin',
                    'bearing': (i * 180) % 360,
                    'last_blip': time.time()
                }

                if i == 0:
                    TWIN1_MAC = mac
                elif i == 1:
                    TWIN2_MAC = mac

    def _setup_acoustic_slider(self):
        """Four-section slider: 0.014mm (off), 4mm, 8mm, 1 inch."""
        w = self.size.w
        n = len(ACOUSTIC_PROFILES)

        self.slider_x0 = max(70.0, w * 0.22)
        self.slider_x1 = w - 125.0
        self.slider_y = 62.0

        self.slider_stops = [
            self.slider_x0
            + i * (self.slider_x1 - self.slider_x0) / (n - 1)
            for i in range(n)
        ]

        self.slider_knob_x = self.slider_stops[ACOUSTIC_PROFILE_INDEX]
        self.slider_target_x = self.slider_knob_x
        self.slider_drag_id = None
        self.slider_label_index = -1

        self.slider_labels = []

        for i, prof in enumerate(ACOUSTIC_PROFILES):
            label = LabelNode(
                prof['label'],
                font=('Courier', 10),
                position=(self.slider_stops[i], self.slider_y + 24),
                color=TONE_MAP_COLOR,
                parent=self
            )
            self.slider_labels.append(label)

        self.acoustic_label = LabelNode(
            '',
            font=('Courier', 9),
            position=(w / 2, self.slider_y + 46),
            color=TONE_MAP_COLOR,
            parent=self
        )

    def _setup_report_button(self):
        """Solid, high-contrast REPORT button just above the slider readout."""
        w = self.size.w
        self.report_w = 120.0
        self.report_h = 36.0
        self.report_cx = w / 2.0
        self.report_cy = self.slider_y + 80.0
        self.report_x = self.report_cx - self.report_w / 2.0
        self.report_y = self.report_cy - self.report_h / 2.0
        self.report_flash = 0.0
        self.report_lit = False

        self.report_shape = ShapeNode(
            ui.Path.rounded_rect(0, 0, self.report_w, self.report_h, 10),
            fill_color='#ffee88',
            stroke_color='#ffffff',
            parent=self
        )
        self.report_shape.position = (self.report_cx, self.report_cy)
        self.report_shape.z_position = 50

        self.report_label = LabelNode(
            'REPORT',
            font=('Courier-Bold', 16),
            position=(self.report_cx, self.report_cy),
            color='#00040a',
            parent=self
        )
        self.report_label.z_position = 51

    def _report_hit(self, loc):
        return (
            self.report_x - 10 <= loc.x <= self.report_x + self.report_w + 10
            and self.report_y - 10 <= loc.y <= self.report_y + self.report_h + 10
        )

    def _on_report(self):
        self.report_flash = time.time()
        CODEC_MODEL.record_control('report')

        text = generate_codec_report()
        path = save_report(text)
        CODEC_MODEL.save()

        if path:
            text += f'\n\nSaved: {path}'

        ui.delay(lambda: show_report(text), 0.0)

    def _draw_report_button(self):
        """Flash the button white briefly after it is pressed."""
        lit = (time.time() - self.report_flash) < 0.3

        if lit != self.report_lit:
            self.report_lit = lit
            self.report_shape.fill_color = '#ffffff' if lit else '#ffee88'

    def _slider_hit(self, loc):
        return (
            self.slider_x0 - 26 <= loc.x <= self.slider_x1 + 26
            and abs(loc.y - self.slider_y) <= 34
        )

    def _slider_set_from_x(self, x):
        x = max(self.slider_x0, min(self.slider_x1, x))
        self.slider_target_x = x

        index = min(
            range(len(self.slider_stops)),
            key=lambda i: abs(self.slider_stops[i] - x)
        )

        if index != ACOUSTIC_PROFILE_INDEX:
            set_acoustic_profile(index)

    def _draw_acoustic_slider(self):
        n = len(ACOUSTIC_PROFILES)
        index = ACOUSTIC_PROFILE_INDEX
        acoustic = get_acoustic_scale()

        # The knob follows the finger while dragging, then snaps to a stop.
        target = (
            self.slider_target_x
            if self.slider_drag_id is not None
            else self.slider_stops[index]
        )

        self.slider_knob_x += (target - self.slider_knob_x) * 0.35

        y = self.slider_y
        colour = TONE_MAP_COLOR if acoustic['enabled'] else '#ff6666'

        stroke(TONE_MAP_COLOR, 0.30)
        stroke_weight(4.0)
        line(self.slider_x0, y, self.slider_x1, y)

        stroke(colour, 0.95)
        stroke_weight(4.0)
        line(self.slider_x0, y, self.slider_knob_x, y)

        stroke_weight(2.0)

        for i in range(n):
            stroke(colour if i == index else TONE_MAP_COLOR,
                   1.0 if i == index else 0.55)
            line(self.slider_stops[i], y - 9, self.slider_stops[i], y + 9)

        no_stroke()
        fill('#ffffff' if acoustic['enabled'] else '#ff6666')
        ellipse(self.slider_knob_x - 10, y - 10, 20, 20)

        if index != self.slider_label_index:
            self.slider_label_index = index

            for i, label in enumerate(self.slider_labels):
                label.color = '#ffffff' if i == index else TONE_MAP_COLOR

        if acoustic['enabled']:
            self.acoustic_label.text = (
                f'DIA {acoustic["label"]}  '
                f'VOL {acoustic["volume"]:.2f}  '
                f'WIDTH {acoustic["width"]:.2f}  '
                f'BEATS 1/{acoustic["stride"]}'
            )
        else:
            self.acoustic_label.text = 'DIA 0.014mm  TONE MAP OFF'

    def simulate_robot_blips(self):
        global DOLPHIN_TONE_ACTIVE, ULTRA_DOLPHIN_ACTIVE

        now = time.time()

        for mac, data in list(robot_registry.items()):
            interval = 2.0 + random.uniform(-0.4, 0.9)

            if now - data.get('last_blip', 0) > interval:
                data['last_blip'] = now

                angle = (
                    data.get('bearing', 0)
                    + random.uniform(-12, 12)
                ) % 360

                data['bearing'] = angle

                pos = Point(
                    self.scope_center.x
                    + self.scope_radius * 0.64
                    * math.cos(math.radians(angle)),
                    self.scope_center.y
                    + self.scope_radius * 0.64
                    * math.sin(math.radians(angle))
                )

                freq = random.uniform(450, 38000)

                if freq >= ULTRA_DOLPHIN_FREQ_MIN:
                    scope = 'ultra_dolphin'
                    ULTRA_DOLPHIN_ACTIVE = True
                elif freq >= DOLPHIN_FREQ_MIN:
                    scope = 'dolphin'
                    DOLPHIN_TONE_ACTIVE = True
                else:
                    scope = 'optical' if OPTICS_PREFERRED else 'ble'

                self.trigger_predictable_feedback(
                    mac,
                    angle,
                    pos,
                    freq,
                    scope_type=scope,
                    is_new_blip=True
                )

    def trigger_predictable_feedback(
        self,
        from_mac,
        bearing,
        pos,
        freq,
        scope_type='yband',
        is_new_blip=False,
        diameter_miles=1200
    ):
        global twin_feedback_counter
        global DOLPHIN_TONE_ACTIVE, ULTRA_DOLPHIN_ACTIVE

        twin_feedback_counter += 1

        if freq >= ULTRA_DOLPHIN_FREQ_MIN:
            scope_type = 'ultra_dolphin'
            ULTRA_DOLPHIN_ACTIVE = True
        elif freq >= DOLPHIN_FREQ_MIN:
            scope_type = 'dolphin'
            DOLPHIN_TONE_ACTIVE = True

        # Process the selected soundform before drawing its visual effects.
        trigger_music_filesystem_response(
            from_mac,
            bearing,
            pos,
            get_sector(bearing),
            freq,
            scope_type=scope_type,
            is_new_blip=is_new_blip,
            diameter_miles=diameter_miles
        )

        induction = active_music_inductions.get(from_mac, {})

        color = induction.get(
            'ceptre_color',
            FEEDBACK_COLOR_TWIN1
            if from_mac == TWIN1_MAC
            else FEEDBACK_COLOR_TWIN2
        )

        vibration = induction.get(
            'ceptre_vibration',
            0.0
        )

        if len(sunbeam_pool) < 38:
            sunbeam_pool.append(
                SunbeamEffect(
                    pos,
                    bearing,
                    freq,
                    color=color,
                    scope_type=scope_type,
                    vibration=vibration
                )
            )

    def update(self):
        global write_tone_map_phase, AUTO_TUNE_ACTIVE
        global DOLPHIN_TONE_ACTIVE, ULTRA_DOLPHIN_ACTIVE
        global EXTERNAL_INTERFERENCE_DETECTED, MIC_SWITCHED_TO_BLIPS
        global PWR_DOWN_ACTIVE, SIGNAL_WHITE

        write_tone_map_phase += (
            0.028 * spinning_plate_speed
        )

        advance_lband_rotor()
        update_tone_map()

        if AUTO_TUNE_ACTIVE:
            active_music_inductions.clear()
            AUTO_TUNE_ACTIVE = False
            DOLPHIN_TONE_ACTIVE = False
            ULTRA_DOLPHIN_ACTIVE = False
            EXTERNAL_INTERFERENCE_DETECTED = False
            MIC_SWITCHED_TO_BLIPS = False
            PWR_DOWN_ACTIVE = False
            SIGNAL_WHITE = False

        continuous_assessment()
        run_increasing_test_blips(self)

        if ROBOT_SIMULATOR_ACTIVE:
            self.simulate_robot_blips()

        mag = motion.get_magnetic_field()

        if mag and len(mag) >= 3:
            mag_history.append(
                abs(mag[0]) + abs(mag[1]) + abs(mag[2])
            )

            acoustic_history.append(
                len(sunbeam_pool)
                + len(active_music_inductions) * 1.3
            )

        now = time.time()

        for mac in list(active_music_inductions.keys()):
            induction = active_music_inductions[mac]

            induction['fallout'] = max(
                0.0,
                1.0
                - (now - induction['start_time'])
                * FALLOUT_DECAY_RATE
                * 2.6
            )

            if induction['fallout'] < 0.07:
                del active_music_inductions[mac]

        sunbeam_pool[:] = [
            effect
            for effect in sunbeam_pool
            if effect.update() and effect.draw()
        ]

        if hasattr(self, 'podem'):
            self.podem.rotation = (
                self.t * 42 + write_tone_map_phase * 9
            )

        if hasattr(self, 'info_label'):
            status = (
                "PWR DOWN + 93nm"
                if PWR_DOWN_ACTIVE
                else "93nm + SINE WAVES"
            )

            if CEPTRE_MIRROR_ACTIVE:
                status += " | CÈPTRE"

            if LLM_WAVE_ACTIVE:
                status += " | LLM WAVE"

            if LBAND_ROTOR_ACTIVE:
                status += " | LBAND ROTOR"

            self.info_label.text = (
                f'TWINS v13 | {status} '
                f'| FX:{len(sunbeam_pool)} '
                f'| CÈPTRE:{CEPTRE_PROCESSED_COUNT} '
                f'| TONE S{TONE_MAP_STATE["sector"]}:'
                f'{TONE_MAP_STATE["freq"]:.0f}Hz '
                f'{TONE_MAP_STATE["backend"]}{" ERR" if TONE_MAP_STATE["error"] else ""} '
                f'{BEHAVIOUR_STATE["behaviour"]}>{TONE_MAP_STATE["instrument"]} '
                f'{"" if TONE_MAP_STATE["ready"] >= TONE_MAP_STATE["total"] else "[%d/%d] " % (TONE_MAP_STATE["ready"], TONE_MAP_STATE["total"])}'
                f'x{TONE_MAP_STATE["multiplier"]:.1f} '
                f'{TONE_MAP_STATE["volume"]:+.2f}/'
                f'{TONE_MAP_STATE["mirror_volume"]:+.2f}'
                f'{"" if TONE_MAP_ENABLED else " OFF"} '
                f'| {BBC_TIME}'
            )

    def _draw_spectrum(
        self,
        cx,
        cy,
        levels,
        color,
        alpha=1.0,
        negative=False,
        bar_width=3.0,
        gap=2.0
    ):
        """
        Draw signed spectrum bars centred on cx.

        Positive levels rise from the baseline (cy + 13). Negative (mirror)
        levels hang directly beneath it, separated by LBAND_MIRROR_GAP, and
        ripple with the LBand rotor phase so they cycle with it. A thin white
        marker shows +RMS above the baseline or -RMS beneath it.
        """
        span = len(levels) * (bar_width + gap)
        x0 = cx - span / 2.0
        y0 = cy + 13.0

        fill(color, alpha)

        for i, level in enumerate(levels):
            magnitude = abs(level)

            if negative:
                ripple = 0.78 + 0.22 * math.sin(
                    MIRROR_RIPPLE_RATE * LBAND_ROTOR_PHASE_TOTAL
                    + i * MIRROR_RIPPLE_SPREAD
                )
                h = 4.0 + magnitude * ripple * 22.0
                y = y0 - LBAND_MIRROR_GAP - h
            else:
                h = 4.0 + magnitude * 22.0
                y = y0

            rect(
                x0 + i * (bar_width + gap),
                y,
                bar_width,
                h
            )

        # RMS marker: +RMS above the baseline, -RMS beneath the mirror bars.
        rms_h = 4.0 + min(
            1.0, abs(LBAND_RMS_STATE['out']) / 1000.0
        ) * 22.0

        fill('#ffffff', alpha * 0.9)

        marker_y = (
            y0 - LBAND_MIRROR_GAP - rms_h
            if negative
            else y0 + rms_h
        )

        rect(x0 - 2.0, marker_y, span + 4.0, 1.0)

    def _draw_l_rotor_transfer(self):
        """
        Draw an animated L-shaped route to the nearest processed mirror target.

        The route, RMS-scaled spectra and transfer score are a local visual
        model. They do not represent physical energy transfer or
        communication with a device.
        """
        candidates = []

        for mac, induction in active_music_inductions.items():
            pos = induction.get('pos')

            if pos is None or not induction.get('ceptre_processed'):
                continue

            distance = math.hypot(
                pos.x - self.scope_center.x,
                pos.y - self.scope_center.y
            )

            candidates.append(
                (distance, mac, induction, pos)
            )

        if not candidates:
            MIRROR_RHYTHM_STATE['bar_levels'] = []
            CEPTRE_TRANSFER_STATE.update({
                'target': None,
                'energy': 0.0,
                'performance': 0.0,
                'distance': 0.0,
                'timestamp': time.time()
            })

            if hasattr(self, 'performance_label'):
                self.performance_label.text = (
                    'L-ROTOR: waiting for mirror target'
                )

            return

        # Select the nearest eligible mirror soundform.
        distance, mac, induction, target = min(
            candidates,
            key=lambda item: item[0]
        )

        origin = self.scope_center

        # The L has a horizontal leg followed by a vertical leg.
        elbow_x = target.x
        elbow_y = origin.y

        phase = LBAND_ROTOR_PHASE
        pulse = 0.5 + 0.5 * math.sin(phase * 2.0)

        energy_ratio = (
            abs(induction.get('ceptre_output', 0.0))
            / max(
                abs(induction.get('ceptre_original', 0.0)),
                1e-9
            )
        )

        energy_ratio = max(
            0.0,
            min(1.0, energy_ratio)
        )

        proximity = max(
            0.0,
            1.0 - distance / max(self.scope_radius, 1.0)
        )

        vibration = abs(
            induction.get('ceptre_vibration', 0.0)
        )

        stability = 1.0 / (
            1.0 + vibration * 0.02
        )

        performance = 100.0 * (
            0.55 * energy_ratio
            + 0.25 * proximity
            + 0.20 * stability
        )

        transferred = energy_ratio * (
            0.65 + 0.35 * pulse
        )

        # Draw the two legs of the L-shaped rotor.
        rotor_color = induction.get(
            'ceptre_color',
            CEPTRE_COLOR_MIRRORED
        )

        stroke(
            rotor_color,
            0.35 + pulse * 0.55
        )

        stroke_weight(
            2.0 + pulse * 2.0
        )

        line(
            origin.x,
            origin.y,
            elbow_x,
            elbow_y
        )

        line(
            elbow_x,
            elbow_y,
            target.x,
            target.y
        )

        # Animate a point travelling along both legs.
        total_length = max(
            1.0,
            abs(target.x - origin.x)
            + abs(target.y - origin.y)
        )

        travel = (
            phase / (2.0 * math.pi)
        ) * total_length

        horizontal_length = abs(
            target.x - origin.x
        )

        if travel <= horizontal_length:
            direction = (
                1.0
                if target.x >= origin.x
                else -1.0
            )

            tip_x = origin.x + direction * travel
            tip_y = origin.y

        else:
            remaining = travel - horizontal_length

            direction = (
                1.0
                if target.y >= origin.y
                else -1.0
            )

            tip_x = target.x

            tip_y = origin.y + direction * min(
                remaining,
                abs(target.y - origin.y)
            )

        no_stroke()
        fill('#ffffff')

        ellipse(
            tip_x - 3.5,
            tip_y - 3.5,
            7.0,
            7.0
        )

        # ---- LBand RMS + mirrored spectra ----------------------------
        # Bar heights come from the primary and secondary Cèptre outputs,
        # then are scaled by the rolling LBand RMS level.
        rms = compute_lband_rms()
        rms_scale = min(1.0, rms['out'] / 1000.0)

        primary_level = min(
            1.0,
            abs(induction.get('ceptre_output', 0.0)) / 1000.0
        )

        response_level = min(
            1.0,
            abs(induction.get('ceptre_response', 0.0)) / 1000.0
        )

        base_levels = [
            primary_level * 0.35,
            primary_level * 0.62,
            primary_level,
            response_level * 0.8,
            response_level,
            response_level * 0.55,
            primary_level * 0.42
        ]

        bar_levels = [
            min(1.0, level * (0.5 + rms_scale))
            for level in base_levels
        ]

        # The mirror RMS is the negative of the positive RMS, so the mirror
        # spectrum carries negative values and hangs beneath the original.
        mirror_levels = [-level for level in bar_levels]
        MIRROR_RHYTHM_STATE['bar_levels'] = [abs(v) for v in mirror_levels]

        c = self.scope_center
        ghost_x = 2.0 * c.x - target.x
        ghost_y = 2.0 * c.y - target.y

        no_stroke()

        # Opposite colour for the mirror spectrum (same polarity inversion
        # already applied to the levels / soundform).
        if rotor_color == CEPTRE_COLOR_MIRRORED:
            mirror_color = CEPTRE_COLOR_ORIGINAL
        elif rotor_color == CEPTRE_COLOR_ORIGINAL:
            mirror_color = CEPTRE_COLOR_MIRRORED
        else:
            mirror_color = CEPTRE_COLOR_MIRRORED

        # Original (positive) spectrum and its negative mirror beneath.
        self._draw_spectrum(
            target.x, target.y, bar_levels, rotor_color, 1.0
        )
        self._draw_spectrum(
            target.x, target.y, mirror_levels, mirror_color, 0.75,
            negative=True
        )

        # Point-reflected ghost across the scope center, same signed layout
        # and opposite colour on the mirror.
        self._draw_spectrum(
            ghost_x, ghost_y, bar_levels, rotor_color, 0.45
        )
        self._draw_spectrum(
            ghost_x, ghost_y, mirror_levels, mirror_color, 0.35,
            negative=True
        )

        # Mark the selected target and its reflected ghost.
        no_fill()
        stroke('#ffffff', 0.8)
        stroke_weight(1.0)

        ellipse(
            target.x - 9,
            target.y - 9,
            18,
            18
        )

        stroke('#ffffff', 0.35)

        ellipse(
            ghost_x - 9,
            ghost_y - 9,
            18,
            18
        )

        # Store the latest simulated transfer and performance values.
        CEPTRE_TRANSFER_STATE.update({
            'target': mac,
            'rms': rms['out'],
            'mirror_rms': rms['out_mirror'],
            'energy': transferred,
            'performance': performance,
            'distance': distance,
            'timestamp': time.time()
        })

        if hasattr(self, 'performance_label'):
            self.performance_label.text = (
                f'L-ROTOR → {mac[:8]} '
                f'| RMS:{rms["out"]:+.0f}/{rms["out_mirror"]:+.0f} '
                f'| TRANSFER:{transferred:.2f} '
                f'| PERF:{performance:.0f}%'
            )

    def _draw_tone_map(self):
        """
        Ring of eight sector arcs around the scope. Arc brightness and weight
        follow each sector's RMS; the sector under the LBand rotor is
        highlighted, matching the tone that sounds as the rotor enters it.
        """
        if not TONE_MAP_ENABLED:
            return

        levels = TONE_MAP_STATE['levels']
        active = TONE_MAP_STATE['sector']
        radius = self.scope_radius * 1.06
        span = 360.0 / SECTOR_COUNT

        for s in range(SECTOR_COUNT):
            norm = tone_level_norm(levels[s])
            is_active = (s == active)

            if is_active:
                stroke(TONE_MAP_COLOR_ACTIVE, 1.0)
                stroke_weight(5.0)
            else:
                stroke(TONE_MAP_COLOR, 0.2 + 0.6 * norm)
                stroke_weight(2.0 + 3.0 * norm)

            previous = None

            for j in range(7):
                angle = math.radians(
                    s * span + 2.0 + (span - 4.0) * j / 6.0
                )

                x = self.scope_center.x + math.cos(angle) * radius
                y = self.scope_center.y + math.sin(angle) * radius

                if previous is not None:
                    line(previous[0], previous[1], x, y)

                previous = (x, y)

        # Mirror ring: negative per-sector RMS, drawn just inside the
        # positive ring in the mirror colour.
        inner = self.scope_radius * 0.99

        for s in range(SECTOR_COUNT):
            m_norm = tone_level_norm(TONE_MAP_STATE['mirror_levels'][s])
            is_active = (s == active)

            stroke(
                CEPTRE_COLOR_MIRRORED,
                1.0 if is_active else 0.2 + 0.6 * m_norm
            )
            stroke_weight(4.0 if is_active else 1.5 + 2.5 * m_norm)

            previous = None

            for j in range(7):
                angle = math.radians(
                    s * span + 2.0 + (span - 4.0) * j / 6.0
                )

                x = self.scope_center.x + math.cos(angle) * inner
                y = self.scope_center.y + math.sin(angle) * inner

                if previous is not None:
                    line(previous[0], previous[1], x, y)

                previous = (x, y)

    def draw(self):
        for mac, induction in list(
            active_music_inductions.items()
        ):
            if induction.get('fallout', 0) < 0.1:
                continue

            alpha = induction['fallout'] * 0.9

            if (
                CEPTRE_MIRROR_ACTIVE
                and induction.get('ceptre_processed')
            ):
                color = induction.get(
                    'ceptre_color',
                    CEPTRE_COLOR_ORIGINAL
                )

            elif SIGNAL_WHITE:
                color = WHITE_SIGNAL_COLOR

            elif induction.get('nm93_modulation'):
                color = NM93_COLOR

            elif induction.get('windsock') or WINDSOCK_ACTIVE:
                color = (
                    DOPPLER_COLOR
                    if induction.get('doppler_active')
                    else WINDSOCK_COLOR
                )

            elif induction.get('measurement'):
                color = MEASUREMENT_COLOR

            elif EXTERNAL_INTERFERENCE_DETECTED:
                color = NOKIA_FUCK_YOU_COLOR

            elif induction.get('pure_optics'):
                color = OPTICAL_WHIRLPOOL_COLOR

            else:
                color = (
                    '#aaffcc'
                    if induction.get('surfing')
                    else '#88ffaa'
                )

            stroke(color, alpha)
            stroke_weight(3.2)

            radius = self.scope_radius * 0.52

            start = math.radians(
                induction['bearing'] - 28
            )

            end = math.radians(
                induction['bearing'] + 28
            )

            previous = None

            for j in range(9):
                angle = start + (
                    j / 8.0
                ) * (end - start)

                x = (
                    self.scope_center.x
                    + math.cos(angle) * radius
                )

                y = (
                    self.scope_center.y
                    + math.sin(angle) * radius
                )

                if previous is not None:
                    line(
                        previous[0],
                        previous[1],
                        x,
                        y
                    )

                previous = (x, y)

        self._draw_tone_map()
        self._draw_l_rotor_transfer()
        self._draw_acoustic_slider()
        self._draw_report_button()

    def touch_moved(self, touch):
        if touch.touch_id == self.slider_drag_id:
            self._slider_set_from_x(touch.location.x)

    def touch_ended(self, touch):
        if touch.touch_id == self.slider_drag_id:
            self.slider_drag_id = None

    def touch_began(self, touch):
        global AUTO_TUNE_ACTIVE
        global PWR_DOWN_ACTIVE, WINDSOCK_ACTIVE
        global TONE_MAP_ENABLED

        # The Report button and the acoustic slider take priority over the
        # corner toggles.
        if self._report_hit(touch.location):
            self._on_report()
            return

        if self._slider_hit(touch.location):
            self.slider_drag_id = touch.touch_id
            self._slider_set_from_x(touch.location.x)
            return

        if (
            touch.location.x < 90
            and touch.location.y > self.size.h - 90
        ):
            AUTO_TUNE_ACTIVE = True
            CODEC_MODEL.record_control('auto_tune')
            return

        if (
            touch.location.x > self.size.w - 120
            and touch.location.y < 120
        ):
            PWR_DOWN_ACTIVE = not PWR_DOWN_ACTIVE
            CODEC_MODEL.record_control('power_down')
            return

        if (
            touch.location.x > self.size.w - 120
            and touch.location.y > self.size.h - 120
        ):
            WINDSOCK_ACTIVE = not WINDSOCK_ACTIVE
            CODEC_MODEL.record_control('windsock')
            return

        if (
            touch.location.x < 90
            and touch.location.y < 90
        ):
            TONE_MAP_ENABLED = not TONE_MAP_ENABLED
            CODEC_MODEL.record_control('tone_toggle')
            return

        loc = touch.location

        dx = loc.x - self.scope_center.x
        dy = loc.y - self.scope_center.y

        if math.hypot(dx, dy) > self.scope_radius * 1.15:
            return

        bearing = (
            math.degrees(math.atan2(dy, dx)) + 360
        ) % 360

        mac = (
            TWIN1_MAC
            if random.random() < 0.5
            else TWIN2_MAC
        )

        if mac is None:
            return

        freq = 580 + (
            math.hypot(dx, dy) / self.scope_radius
        ) * 620

        pos = Point(
            loc.x,
            loc.y
        )

        scope = (
            'windsock'
            if WINDSOCK_ACTIVE
            else (
                'optical'
                if OPTICS_PREFERRED
                else random.choice(['yband', 'ble', 'uwb'])
            )
        )

        scope = characteristics_surfing(
            mac,
            scope
        )

        self.trigger_predictable_feedback(
            mac,
            bearing,
            pos,
            freq,
            scope_type=scope,
            is_new_blip=True,
            diameter_miles=1200
        )
        CODEC_MODEL.record_control('tap_blip')


if __name__ == '__main__':
    last_induction_time = time.time()

    last_chatter_check = (
        time.time()
        if 'last_chatter_check' not in globals()
        else last_chatter_check
    )

    run(
        YBandGlowfishScope(),
        PORTRAIT,
        show_fps=False
    )