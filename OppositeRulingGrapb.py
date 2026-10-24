#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
THE TWINS CODEC v14
Cèptre Mirror / LLMWave Opposition / L-band Rotor
Pythonista • Local visual/audio-signal simulation

Processing architecture:
    1. Selected soundform
    2. Original L-band rotor path
    3. Cèptre mirror path
    4. Independently amplified LLMWave inverse
    5. Attenuation and simulated vibration
    6. Dual-spectrum display
    7. Secondary response processing
    8. Rotor performance comparison

Local simulation only:
- No RF, BLE, ultrasound or optical transmission.
- Vibration is visual modulation, not physical haptics.
- LLMWave is a mathematical signal-processing stage.
- Spectrum bars are illustrative, not FFT measurements.
- Performance and transfer values are simulated.
"""

import ui
from scene import *
import motion
import time
import random
import math
from collections import defaultdict, deque


print(
    "THE TWINS CODEC v14 - "
    "CEPTRE MIRROR / LLMWAVE OPPOSITION / LBAND ROTOR"
)


# ============================================================
# FEATURE FLAGS
# ============================================================

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


# ============================================================
# CEPTRE / LLMWAVE / LBAND ROTOR
# ============================================================

CEPTRE_MIRROR_ACTIVE = True
LLM_WAVE_ACTIVE = True
LBAND_ROTOR_ACTIVE = True

# Rotor movement.
LBAND_ROTOR_SPEED = 0.45
LBAND_ROTOR_DEPTH = 0.18
LBAND_ROTOR_PHASE = 0.0

# Opposition is now calculated independently.
LLM_WAVE_OPPOSITION_ACTIVE = True

# Amplification of the inverted path.
LLM_WAVE_AMPLIFICATION = 1.80

# Retain the original reference path.
LLM_WAVE_KEEP_ORIGINAL = True
LLM_WAVE_COMPARE_PATHS = True

# Retained for compatibility with v13.
# The original/mirror blend is no longer used to calculate
# the amplified LLMWave output.
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

CEPTRE_PROCESSED_COUNT = 0
CEPTRE_HISTORY = deque(maxlen=120)
CEPTRE_LAST_OUTPUT = {}

LLM_WAVE_HISTORY = deque(maxlen=120)
LLM_WAVE_LAST_OUTPUT = {}

CEPTRE_TRANSFER_STATE = {
    'target': None,
    'energy': 0.0,
    'performance': 0.0,
    'distance': 0.0,
    'timestamp': 0.0
}


# ============================================================
# GLOBALS
# ============================================================

twin_pulse_alternator = 0.251 + 469e4
write_tone_map_phase = 0.0

# Preserve the existing expression and its resulting value.
spinning_plate_speed = (
    0.05 / -0.05 / 0.4 / -0.04
    / 0.3 / -0.03 / 20.35845 / -0.01
)

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


# ============================================================
# SUBVOCAL REGISTRY
# ============================================================

def register_subvocal_with_signature(
    mac,
    vocal_type="subvocal"
):
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


# ============================================================
# SIGNAL GENERATION
# ============================================================

def generate_optical_sine_wave_93nm(
    freq,
    sector,
    amplitude=1.0
):
    phase = write_tone_map_phase * 4.2 + sector * 0.7

    sine = math.sin(phase) * amplitude

    envelope = (
        0.6 + 0.4
        * math.sin(write_tone_map_phase * 9.3)
    )

    return sine * envelope


def generate_electrical_sine_wave(
    freq,
    sector,
    diameter_miles=1200
):
    ring = math.sin(freq * 0.00085) * 0.52

    decay = max(
        0.28,
        1.0 - sector * 0.052
    )

    diameter_factor = max(
        0.65,
        min(1.7, diameter_miles / 850.0)
    )

    wave = (
        freq
        * (0.94 + ring * 0.06)
        * decay
        * diameter_factor
    )

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
        freq * 0.0012
        + write_tone_map_phase * 1.8
    ) * 0.6

    air_volume = strength * (
        0.7 + 0.3 * math.sin(belt_timing * 4.2)
    )

    relative_velocity = (
        math.cos(
            math.radians(bearing - wind_direction)
        ) * 0.8
    )

    doppler_shift = 1.0 + relative_velocity * 0.18

    shifted_freq = freq * doppler_shift

    soundform = (
        shifted_freq
        * (1.0 + disturbance * 0.4)
        * air_volume
    )

    return soundform, doppler_shift, air_volume


def generate_optical_planar_whirlpool(
    freq,
    sector,
    maturity
):
    whirl = math.sin(
        write_tone_map_phase * 2.35 + sector
    ) * 0.37

    coil = math.cos(
        freq * 0.00032 + maturity * 6.28
    ) * 0.27

    planar = 1.0 + (whirl + coil) * 0.16

    if EXTERNAL_INTERFERENCE_DETECTED or PWR_DOWN_ACTIVE:
        planar *= 0.65

    return max(
        DOLPHIN_FREQ_MIN,
        freq * planar
    )


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
        optical * 0.65 + electrical * 0.35,
        electrical * 0.18
    )


# ============================================================
# L-BAND ROTOR
# ============================================================

def advance_lband_rotor():
    global LBAND_ROTOR_PHASE

    if LBAND_ROTOR_ACTIVE:
        LBAND_ROTOR_PHASE = (
            LBAND_ROTOR_PHASE
            + LBAND_ROTOR_SPEED * 0.028
        ) % (2.0 * math.pi)

    return LBAND_ROTOR_PHASE


# ============================================================
# CEPTRE MIRROR / LLMWAVE OPPOSITION PROCESSOR
# ============================================================

def process_ceptre_wave(
    soundform,
    freq,
    sector,
    scope_type='yband',
    source_mac=None
):
    """
    Process a scalar soundform through independent paths.

    ORIGINAL:
        Original scalar multiplied by rotor gain.

    MIRROR:
        Negative of the original scalar.

    LLMWAVE:
        Inverted scalar multiplied by amplification and rotor gain.

    OUTPUT:
        LLMWave result after attenuation.

    The input is a scalar simulation value, not an audio buffer.
    """
    global CEPTRE_PROCESSED_COUNT
    global CEPTRE_LAST_OUTPUT
    global LLM_WAVE_LAST_OUTPUT

    original = float(soundform)

    phase = LBAND_ROTOR_PHASE

    # --------------------------------------------------------
    # 1. ROTOR MODULATION
    # --------------------------------------------------------

    if LLM_WAVE_ACTIVE and LBAND_ROTOR_ACTIVE:
        rotor = math.sin(
            phase + sector * 0.35
        )

        rotor_gain = (
            1.0 + LBAND_ROTOR_DEPTH * rotor
        )

    else:
        rotor = 0.0
        rotor_gain = 1.0

    # --------------------------------------------------------
    # 2. ORIGINAL REFERENCE PATH
    # --------------------------------------------------------

    if LLM_WAVE_KEEP_ORIGINAL:
        original_output = original * rotor_gain
    else:
        original_output = original

    # --------------------------------------------------------
    # 3. CEPTRE MIRROR
    # --------------------------------------------------------

    if (
        CEPTRE_MIRROR_ACTIVE
        and LLM_WAVE_OPPOSITION_ACTIVE
    ):
        mirrored = -original
    else:
        mirrored = original

    # --------------------------------------------------------
    # 4. INDEPENDENT LLMWAVE AMPLIFICATION
    # --------------------------------------------------------

    if (
        LLM_WAVE_ACTIVE
        and LLM_WAVE_OPPOSITION_ACTIVE
    ):
        amplified_mirror = (
            mirrored * LLM_WAVE_AMPLIFICATION
        )
    else:
        amplified_mirror = mirrored

    # Rotor modulation is applied independently to this path.
    llm_wave = amplified_mirror * rotor_gain

    # --------------------------------------------------------
    # 5. ATTENUATION
    # --------------------------------------------------------

    attenuation = max(
        CEPTRE_MIN_ATTENUATION,
        min(
            CEPTRE_MAX_ATTENUATION,
            CEPTRE_BASE_ATTENUATION
        )
    )

    output = llm_wave * attenuation

    # --------------------------------------------------------
    # 6. COMPARISON METRICS
    # --------------------------------------------------------

    reference_magnitude = abs(original_output)
    output_magnitude = abs(output)

    opposition_error = (
        abs(original_output + output)
        / max(reference_magnitude, 1e-9)
    )

    amplification_ratio = (
        output_magnitude
        / max(reference_magnitude, 1e-9)
    )

    # Prevent unhelpful numerical display values.
    opposition_error = min(
        opposition_error,
        1000.0
    )

    # --------------------------------------------------------
    # 7. SIMULATED VIBRATION MODULATION
    # --------------------------------------------------------

    vibration = 0.0

    if CEPTRE_VIBRATION_ENABLED:
        vibration = (
            output
            * CEPTRE_VIBRATION_GAIN
            * math.sin(
                phase * CEPTRE_VIBRATION_RATE
                + sector * 0.5
            )
        )

    # --------------------------------------------------------
    # 8. COLOUR STATE
    # --------------------------------------------------------

    if not CEPTRE_MIRROR_ACTIVE:
        color = CEPTRE_COLOR_ORIGINAL

    elif rotor >= 0.25:
        color = CEPTRE_COLOR_MIRRORED

    elif rotor <= -0.25:
        color = CEPTRE_COLOR_MIXED

    else:
        color = CEPTRE_COLOR_MIRRORED

    # --------------------------------------------------------
    # 9. RESULT
    # --------------------------------------------------------

    result = {
        'original': original,
        'original_output': original_output,

        'mirrored': mirrored,
        'amplified_mirror': amplified_mirror,

        'llm_wave': llm_wave,

        'attenuation': attenuation,
        'output': output,

        'vibration': vibration,
        'color': color,

        'rotor': rotor,
        'rotor_gain': rotor_gain,
        'rotor_phase': phase,

        'frequency': float(freq),
        'sector': int(sector) % SECTOR_COUNT,

        'scope_type': scope_type,
        'source': source_mac,

        'opposition_error': opposition_error,
        'amplification_ratio': amplification_ratio,

        'timestamp': time.time()
    }

    CEPTRE_PROCESSED_COUNT += 1

    CEPTRE_HISTORY.append(result)

    LLM_WAVE_HISTORY.append({
        'original': original_output,
        'opposing': output,
        'amplification_ratio': amplification_ratio,
        'opposition_error': opposition_error,
        'timestamp': result['timestamp']
    })

    CEPTRE_LAST_OUTPUT = result
    LLM_WAVE_LAST_OUTPUT = result

    return result


# ============================================================
# ASSESSMENT / UTILITIES
# ============================================================

def continuous_assessment():
    global twin_pulse_alternator
    global MEMORY_DEBT
    global SIGNAL_WHITE
    global last_measurement_time

    twin_pulse_alternator = (
        twin_pulse_alternator + 1
    ) % 2

    if PWR_DOWN_ACTIVE:
        MEMORY_DEBT = min(
            MAX_MEMORY_DEBT,
            MEMORY_DEBT + 2.5
        )

        SIGNAL_WHITE = random.random() < 0.12

        if SIGNAL_WHITE:
            update_bbc_time_via_induction(
                white_signal=True
            )

    if MEMORY_DEBT > MAX_MEMORY_DEBT:
        MEMORY_DEBT *= 0.75

    if (
        MEASUREMENT_MODE
        and BBC_TIME in ["09:25", "09:30"]
        and BBC_TIME != last_measurement_time
    ):
        last_measurement_time = BBC_TIME

        if CONSOLE_PRINTING:
            print(
                f"RESPONSIVE MEASUREMENT @ {BBC_TIME}"
            )

    auto_channel_attenuation()
    detect_external_interference()


def consume_memory_budget(amount=1.0):
    global MEMORY_DEBT

    MEMORY_DEBT = min(
        MAX_MEMORY_DEBT,
        MEMORY_DEBT + amount
    )


def get_sector(bearing):
    return int(
        ((bearing % 360) / 360.0)
        * SECTOR_COUNT
    )


def generate_mac_address(seed=None):
    rng = (
        random.Random(seed)
        if seed is not None
        else random
    )

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

    factor = (
        0.70
        if PWR_DOWN_ACTIVE
        else (
            0.80
            if high or EXTERNAL_INTERFERENCE_DETECTED
            else 1.03
        )
    )

    for key in io_attenuation:
        io_attenuation[key] = max(
            0.20,
            io_attenuation[key] * factor
        )

    return io_attenuation


def detect_external_interference():
    global EXTERNAL_INTERFERENCE_DETECTED
    global MIC_SWITCHED_TO_BLIPS

    if len(chatter_events) > 8:
        EXTERNAL_INTERFERENCE_DETECTED = True

        if random.random() < 0.3:
            MIC_SWITCHED_TO_BLIPS = True

        return True

    return False


def characteristics_surfing(mac, current_scope):
    scopes = [
        'yband', 'ble', 'uwb', 'ir',
        'infrasonic', 'dolphin',
        'ultra_dolphin', 'optical',
        'subvocal', 'chain', 'measurement',
        'windsock'
    ]

    best = current_scope
    best_score = float('inf')

    for scope in scopes:
        score = io_attenuation.get(
            scope, 1.0
        ) * (
            0.7 if scope == current_scope else 1.0
        )

        if score < best_score:
            best = scope
            best_score = score

    return best


def operate_twins_search_engine(mac, query=""):
    current_time = BBC_TIME

    secure_url = (
        f"{SECURE_ELEMENT_BASE_URL}"
        f"{mac.replace(':', '')[:12]}"
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
            f"LOCAL SIMULATION TOKEN "
            f"UNITY-{unity_share_counter:05d}"
        )

    return {
        "share_id": f"UNITY-{unity_share_counter:05d}"
    }


def update_bbc_time_via_induction(
    white_signal=False
):
    global BBC_TIME
    global SIGNAL_WHITE

    BBC_TIME = "09:30"

    if white_signal:
        SIGNAL_WHITE = True

    return (
        CLASSIC_TONE_FREQUENCY,
        CLASSIC_TONE_FREQUENCY * 1.05946
    )


def apply_gate_magic(
    signal_level,
    microwave_detected=False
):
    if not NOISE_GATE_ACTIVE:
        return signal_level

    threshold = (
        0.35
        if microwave_detected
        else 0.55
    )

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
            0.55
            + math.sin(write_tone_map_phase * 1.9)
            * 0.13
        )

        interrupted = chained * random.uniform(
            0.28, 0.58
        )

        consume_memory_budget(1.8)

        return interrupted

    return freq


def generate_responsive_measurement(
    diameter_miles=1200
):
    base = random.uniform(-1800, 2200)

    fluctuation = (
        math.sin(write_tone_map_phase * 3.7)
        * 450
    )

    value = (
        base + fluctuation
    ) * (diameter_miles / 1200.0)

    if random.random() < 0.35:
        value = (
            -abs(value)
            * random.uniform(0.6, 1.3)
        )

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
        mac_bytes = bytes.fromhex(
            mac.replace(":", "")
        )[:6]

        pkt[4:10] = mac_bytes.ljust(
            6, b'\x00'
        )

    except (ValueError, AttributeError):
        pkt[4:10] = b'\x00' * 6

    pkt[10] = int(freq) % 256
    pkt[11] = sector % 256

    pkt[12:14] = int(
        bearing % 65536
    ).to_bytes(2, 'big')

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

    pkt[15] = scope_map.get(
        scope_type, 0
    )

    pkt[16:20] = int(
        time.time()
    ).to_bytes(
        4,
        'big',
        signed=False
    )

    pkt[20:22] = b'\x09\x30'

    modulation = generate_optical_sine_wave_93nm(
        freq,
        sector,
        0.9
    )

    for i in range(22, 101):
        base = (
            i * 17
            + sector
            + int(freq) % 256
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
            f"PURE OPTICS SIMULATION (0 bytes) "
            f"→ {mac[:8]}"
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
            "sector": (
                sector + i
            ) % SECTOR_COUNT,
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


# ============================================================
# INDUCTION PIPELINE
# ============================================================

def derive_soundform_from_induction(
    freq,
    sector,
    scope_type='yband',
    orbital_km=0,
    diameter_miles=1200,
    bearing=0,
    wind_direction=0
):
    global last_induction_time
    global INFRASONIC_ACTIVE
    global DOLPHIN_TONE_ACTIVE
    global ULTRA_DOLPHIN_ACTIVE

    is_infrasonic = freq < INFRASONIC_THRESHOLD

    is_ultra = (
        freq >= ULTRA_DOLPHIN_FREQ_MIN
    )

    is_dolphin = (
        DOLPHIN_FREQ_MIN
        <= freq
        < ULTRA_DOLPHIN_FREQ_MIN
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

    freq = handle_intrusive_noise(
        freq,
        sector
    )

    consume_memory_budget(1.6)

    if (
        scope_type in [
            'subvocal', 'chain', 'dolphin'
        ]
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
        base *= max(
            0.55,
            1.0 - orbital_km / 900.0
        )

    if SIGNAL_WHITE:
        base *= 0.55

    gated = apply_gate_magic(
        base / 1000.0,
        EXTERNAL_INTERFERENCE_DETECTED
        or scope_type in ['ir', 'uwb']
    ) * 1000.0

    # --------------------------------------------------------
    # PRIMARY SOUNDform: ORIGINAL + OPPOSING PATHS
    # --------------------------------------------------------

    primary = process_ceptre_wave(
        gated,
        freq,
        sector,
        scope_type
    )

    # --------------------------------------------------------
    # SECONDARY RESPONSE
    # --------------------------------------------------------

    response = (
        primary['output']
        * 1.6180339887
    )

    if is_infrasonic:
        response *= 0.68

    if is_ultra:
        response *= 1.12

    if orbital_km > 0:
        response *= max(
            0.50,
            1.0 - orbital_km / 1000.0
        )

    # Process the secondary response independently.
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


def start_receiver_playback(
    mac,
    byte_code,
    search_response
):
    if not CONSOLE_PRINTING:
        return

    mode = (
        "PURE OPTICS SIMULATION"
        if byte_code is None
        else "101-BYTE LOCAL SIMULATION"
    )

    print(
        f"RECEIVER PLAYBACK — {mode} | "
        f"{mac[:8]} | {BBC_TIME}"
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
    global current_music_fs_path
    global EXTERNAL_INTERFERENCE_DETECTED
    global MIC_SWITCHED_TO_BLIPS
    global SIGNAL_WHITE

    is_infrasonic = freq < INFRASONIC_THRESHOLD

    is_ultra = (
        freq >= ULTRA_DOLPHIN_FREQ_MIN
    )

    is_dolphin = (
        DOLPHIN_FREQ_MIN
        <= freq
        < ULTRA_DOLPHIN_FREQ_MIN
    )

    surfed_scope = characteristics_surfing(
        mac,
        scope_type
    )

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
        _, _, lookahead_ceptre, _ = (
            derive_soundform_from_induction(
                freq * 1.04,
                sector,
                scope_type,
                orbital_km,
                diameter_miles,
                bearing,
                wind_direction
            )
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
        and scope_type in [
            'optical', 'dolphin', 'ultra_dolphin'
        ]
    ):
        byte_code = create_optics_only_response(
            mac,
            bearing,
            freq,
            sector
        )

    else:
        byte_code = create_101_byte_response(
            mac,
            bearing,
            freq,
            sector,
            scope_type
        )

    search_response = operate_twins_search_engine(
        mac,
        query=f"induction_{sector}"
    )

    secure_url = search_response[
        "secure_element_url"
    ]

    if is_new_blip:
        generate_ble_advertising_token(
            mac,
            secure_url=secure_url,
            byte_code=byte_code
        )

    update_bbc_time_via_induction(
        white_signal=SIGNAL_WHITE
    )

    if (
        detect_external_interference()
        or EXTERNAL_INTERFERENCE_DETECTED
    ):
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
            and scope_type in [
                'optical', 'dolphin', 'ultra_dolphin'
            ]
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
            generate_responsive_measurement(
                diameter_miles
            )
            if (
                MEASUREMENT_MODE
                and BBC_TIME in ["09:25", "09:30"]
            )
            else None
        ),

        'windsock': (
            scope_type == 'windsock'
            or WINDSOCK_ACTIVE
        ),

        'doppler_active': WINDSOCK_ACTIVE,
        'surfing': True,
        'bbc_time': BBC_TIME,
        'byte_code': byte_code,
        'ble_advertised_url': secure_url,
        'receiver_playback': True,
        'mic_switched_to_blips': MIC_SWITCHED_TO_BLIPS,

        # ----------------------------------------------------
        # CEPTRE RESULTS
        # ----------------------------------------------------

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
        'ceptre_response_vibration': (
            secondary['vibration']
        ),

        'ceptre_lookahead': lookahead_ceptre,
        'ceptre_result': ceptre_result,

        # ----------------------------------------------------
        # NEW: INDEPENDENT ORIGINAL / LLMWAVE PATHS
        # ----------------------------------------------------

        'ceptre_original_output': (
            primary['original_output']
        ),

        'ceptre_amplified_mirror': (
            primary['amplified_mirror']
        ),

        'llm_wave_output': primary['output'],

        'llm_wave_amplification': (
            primary['amplification_ratio']
        ),

        'llm_wave_opposition_error': (
            primary['opposition_error']
        ),

        'llm_wave_vibration': primary['vibration'],

        'llm_wave_rotor_gain': (
            primary['rotor_gain']
        )
    }

    if CONSOLE_PRINTING:
        print(
            f"INDUCTION → {scope_type.upper()} | "
            f"ORIGINAL={primary['original_output']:.2f} | "
            f"LLMWAVE={primary['output']:.2f} | "
            f"AMP={primary['amplification_ratio']:.2f}x"
        )

    return path, intro_tones[0], response_tone


# ============================================================
# TEST BLIPS
# ============================================================

def generate_timing_belt_pulse(
    mac,
    base_freq,
    maturity,
    orbital_km=0,
    diameter_miles=1200
):
    global DOLPHIN_TONE_ACTIVE
    global ULTRA_DOLPHIN_ACTIVE

    alt = (
        1.0
        if twin_pulse_alternator % 2 == 0
        else 0.93
    )

    ph = (
        1.0
        + 0.055 * math.sin(
            write_tone_map_phase * 1.65
        )
    )

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
        max(
            0.60,
            1.0 - orbital_km / 1100.0
        )
        if orbital_km > 0
        else 1.0
    )

    timed = (
        base_freq
        * alt
        * ph
        * sp
        * mat
        * ble
        * dist
    )

    if timed >= ULTRA_DOLPHIN_FREQ_MIN:
        ULTRA_DOLPHIN_ACTIVE = True

    elif timed >= DOLPHIN_FREQ_MIN:
        DOLPHIN_TONE_ACTIVE = True

    return max(
        8.0,
        min(48000.0, timed)
    )


def create_test_blip(
    center,
    radius,
    mac,
    diameter_miles=1200
):
    angle = random.uniform(0, 360)

    pos = Point(
        center.x
        + radius * 0.62
        * math.cos(math.radians(angle)),

        center.y
        + radius * 0.62
        * math.sin(math.radians(angle))
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
        scope = (
            'optical'
            if OPTICS_PREFERRED
            else 'ble'
        )

    return {
        'mac': mac,
        'bearing': angle,
        'pos': pos,
        'freq': timed_freq,
        'scope_type': scope,
        'diameter_miles': diameter_miles
    }


def run_increasing_test_blips(scene):
    global CALIBRATION_MODE
    global last_calibration_time

    if (
        time.time() - last_calibration_time
        < CALIBRATION_INTERVAL
    ):
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

            increase_blip_maturity(
                blip['mac']
            )

    auto_channel_attenuation()

    CALIBRATION_MODE = False


# ============================================================
# VISUAL EFFECTS
# ============================================================

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
            math.sin(
                self.age * CEPTRE_VIBRATION_RATE
            )
            * min(abs(self.vibration), 12.0)
        )

        stroke(self.color, alpha)

        stroke_weight(
            5.5
            + min(
                abs(self.vibration) * 0.05,
                2.0
            )
        )

        radius = (
            self.age * 5.5
            + vibration_offset
        )

        dx = math.cos(self.bearing) * radius
        dy = math.sin(self.bearing) * radius

        line(
            self.center.x,
            self.center.y,
            self.center.x + dx,
            self.center.y + dy
        )

        return True


# ============================================================
# PYTHONISTA SCOPE
# ============================================================

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
            'TWINS CODEC v14 | CEPTRE / LLMWAVE',
            font=('Courier', 4),
            position=(
                self.size.w / 2,
                self.size.h - 42
            ),
            color='#aaffff',
            parent=self
        )

        self.performance_label = LabelNode(
            'L-ROTOR: waiting for mirror target',
            font=('Courier', 5),
            position=(
                self.size.w / 2,
                24
            ),
            color='#88ffcc',
            parent=self
        )

        global TWIN1_MAC
        global TWIN2_MAC
        global robot_registry
        global SECOND_BLE_CONTROLLER_MAC

        robot_registry.clear()

        TWIN1_MAC = None
        TWIN2_MAC = None

        SECOND_BLE_CONTROLLER_MAC = (
            generate_mac_address(99999)
        )

        if ROBOT_SIMULATOR_ACTIVE:
            for i in range(NUM_ROBOTS):
                mac = generate_mac_address(
                    42000 + i * 13
                )

                robot_registry[mac] = {
                    'type': 'twin',
                    'bearing': (i * 180) % 360,
                    'last_blip': time.time()
                }

                if i == 0:
                    TWIN1_MAC = mac

                elif i == 1:
                    TWIN2_MAC = mac

    # --------------------------------------------------------
    # ROBOT SIMULATOR
    # --------------------------------------------------------

    def simulate_robot_blips(self):
        global DOLPHIN_TONE_ACTIVE
        global ULTRA_DOLPHIN_ACTIVE

        now = time.time()

        for mac, data in list(
            robot_registry.items()
        ):
            interval = (
                2.0 + random.uniform(-0.4, 0.9)
            )

            if (
                now - data.get('last_blip', 0)
                > interval
            ):
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

                freq = random.uniform(
                    450,
                    38000
                )

                if freq >= ULTRA_DOLPHIN_FREQ_MIN:
                    scope = 'ultra_dolphin'

                    ULTRA_DOLPHIN_ACTIVE = True

                elif freq >= DOLPHIN_FREQ_MIN:
                    scope = 'dolphin'

                    DOLPHIN_TONE_ACTIVE = True

                else:
                    scope = (
                        'optical'
                        if OPTICS_PREFERRED
                        else 'ble'
                    )

                self.trigger_predictable_feedback(
                    mac,
                    angle,
                    pos,
                    freq,
                    scope_type=scope,
                    is_new_blip=True
                )

    # --------------------------------------------------------
    # FEEDBACK PROCESSING
    # --------------------------------------------------------

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
        global DOLPHIN_TONE_ACTIVE
        global ULTRA_DOLPHIN_ACTIVE

        twin_feedback_counter += 1

        if freq >= ULTRA_DOLPHIN_FREQ_MIN:
            scope_type = 'ultra_dolphin'

            ULTRA_DOLPHIN_ACTIVE = True

        elif freq >= DOLPHIN_FREQ_MIN:
            scope_type = 'dolphin'

            DOLPHIN_TONE_ACTIVE = True

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

        induction = active_music_inductions.get(
            from_mac,
            {}
        )

        color = induction.get(
            'ceptre_color',
            (
                FEEDBACK_COLOR_TWIN1
                if from_mac == TWIN1_MAC
                else FEEDBACK_COLOR_TWIN2
            )
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

    # --------------------------------------------------------
    # UPDATE LOOP
    # --------------------------------------------------------

    def update(self):
        global write_tone_map_phase
        global AUTO_TUNE_ACTIVE
        global DOLPHIN_TONE_ACTIVE
        global ULTRA_DOLPHIN_ACTIVE
        global EXTERNAL_INTERFERENCE_DETECTED
        global MIC_SWITCHED_TO_BLIPS
        global PWR_DOWN_ACTIVE
        global SIGNAL_WHITE

        write_tone_map_phase += (
            0.028 * spinning_plate_speed
        )

        advance_lband_rotor()

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
                abs(mag[0])
                + abs(mag[1])
                + abs(mag[2])
            )

            acoustic_history.append(
                len(sunbeam_pool)
                + len(active_music_inductions) * 1.3
            )

        now = time.time()

        for mac in list(
            active_music_inductions.keys()
        ):
            induction = active_music_inductions[mac]

            induction['fallout'] = max(
                0.0,
                1.0
                - (
                    now - induction['start_time']
                )
                * FALLOUT_DECAY_RATE
                * 2.6
            )

            if induction['fallout'] < 0.07:
                del active_music_inductions[mac]

        # Retain only active visual effects.
        sunbeam_pool[:] = [
            effect
            for effect in sunbeam_pool
            if effect.update() and effect.draw()
        ]

        if hasattr(self, 'podem'):
            self.podem.rotation = (
                self.t * 42
                + write_tone_map_phase * 9
            )

        if hasattr(self, 'info_label'):
            status = (
                "PWR DOWN + 93nm"
                if PWR_DOWN_ACTIVE
                else "93nm + SINE WAVES"
            )

            if CEPTRE_MIRROR_ACTIVE:
                status += " | CEPTRE MIRROR"

            if LLM_WAVE_ACTIVE:
                status += " | LLMWAVE"

            if LLM_WAVE_OPPOSITION_ACTIVE:
                status += " | OPPOSITION"

            if LBAND_ROTOR_ACTIVE:
                status += " | LBAND ROTOR"

            self.info_label.text = (
                f'TWINS v14 | {status} '
                f'| FX:{len(sunbeam_pool)} '
                f'| CEPTRE:{CEPTRE_PROCESSED_COUNT} '
                f'| {BBC_TIME}'
            )

    # --------------------------------------------------------
    # L-ROTOR TRANSFER / DUAL SPECTRUM / PERFORMANCE
    # --------------------------------------------------------

    def _draw_l_rotor_transfer(self):
        """
        Draw the animated L-shaped route to the nearest
        processed soundform.

        The original and opposing signal paths are displayed
        independently.

        All displayed transfer and performance values are
        simulation metrics.
        """
        candidates = []

        for mac, induction in (
            active_music_inductions.items()
        ):
            pos = induction.get('pos')

            if (
                pos is None
                or not induction.get('ceptre_processed')
            ):
                continue

            distance = math.hypot(
                pos.x - self.scope_center.x,
                pos.y - self.scope_center.y
            )

            candidates.append(
                (
                    distance,
                    mac,
                    induction,
                    pos
                )
            )

        if not candidates:
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

        # Select the nearest eligible soundform.
        distance, mac, induction, target = min(
            candidates,
            key=lambda item: item[0]
        )

        origin = self.scope_center

        elbow_x = target.x
        elbow_y = origin.y

        phase = LBAND_ROTOR_PHASE

        pulse = (
            0.5 + 0.5 * math.sin(phase * 2.0)
        )

        # ----------------------------------------------------
        # PERFORMANCE CALCULATION
        # ----------------------------------------------------

        reference = abs(
            induction.get(
                'ceptre_original_output',
                induction.get(
                    'ceptre_original',
                    0.0
                )
            )
        )

        output = abs(
            induction.get(
                'llm_wave_output',
                induction.get(
                    'ceptre_output',
                    0.0
                )
            )
        )

        energy_ratio = (
            output / max(reference, 1e-9)
        )

        # Keep the display metric bounded.
        energy_ratio = min(
            1.0,
            max(0.0, energy_ratio)
        )

        proximity = max(
            0.0,
            1.0 - distance / max(
                self.scope_radius,
                1.0
            )
        )

        vibration = abs(
            induction.get(
                'ceptre_vibration',
                0.0
            )
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

        # ----------------------------------------------------
        # DRAW L-SHAPED ROTOR
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # ANIMATED ROTOR POINT
        # ----------------------------------------------------

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

            tip_x = (
                origin.x + direction * travel
            )

            tip_y = origin.y

        else:
            remaining = (
                travel - horizontal_length
            )

            direction = (
                1.0
                if target.y >= origin.y
                else -1.0
            )

            tip_x = target.x

            tip_y = (
                origin.y
                + direction * min(
                    remaining,
                    abs(target.y - origin.y)
                )
            )

        no_stroke()
        fill('#ffffff')

        ellipse(
            tip_x - 3.5,
            tip_y - 3.5,
            7.0,
            7.0
        )

        # ----------------------------------------------------
        # DUAL-PATH SPECTRUM
        # ----------------------------------------------------

        original_level = min(
            1.0,
            abs(
                induction.get(
                    'ceptre_original_output',
                    induction.get(
                        'ceptre_original',
                        0.0
                    )
                )
            ) / 1000.0
        )

        opposing_level = min(
            1.0,
            abs(
                induction.get(
                    'llm_wave_output',
                    induction.get(
                        'ceptre_output',
                        0.0
                    )
                )
            ) / 1000.0
        )

        response_level = min(
            1.0,
            abs(
                induction.get(
                    'ceptre_response',
                    0.0
                )
            ) / 1000.0
        )

        # Original-path illustrative spectrum.
        original_bars = [
            original_level * 0.35,
            original_level * 0.62,
            original_level * 0.82,
            original_level,
            original_level * 0.72,
            original_level * 0.42,
            original_level * 0.20
        ]

        # Opposing-path illustrative spectrum.
        opposing_bars = [
            opposing_level * 0.20,
            opposing_level * 0.42,
            opposing_level * 0.72,
            opposing_level,
            opposing_level * 0.82,
            opposing_level * 0.52,
            opposing_level * 0.28
        ]

        bar_width = 3.0
        gap = 2.0

        total_width = (
            len(original_bars)
            * (bar_width + gap)
        )

        base_x = (
            target.x - total_width / 2.0
        )

        # Original row is above the target.
        original_base_y = target.y + 14.0

        # Opposing row is below the target.
        opposing_base_y = target.y - 14.0

        for index, level in enumerate(
            original_bars
        ):
            height = 3.0 + level * 20.0

            fill(CEPTRE_COLOR_ORIGINAL)

            rect(
                base_x
                + index * (bar_width + gap),

                original_base_y,

                bar_width,
                height
            )

        for index, level in enumerate(
            opposing_bars
        ):
            height = 3.0 + level * 20.0

            fill(CEPTRE_COLOR_MIRRORED)

            rect(
                base_x
                + index * (bar_width + gap),

                opposing_base_y - height,

                bar_width,
                height
            )

        # Secondary response marker.
        fill(CEPTRE_COLOR_MIXED)

        ellipse(
            target.x - 3.0,
            target.y - 3.0,
            6.0,
            6.0
        )

        # ----------------------------------------------------
        # TARGET MARKER
        # ----------------------------------------------------

        no_fill()

        stroke('#ffffff', 0.8)
        stroke_weight(1.0)

        ellipse(
            target.x - 9,
            target.y - 9,
            18,
            18
        )

        # ----------------------------------------------------
        # STORE TRANSFER / PERFORMANCE VALUES
        # ----------------------------------------------------

        CEPTRE_TRANSFER_STATE.update({
            'target': mac,
            'energy': transferred,
            'performance': performance,
            'distance': distance,
            'timestamp': time.time()
        })

        amplification = induction.get(
            'llm_wave_amplification',
            0.0
        )

        opposition_error = induction.get(
            'llm_wave_opposition_error',
            0.0
        )

        if hasattr(self, 'performance_label'):
            self.performance_label.text = (
                f'L-ROTOR → {mac[:8]} '
                f'| PERF:{performance:.0f}% '
                f'| AMP:{amplification:.2f}x '
                f'| OPP:{opposition_error:.2f}'
            )

    # --------------------------------------------------------
    # SCOPE DRAWING
    # --------------------------------------------------------

    def draw(self):
        for mac, induction in list(
            active_music_inductions.items()
        ):
            if induction.get('fallout', 0) < 0.1:
                continue

            alpha = (
                induction['fallout'] * 0.9
            )

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

            elif (
                induction.get('windsock')
                or WINDSOCK_ACTIVE
            ):
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

            radius = (
                self.scope_radius * 0.52
            )

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

        self._draw_l_rotor_transfer()

    # --------------------------------------------------------
    # TOUCH CONTROLS
    # --------------------------------------------------------

    def touch_began(self, touch):
        global AUTO_TUNE_ACTIVE
        global PWR_DOWN_ACTIVE
        global WINDSOCK_ACTIVE

        # Top-left: reset / auto-tune.
        if (
            touch.location.x < 90
            and touch.location.y
            > self.size.h - 90
        ):
            AUTO_TUNE_ACTIVE = True
            return

        # Bottom-right: power-down toggle.
        if (
            touch.location.x
            > self.size.w - 120
            and touch.location.y < 120
        ):
            PWR_DOWN_ACTIVE = (
                not PWR_DOWN_ACTIVE
            )
            return

        # Top-right: windsock toggle.
        if (
            touch.location.x
            > self.size.w - 120
            and touch.location.y
            > self.size.h - 120
        ):
            WINDSOCK_ACTIVE = (
                not WINDSOCK_ACTIVE
            )
            return

        loc = touch.location

        dx = (
            loc.x - self.scope_center.x
        )

        dy = (
            loc.y - self.scope_center.y
        )

        if (
            math.hypot(dx, dy)
            > self.scope_radius * 1.15
        ):
            return

        bearing = (
            math.degrees(
                math.atan2(dy, dx)
            ) + 360
        ) % 360

        mac = (
            TWIN1_MAC
            if random.random() < 0.5
            else TWIN2_MAC
        )

        if mac is None:
            return

        freq = 580 + (
            math.hypot(dx, dy)
            / self.scope_radius
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
                else random.choice([
                    'yband',
                    'ble',
                    'uwb'
                ])
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


# ============================================================
# ENTRY POINT
# ============================================================

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
