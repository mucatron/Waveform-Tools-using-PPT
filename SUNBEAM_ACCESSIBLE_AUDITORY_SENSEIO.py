#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOTTED NET WHICH SURVEY — SUNBEAM ACCESSIBLE AUDITORY HOPS
Pythonista for iOS
@copyright The twins - OI
Local microphone analysis, adaptive acoustic-band learning, gentle musical
hop cues, visual event indication, and opt-in generated-audio test stimuli.

NAU spectral-temporal modifier is applied to:
  - connection handshake tones (original acoustic cue only)
  - HOP triggering (gate sensitivity)
  - HCP detection (high-confidence prediction / tinman_confidence)
  - optional NAU-shifted hop indicator tones

Handshake / negotiation is NOT started by this script. It is discovered
through analysis:
  - HCP permanently available (entropic twin) = Background teal
  - HOP hopping or not; amber when negotiation learning / competing
  - Streaming stable HOP = green; compete held unless gate or push/pull changes

Accessibility notes:
- Uses iOS/Pythonista's normal audio output route.
- Can play to compatible connected audio devices selected by iOS.
- Does not enumerate every hearing aid, guarantee audibility, implement
  proprietary hearing-aid protocols, or transmit Auracast.
- Venue-wide hearing loops / broadcast systems require separate hardware.
- Visual event cues are included; this is not a certified ride safety system.
- Digital gain is not a calibrated sound-pressure limit.
- Audio analysis is short-file/chunk based, not low-latency live DSP.
- Local files only; no network or location access.
- Optional low-level ambient and synthetic speech-like test stimuli are OFF by
  default, selected separately, and never used as evidence of participant intent.
- Generated playback can leak into the microphone; microphone metrics during
  playback may include the stimulus and are not automatically attributed to people.
"""

import os
import time
import math
import wave
import struct
import threading
import traceback
import hashlib
from collections import deque

import sound
import scene

# Pythonista motion sensors are optional. No location/GPS API is imported or used.
try:
    import motion
except Exception:
    motion = None

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

APP_NAME = "SUNBEAM ACCESSIBLE AUDITORY HOPS"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HOP_SOUND_WAV_PATH = os.path.join(SCRIPT_DIR, "shake.wav")
SAMPLE_RATE = 44100
CHANNELS = 2
CAPTURE_SECONDS = 0.60
# User-supplied SIP-style pickup timing signatures. Kept as learning metadata;
# these do not alter HOP triggering or capture timing. Any future classifier
# should learn them independently for each microphone/channel.
PICKUP_CAPTURE_SIGNATURES_SECONDS = (0.568, 0.602)
RESPONSE_SECONDS = 1.65
UI_UPDATE_SECONDS = 0.1

LEARNING_RATE = 0.14
BAND_LEARNING_RATE = 0.06
BAND_EQ_LIMIT_DB = 3.0
MIN_EQ_GAIN_DB = -6.0
MAX_EQ_GAIN_DB = 6.0
BASE_DB = 45.0

CONTEXT_AWARENESS = 140
REASONING_CONTEXT_UNITS = 14
LEARNING_CONTEXT_UNITS = 14

F1_F3_BANDS = {
    "F0": (-20, 80),
    "F1": (-80, 350),
    "F2": (350, 1200),
    "F3": (1200, 4000),
}
IR_SPLIT_BANDS = {
    "F4": (-180, 450),
    "F5": (450, 800),
    "F6": (800, 1400),
    "F7": (1400, 2200),
    "F8": (2200, 3400),
    "F9": (3400, 5200),
    "F10": (5200, 6500),
    "F11": (6500, 7200),
    "F12": (7200, 7900),
    "F13": (7900, 8600),
    "F14": (8600, 9300),
    "F15": (9300, 10000),
    "F16": (10000, 10800),
}
ALL_BANDS = dict(F1_F3_BANDS)
ALL_BANDS.update(IR_SPLIT_BANDS)

DOCS = os.path.expanduser("~/Documents")
LOG_PATH = os.path.join(DOCS, "DOTTED_NET_WHICH_SURVEY.log")
CAPTURE_PATH = os.path.join(DOCS, "DOTTED_NET_CAPTURE.wav")
PROCESSED_PATH = os.path.join(DOCS, "DOTTED_NET_COMPETE_PROCESSED.wav")
RESPONSE_PATH = os.path.join(DOCS, "DOTTED_NET_COMPETE_RESPONSE.wav")
REFERENCE_FILE = os.path.join(DOCS, "DOTTED_NET_1099_REFERENCE.wav")

GATE_OPEN_THRESHOLD = 0.018
GATE_CLOSE_THRESHOLD = 0.013
GATE_HOLD_SECONDS = 0.30
STREAM_JOIN_SECONDS = 0.90
ALERT_COOLDOWN_SECONDS = 1.25

# Microphone-derived gain is bounded and applied to processed local WAV files.
MIC_DRIVE_ENABLED = True
MIC_DRIVE_MAX_GAIN_DB = 6.0
MIC_DRIVE_SMOOTHING = 0.12
MIC_DRIVE_DEADBAND = 0.002
MIC_DRIVE_REFERENCE_ERROR = 0.06

# Optional diagnostic tone; disabled by default for ride use.
REFERENCE_TONE_HZ = 1099.0
REFERENCE_TONE_AMPLITUDE = 0.05
REFERENCE_TONE_SECONDS = 0.45
REFERENCE_AUTO_INTERVAL = 30.0
REFERENCE_TONE_ENABLED = False

# Original family-friendly musical auditory-hop cue.
ACCESSIBILITY_MODE = True
VISUAL_CUES_ENABLED = True
HOP_ENABLED = True
HOP_MASTER_GAIN = 0.10
HOP_MAX_PEAK = 0.12
# Distinct, prominent cue paired with the on-screen HOP indicator. This is a
# digital peak setting, not a calibrated acoustic loudness guarantee.
HOP_INDICATOR_GAIN = 0.58
HOP_INDICATOR_MAX_PEAK = 0.68
HOP_INDICATOR_SECONDS = 1.20
HOP_INDICATOR_PATH = os.path.join(DOCS, "DOTTED_NET_HOP_INDICATOR.wav")
HOP_NOTE_SECONDS = 0.13
HOP_GAP_SECONDS = 0.035
HOP_ATTACK_SECONDS = 0.015
HOP_RELEASE_SECONDS = 0.05
HOP_NOTES = (523.25, 659.25, 783.99, 659.25, 523.25)
HOP_COOLDOWN_SECONDS = 1.25

# Optional generated-audio test stimuli. Both are OFF at launch and mutually
# exclusive. These are local diagnostic stimuli, not negotiation instructions
# or a mechanism for inferring agreement/consent. Digital amplitude is not SPL.
GENERATED_AUDIO_ENABLED = True
BACKGROUND_TEST_AMPLITUDE = 0.018
SPEECHLIKE_TEST_AMPLITUDE = 0.014
GENERATED_AUDIO_SAMPLE_RATE = 22050
GENERATED_AUDIO_SECONDS = 4.0
BACKGROUND_TEST_PATH = os.path.join(DOCS, "SUNBEAM_BACKGROUND_TEST.wav")
SPEECHLIKE_TEST_PATH = os.path.join(DOCS, "SUNBEAM_SPEECHLIKE_TEST.wav")
GENERATED_AUDIO_PLAYER_VOLUME = 0.35  # software volume; not calibrated SPL

# Connection-request handshake cue. Played only when the remote BLE/BTT
# integration reports an actual request; this module does not scan by itself.
CONNECTION_HANDSHAKE_ENABLED = True
CONNECTION_HANDSHAKE_COOLDOWN_SECONDS = 2.0
CONNECTION_HANDSHAKE_GAIN = 0.42
# Four audible two-tone pairs, hopped sequentially in the local WAV handshake.
# These are acoustic indicator tones, not a standards-compliant SIP/BLE radio
# handshake and not RF spread-spectrum transmission.
CONNECTION_HANDSHAKE_FREQUENCY_PAIRS = (
    (697.0, 1209.0),
    (770.0, 1336.0),
    (852.0, 1477.0),
    (941.0, 1633.0),
)
CONNECTION_HANDSHAKE_HOP_SECONDS = 0.14
CONNECTION_HANDSHAKE_PAIR_GAIN = 0.5
# Twin-perspective frequency-shift operator:
# Δν(θ,t) = Δν_Doppler + tt·Δν_T(θ) + Δν_ε
# Defaults are illustrative acoustic offsets and can be calibrated later.
HANDSHAKE_DOPPLER_SHIFT_HZ = 0.0
HANDSHAKE_TT_DELTA_NU_HZ = 18.0
HANDSHAKE_TT_OPERATOR_GAIN = 1.0
HANDSHAKE_EPSILON_SHIFT_HZ = 4.0
HANDSHAKE_EPSILON_HOP_PATTERN = (-1.0, 1.0, 0.5, -0.5)
# NAU: bounded spectral-temporal modifier for the acoustic handshake.
# It varies the frequency offset smoothly over time and by hop slot; it does
# not change HOP triggering, cooldown, microphone capture, or adapter behavior
# unless the HOP/HCP flags below are enabled.
NAU_SPECTRAL_TEMPORAL_ENABLED = True
NAU_TEMPORAL_DEPTH_HZ = 3.0
NAU_TEMPORAL_RATE_HZ = 2.0
NAU_HOP_SPREAD_HZ = 1.5
CONNECTION_HANDSHAKE_PATH = os.path.join(DOCS, "DOTTED_NET_CONNECTION_HANDSHAKE.wav")

# NAU influence on HOP triggering and HCP (high-confidence prediction / event detection).
# Positive values make gates slightly more sensitive and raise confidence when the
# spectral-temporal modifier is active; still hard-bounded.
NAU_HOP_TRIGGER_ENABLED = True
NAU_HCP_DETECTION_ENABLED = True
NAU_GATE_SENSITIVITY_SCALE = 0.12   # fraction of GATE_OPEN_THRESHOLD
NAU_HCP_CONFIDENCE_BOOST = 0.18     # added to tinman_confidence (clamped)
NAU_HOP_FREQUENCY_APPLY = True      # also shift the on-device hop cue tones

# Kept disabled: no high-frequency sweep is needed for the ride cue.
HIGH_RESPONSE_START_HZ = 0.0
HIGH_RESPONSE_END_HZ = 0.0
HIGH_RESPONSE_SECONDS = 0.0
HIGH_RESPONSE_AMPLITUDE = 0.0

STATE_LOCK = threading.RLock()
STOP_EVENT = threading.Event()
CAPTURE_LOCK = threading.Lock()

# Lock-protected, tamper-evident operation ledger. The tiny epsilon advances
# per protected operation; it is deliberately isolated from operational
# thresholds, timings, sample rates, indices, and audio values so it cannot
# silently distort the application's numerical behavior.
INTEGRITY_LOCK = threading.RLock()
INTEGRITY_EPSILON = 1e-9
INTEGRITY_OPERATION_COUNT = 0
INTEGRITY_EPSILON_TOTAL = 0.0
INTEGRITY_CHAIN_HEAD = 'SUNBEAM-INTEGRITY-GENESIS-v1'
INTEGRITY_JOURNAL = []
INTEGRITY_JOURNAL_LIMIT = 10000


def integrity_tick(operation):
    """Append one locked, hash-chained operation record with epsilon progress."""
    global INTEGRITY_OPERATION_COUNT, INTEGRITY_EPSILON_TOTAL, INTEGRITY_CHAIN_HEAD
    label = str(operation)[:120]
    with INTEGRITY_LOCK:
        INTEGRITY_OPERATION_COUNT += 1
        INTEGRITY_EPSILON_TOTAL += INTEGRITY_EPSILON
        payload = '{}|{}|{:.12f}|{}'.format(
            INTEGRITY_OPERATION_COUNT, label, INTEGRITY_EPSILON_TOTAL,
            INTEGRITY_CHAIN_HEAD)
        digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        INTEGRITY_CHAIN_HEAD = digest
        INTEGRITY_JOURNAL.append((INTEGRITY_OPERATION_COUNT, label,
                                  INTEGRITY_EPSILON_TOTAL, digest))
        if len(INTEGRITY_JOURNAL) > INTEGRITY_JOURNAL_LIMIT:
            # Retain a verifiable anchor for the retained segment.
            del INTEGRITY_JOURNAL[0]
        return digest


def verify_integrity_chain():
    """Check retained records for accidental edits or inconsistent counters."""
    with INTEGRITY_LOCK:
        previous = 'SUNBEAM-INTEGRITY-GENESIS-v1'
        expected_count = None
        for count, label, epsilon_total, digest in INTEGRITY_JOURNAL:
            # If the journal has rolled over, the first retained digest has a
            # prior-chain dependency; verify its shape and then verify all later
            # links. Full replay verification is available before rollover.
            if expected_count is None and count > 1:
                if not isinstance(digest, str) or len(digest) != 64:
                    return False
                previous = digest
                expected_count = count
                continue
            payload = '{}|{}|{:.12f}|{}'.format(count, label, epsilon_total, previous)
            expected = hashlib.sha256(payload.encode('utf-8')).hexdigest()
            if expected != digest:
                return False
            previous = digest
            expected_count = count
        if INTEGRITY_JOURNAL:
            last_count, _, last_epsilon, last_digest = INTEGRITY_JOURNAL[-1]
            return (last_count == INTEGRITY_OPERATION_COUNT and
                    abs(last_epsilon - INTEGRITY_EPSILON_TOTAL) <= 1e-12 and
                    last_digest == INTEGRITY_CHAIN_HEAD)
        return INTEGRITY_OPERATION_COUNT == 0


def locked_state_update(updates, operation='state_update'):
    """Apply a group of state mutations atomically under STATE_LOCK."""
    with STATE_LOCK:
        state.update(updates)
    integrity_tick(operation)

state = {
    "running": True,
    "status": "Starting",
    "integrity_status": "ARMED / FIRST CHECK PENDING",
    "integrity_operation_count": 0,
    "integrity_epsilon_total": 0.0,
    "error": "",
    "left_rms": 0.0,
    "right_rms": 0.0,
    "left_pos_rms": 0.0,
    "left_neg_rms": 0.0,
    "right_pos_rms": 0.0,
    "right_neg_rms": 0.0,
    "left_learned": 0.0,
    "right_learned": 0.0,
    "left_gate": False,
    "right_gate": False,
    "left_gate_since": 0.0,
    "right_gate_since": 0.0,
    "left_gate_until": 0.0,
    "right_gate_until": 0.0,
    "tinman_enabled": True,
    "tinman_context": "BACKGROUND",
    "tinman_action": "Observe acoustic context",
    "tinman_confidence": 0.0,
    "connection_transport": "NONE",
    "connection_device_name": "NoName",
    "connection_state": "NO REQUEST",
    "connection_confidence": 0,
    "connection_confidence_label": "No request detected",
    "connection_read_status": "NOT CHECKED",
    "connection_write_status": "NOT CHECKED",
    "connection_identity_status": "NOT CHECKED",
    "connection_handshake_status": "NOT STARTED",
    "connection_last_event": "Waiting for BLE/BTT adapter event",
    "connection_last_sound_time": 0.0,
    "predicted_event": "Background — no negotiation, no HCP",
    "compete": 0.0,
    "compete_delta": 0.0,
    "controller_wave_db": BASE_DB,
    "eq_low_db": 0.0,
    "eq_mid_db": 0.0,
    "eq_high_db": 0.0,
    "bands": {key: 0.0 for key in ALL_BANDS},
    "band_eq_db": {key: 0.0 for key in ALL_BANDS},
    "stream_windows": 0,
    "stream_events": 0,
    "stream_active": False,
    "stream_started": 0.0,
    "last_event_time": 0.0,
    "stream_profile": "LOCAL AUDIO / ACCESSIBLE HOPS",
    "alert_enabled": True,
    "alert_cooldown_until": 0.0,
    "workers": [0] * 16,
    "packet_count": 0,
    "context_count": 0,
    "last_capture": "",
    "last_processed": "",
    "last_response": "",
    "capture_busy": False,
    "playback_busy": False,
    "reference_tone_hz": REFERENCE_TONE_HZ,
    "reference_tone_level": 0.0,
    "eq_compete_reduction": 0.0,
    "mic_positive_envelope": 0.0,
    "mic_signed_error": 0.0,
    "mic_drive_gain_db": 0.0,
    "amplifier_input_rms": 0.0,
    "amplifier_output_rms": 0.0,
    "accessibility_mode": ACCESSIBILITY_MODE,
    "audio_route_status": "SYSTEM-MANAGED / NOT VERIFIED",
    "audio_route_name": "iOS audio output",
    "hearing_access_note": "Confirm the selected device and actual playback.",
    "last_hop_time": 0.0,
    "last_hop_reason": "Waiting for first cue",
    "visual_cue_active": False,
    "nau_influence": 0.0,
    "hcp_active": True,   # permanently available (entropic twin)
    # Handshake / connection visual persistence on the avatar
    "handshake_visual_active": False,
    "connection_pulling": False,
    "message": "Microphone capture is local to this device.",
    "background_management": "IDLE / GENERATED AUDIO OFF",
    "generated_audio_mode": "OFF",
    "generated_audio_status": "OFF — LOCAL TEST STIMULI",
    "generated_audio_volume": GENERATED_AUDIO_PLAYER_VOLUME,
    "generated_audio_mic_caveat": "MIC MAY INCLUDE PLAYBACK LEAKAGE",
    "hop_state": "IDLE",
    "fm_test_active": False,
    "fm_test_status": "NOT RUNNING",
    "fm_test_delta_hz": 0.0,
    "resonance_status": "WAITING FOR CAPTURE",
    "resonance_peak_hz": 0.0,
    "trace_status": "LOCAL TRACE ENABLED",
    "trace_last_bands": [],
    "isolation_status": "BOUNDED STEREO EQ ONLY",
    "privacy_simulation_status": "LOCAL SOFTWARE SIMULATION ONLY",
    "privacy_simulation_score": 0.0,
    "negative_field_simulation": False,
    "mssa_privacy_status": "NOT A VERIFIED SECURITY PROPERTY",
    "entropy_status": "MEASURED INPUTS SEPARATE FROM SIMULATED OUTPUTS",
    "entropy_measured": 0.0,
    "entropy_simulated": 0.0,
    "sunbeam_emission_status": "LOCAL DIAGNOSTIC ONLY / NO NETWORK",
    "consumer_mode": "BLACK",
    "training_mode": False,
    "start_tone_played": False,
    # Generated audio starts OFF at launch; once motion monitoring supplies a sample,
    # D speech-like stimulus is enabled regardless of the calculated threat score.
    "motion_enabled": False,
    "motion_status": "OFF / SENSOR NOT STARTED",
    "motion_strength": 0.0,
    "motion_delta": 0.0,
    "motion_threat": 0.0,
    "motion_trigger": "OFF",
    "motion_threat_label": "Threat: Calm",
    "motion_heading_deg": 0.0,
    "motion_accuracy": "---",
    "motion_head_contact_alpha": 0.0,
    "motion_blips": [],
    "motion_movement_bearing_deg": None,
    "motion_high_threat_proxy_bearing_deg": None,
    "amber_background_active": False,
    "motion_blip_next_index": 0,
    "motion_last_blip_time": 0.0,
    "motion_last_center_blip_time": 0.0,
    "motion_last_poll": 0.0,
    # The attached tracker initializes its previous field strength to zero.
    # Keep that exact first-sample behaviour rather than baseline-calibrating.
    "motion_last_strength": 0.0,
    "motion_baseline_strength": None,
    "motion_scope_visible": True,
    "isolation_mode": "OFF / ADAPTIVE ISOLATION STANDBY",
    "isolation_steering": "NO FREQUENCY MULTIPLIERS OR CUTOFF CHANGES",
    # Motion-triggered negotiation / stereo-D steering are local DSP states.
    "motion_negotiation_active": False,
    "learning_mode_active": False,
    "motion_previous_consumer_mode": None,
    "motion_previous_training_mode": None,
    "entropy_active": False,
    "stereo_d_active": False,
    "stereo_d_status": "OFF / LOCAL STEREO GAIN SIMULATION",
    "stereo_d_target_bearing_deg": 0.0,
    "stereo_d_relative_bearing_deg": 0.0,
    "stereo_d_pan": 0.0,
    "stereo_d_left_multiplier": 1.0,
    "stereo_d_right_multiplier": 1.0,
    "opposite_jitter_active": False,
    "opposite_jitter_bearing_deg": 180.0,
    "opposite_indicator_sound_status": "OFF",
    "motion_last_indicator_time": 0.0,
    "stop_tone_played": False,
}

histories = {
    "left_rms": deque(maxlen=CONTEXT_AWARENESS),
    "right_rms": deque(maxlen=CONTEXT_AWARENESS),
    "prediction_error": deque(maxlen=CONTEXT_AWARENESS),
    "compete_response": deque(maxlen=CONTEXT_AWARENESS),
}


# ---------------------------------------------------------------------------
# UTILITIES / LOGGING
# ---------------------------------------------------------------------------

def log(message):
    line = "[{}] {}".format(time.strftime("%Y-%m-%d %H:%M:%S"), message)
    print(line)
    try:
        os.makedirs(DOCS, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def clamp(value, low, high):
    return max(low, min(high, value))


def rms(values):
    if not values:
        return 0.0
    return math.sqrt(sum(float(v) * float(v) for v in values) / len(values))


def half_rms(values, positive=True):
    selected = [v for v in values if (v >= 0 if positive else v < 0)]
    if not selected:
        return 0.0
    if not positive:
        selected = [-v for v in selected]
    return rms(selected)


def db_to_gain(db):
    return 10.0 ** (float(db) / 20.0)


def safe_unlink(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# WAV I/O AND MICROPHONE CAPTURE
# ---------------------------------------------------------------------------

def read_wav_pcm16(path):
    with wave.open(path, "rb") as wf:
        channels = wf.getnchannels()
        rate = wf.getframerate()
        width = wf.getsampwidth()
        frames = wf.readframes(wf.getnframes())

    if width != 2:
        raise ValueError("Expected 16-bit PCM WAV; got {}-byte samples".format(width))

    count = len(frames) // 2
    samples = list(struct.unpack("<{}h".format(count), frames)) if count else []

    if channels == 1:
        stereo = []
        for sample in samples:
            stereo.extend((sample, sample))
        samples, channels = stereo, 2
    elif channels > 2:
        stereo = []
        for i in range(0, len(samples), channels):
            if i + 1 < len(samples):
                stereo.extend((samples[i], samples[i + 1]))
        samples, channels = stereo, 2

    return rate, channels, samples


def write_wav_pcm16(path, rate, channels, samples):
    safe_unlink(path)
    packed = struct.pack(
        "<{}h".format(len(samples)),
        *[int(clamp(round(v), -32768, 32767)) for v in samples]
    )
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(packed)


def capture_wav(seconds=CAPTURE_SECONDS):
    """Record and validate a short WAV through Pythonista sound.Recorder."""
    with CAPTURE_LOCK:
        safe_unlink(CAPTURE_PATH)
        with STATE_LOCK:
            state["capture_busy"] = True
            state["status"] = "Recording microphone window"
            state["error"] = ""

        recorder = None
        try:
            os.makedirs(DOCS, exist_ok=True)
            recorder = sound.Recorder(CAPTURE_PATH)
            recorder.record()
            time.sleep(max(0.2, float(seconds)))
            recorder.stop()
            recorder = None

            deadline = time.time() + 1.5
            last_size = -1
            stable_checks = 0
            while time.time() < deadline:
                if os.path.isfile(CAPTURE_PATH):
                    try:
                        size = os.path.getsize(CAPTURE_PATH)
                    except OSError:
                        size = 0
                    if size == last_size and size > 44:
                        stable_checks += 1
                        if stable_checks >= 2:
                            break
                    else:
                        stable_checks = 0
                    last_size = size
                time.sleep(0.10)

            if not os.path.isfile(CAPTURE_PATH):
                raise RuntimeError(
                    "Recorder did not create a capture file. Check microphone permission."
                )
            file_size = os.path.getsize(CAPTURE_PATH)
            if file_size <= 44:
                raise RuntimeError(
                    "Recorder output is empty or incomplete. Check microphone permission."
                )

            try:
                with wave.open(CAPTURE_PATH, "rb") as wf:
                    channels = wf.getnchannels()
                    rate = wf.getframerate()
                    width = wf.getsampwidth()
                    frame_count = wf.getnframes()
                    if channels < 1 or rate <= 0 or frame_count <= 0:
                        raise RuntimeError("WAV header contains no audio frames")
                    if width != 2:
                        raise RuntimeError(
                            "Expected 16-bit PCM WAV, found {}-byte samples".format(width)
                        )
            except (wave.Error, EOFError) as exc:
                raise RuntimeError("Recorder output is not a readable PCM WAV: {}".format(exc))

            log("Capture OK: {} bytes, {} Hz, {} channel(s), {} frames.".format(
                file_size, rate, channels, frame_count))
            return CAPTURE_PATH

        except Exception as exc:
            log("Microphone capture failed: {}".format(exc))
            raise
        finally:
            if recorder is not None:
                try:
                    recorder.stop()
                except Exception:
                    pass
            with STATE_LOCK:
                state["capture_busy"] = False


# ---------------------------------------------------------------------------
# ACOUSTIC ANALYSIS
# ---------------------------------------------------------------------------

def channel_samples(samples):
    return samples[0::2], samples[1::2]


def goertzel_power(samples, sample_rate, low_hz, high_hz):
    """Estimate average band energy using a limited set of Goertzel bins."""
    if not samples or len(samples) < 4:
        return 0.0

    n = len(samples)
    nyquist = sample_rate * 0.5
    low_hz = max(1.0, min(float(low_hz), nyquist - 1.0))
    high_hz = max(low_hz, min(float(high_hz), nyquist - 1.0))
    low_bin = max(1, int(low_hz * n / sample_rate))
    high_bin = max(low_bin, min(n // 2 - 1, int(high_hz * n / sample_rate)))
    if high_bin < low_bin:
        return 0.0

    stride = max(1, (high_bin - low_bin + 1) // 8)
    powers = []
    for k in range(low_bin, high_bin + 1, stride):
        omega = 2.0 * math.pi * k / n
        coeff = 2.0 * math.cos(omega)
        s1 = s2 = 0.0
        for sample in samples:
            x = sample / 32768.0
            s0 = x + coeff * s1 - s2
            s2, s1 = s1, s0
        powers.append(max(0.0, s1 * s1 + s2 * s2 - coeff * s1 * s2))

    return math.sqrt(sum(powers) / len(powers)) if powers else 0.0


def analyze_wav(path):
    rate, channels, samples = read_wav_pcm16(path)
    left, right = channel_samples(samples)
    left_n = [x / 32768.0 for x in left]
    right_n = [x / 32768.0 for x in right]
    mono = [(a + b) * 0.5 for a, b in zip(left, right)]
    bands = {
        name: goertzel_power(mono, rate, low, high)
        for name, (low, high) in ALL_BANDS.items()
    }
    return {
        "rate": rate,
        "left_rms": rms(left_n),
        "right_rms": rms(right_n),
        "left_pos_rms": half_rms(left_n, True),
        "left_neg_rms": half_rms(left_n, False),
        "right_pos_rms": half_rms(right_n, True),
        "right_neg_rms": half_rms(right_n, False),
        "bands": bands,
        "samples": samples,
    }


# ---------------------------------------------------------------------------
# GATES, LEARNING AND CONTEXT (NAU → HOP trigger + HCP)
# ---------------------------------------------------------------------------

def update_gate(side, level, now, open_threshold=None):
    opened = False
    thr = GATE_OPEN_THRESHOLD if open_threshold is None else open_threshold
    with STATE_LOCK:
        gate_key = side + "_gate"
        until_key = side + "_gate_until"
        since_key = side + "_gate_since"
        was_open = state[gate_key]

        if level >= thr:
            state[until_key] = now + GATE_HOLD_SECONDS
            if not was_open:
                state[gate_key] = True
                state[since_key] = now
                opened = True
        elif was_open and now > state[until_key] and level < GATE_CLOSE_THRESHOLD:
            state[gate_key] = False
    return opened


def update_context_controller(metrics):
    now = time.time()
    left, right = metrics["left_rms"], metrics["right_rms"]
    mean_level = (left + right) * 0.5
    imbalance = clamp((left - right) * 8.0, -1.0, 1.0)

    # NAU influence for this window (HOP trigger sensitivity + HCP)
    measured_delta = ((left + right) * 0.5) - ((state["left_learned"] + state["right_learned"]) * 0.5)
    nau_inf = nau_influence(measured_delta)
    effective_open = GATE_OPEN_THRESHOLD
    if NAU_HOP_TRIGGER_ENABLED and NAU_SPECTRAL_TEMPORAL_ENABLED:
        effective_open = GATE_OPEN_THRESHOLD * (
            1.0 - NAU_GATE_SENSITIVITY_SCALE * nau_inf
        )
        effective_open = max(GATE_CLOSE_THRESHOLD + 0.002, effective_open)

    left_opened = update_gate("left", left, now, open_threshold=effective_open)
    right_opened = update_gate("right", right, now, open_threshold=effective_open)

    with STATE_LOCK:
        previous_baseline = (state["left_learned"] + state["right_learned"]) * 0.5
        signed_error = mean_level - previous_baseline
        positive_error = max(0.0, signed_error - MIC_DRIVE_DEADBAND)
        previous_envelope = state["mic_positive_envelope"]
        envelope = (
            (1.0 - MIC_DRIVE_SMOOTHING) * previous_envelope
            + MIC_DRIVE_SMOOTHING * positive_error
        )
        drive_db = clamp(
            envelope / max(MIC_DRIVE_REFERENCE_ERROR, 1e-6)
            * MIC_DRIVE_MAX_GAIN_DB,
            0.0, MIC_DRIVE_MAX_GAIN_DB
        )

        state["mic_signed_error"] = signed_error
        state["mic_positive_envelope"] = envelope
        state["mic_drive_gain_db"] = drive_db
        state["amplifier_input_rms"] = mean_level
        state["nau_influence"] = nau_inf
        update_privacy_simulation(measured_delta)

        state["left_rms"], state["right_rms"] = left, right
        state["left_pos_rms"] = metrics["left_pos_rms"]
        state["left_neg_rms"] = metrics["left_neg_rms"]
        state["right_pos_rms"] = metrics["right_pos_rms"]
        state["right_neg_rms"] = metrics["right_neg_rms"]

        state["left_learned"] = (
            (1.0 - LEARNING_RATE) * state["left_learned"] + LEARNING_RATE * left
        )
        state["right_learned"] = (
            (1.0 - LEARNING_RATE) * state["right_learned"] + LEARNING_RATE * right
        )

        bands = metrics["bands"]
        state["bands"] = dict(bands)
        state["packet_count"] += 1
        state["context_count"] += 1

        active = bool(state["left_gate"] or state["right_gate"])
        if active:
            state["tinman_context"] = "ACTIVE ACOUSTIC EVENT"
            state["tinman_action"] = "Apply bounded EQ and microphone-derived gain"
            state["predicted_event"] = "Elevated acoustic transient / speech-like sound"
        elif mean_level > 0.006:
            state["tinman_context"] = "BACKGROUND"
            state["tinman_action"] = "Learn background spectrum"
            state["predicted_event"] = "Background — low-level ambient activity"
        else:
            state["tinman_context"] = "BACKGROUND"
            state["tinman_action"] = "Update baseline; background only"
            state["predicted_event"] = "Background — no negotiation, no HCP"

        # --- Twin / HCP / negotiation / streaming discovery ---
        # HCP is permanently available (entropic twin) → Background teal.
        # HOP is either hopping or not.
        # Negotiation learning → amber; HOP indicator shows amber competing.
        # Streaming stable HOP → green; compete held stable unless gate or
        # push/pull changes restart negotiation.
        base_conf = clamp(
            (mean_level - GATE_CLOSE_THRESHOLD) / 0.08, 0.0, 1.0
        )
        if NAU_HCP_DETECTION_ENABLED and NAU_SPECTRAL_TEMPORAL_ENABLED:
            conf = clamp(base_conf + NAU_HCP_CONFIDENCE_BOOST * nau_inf, 0.0, 1.0)
        else:
            conf = base_conf
        state["tinman_confidence"] = conf

        # HCP permanently available (twin) — always true as background capability
        state["hcp_active"] = True

        # Compete is very sensitive: tracks frequency-group shifts and hop pulls.
        bands = metrics["bands"]
        low_e = bands.get("F1", 0.0) + bands.get("F4", 0.0)
        mid_e = bands.get("F2", 0.0) + bands.get("F5", 0.0) + bands.get("F6", 0.0)
        high_e = (
            bands.get("F3", 0.0) + bands.get("F8", 0.0)
            + bands.get("F9", 0.0) + bands.get("F10", 0.0)
        )
        band_total = low_e + mid_e + high_e + 1e-9
        low_share, mid_share, high_share = (
            low_e / band_total, mid_e / band_total, high_e / band_total
        )
        prev_low = float(state.get("_prev_low_share", low_share))
        prev_mid = float(state.get("_prev_mid_share", mid_share))
        prev_high = float(state.get("_prev_high_share", high_share))
        freq_group_shift = (
            abs(low_share - prev_low)
            + abs(mid_share - prev_mid)
            + abs(high_share - prev_high)
        )
        state["_prev_low_share"] = low_share
        state["_prev_mid_share"] = mid_share
        state["_prev_high_share"] = high_share

        # Compete delta is formed as NAU Δ for context-awareness (>= 0.014).
        # Frequency-group shift is expressed in context units and capped at 14.
        NAU_COMPETE_DELTA = 0.014
        FREQ_GROUP_CONTEXT_UNITS = 14  # matches REASONING/LEARNING context units

        # High-gain compete from imbalance, confidence, and frequency-group motion
        compete_now = clamp(
            abs(imbalance) * 1.8
            + conf * 0.35
            + freq_group_shift * 4.0,
            0.0, 1.0
        )
        prev_compete = float(state.get("compete", 0.0))
        # Very sensitive blend — current window dominates
        blended_compete = clamp(
            0.35 * prev_compete + 0.65 * compete_now, 0.0, 1.0
        )
        # NAU Δ — compete delta for context-awareness
        compete_delta = abs(blended_compete - prev_compete)
        nau_delta = compete_delta

        # Frequency-group shift in context units, hard-capped at <= 14
        freq_units = clamp(
            freq_group_shift * (FREQ_GROUP_CONTEXT_UNITS / 0.15),
            0.0,
            float(FREQ_GROUP_CONTEXT_UNITS),
        )

        prev_left_gate = bool(state.get("_prev_left_gate", False))
        prev_right_gate = bool(state.get("_prev_right_gate", False))
        gate_changed = (
            bool(state["left_gate"]) != prev_left_gate
            or bool(state["right_gate"]) != prev_right_gate
        )
        state["_prev_left_gate"] = bool(state["left_gate"])
        state["_prev_right_gate"] = bool(state["right_gate"])

        push_pull = abs(float(state.get("mic_signed_error", 0.0))) >= 0.004
        streaming = bool(state.get("stream_active"))

        # Underlying compete stays sensitive (NAU Δ / freq units tracked always).
        # On-screen NEGOTIATION label is less sensitive — needs a clearer move.
        NEGOTIATION_NAU_DELTA = 0.045          # label threshold (tracking stays 0.014)
        NEGOTIATION_FREQ_UNITS = 3.0           # of 14; was 1.0 for label
        negotiation = (
            nau_delta >= NEGOTIATION_NAU_DELTA
            or freq_units >= NEGOTIATION_FREQ_UNITS
            or (gate_changed and conf >= 0.40)
            or (push_pull and conf >= 0.40)
            or (active and conf >= 0.55 and nau_delta >= NAU_COMPETE_DELTA)
        )

        state["handshake_visual_active"] = negotiation
        state["_blended_compete"] = blended_compete
        state["_freq_group_shift"] = freq_group_shift
        state["_freq_units"] = freq_units
        state["_nau_delta"] = nau_delta
        # Pulling hops still follows sensitive compete / stream
        state["connection_pulling"] = (
            negotiation
            or nau_delta >= NAU_COMPETE_DELTA
            or freq_units >= 1.0
            or streaming
        )

        if streaming and not negotiation:
            state["tinman_context"] = "STREAMING"
            state["connection_state"] = "STREAMING STABLE (HOP)"
            state["predicted_event"] = "Streaming HOP stable"
            state["tinman_action"] = "Streaming green; compete watched"
            state["connection_handshake_status"] = "VERIFIED"
            state["visual_cue_active"] = VISUAL_CUES_ENABLED
        elif negotiation:
            state["tinman_context"] = "NEGOTIATION"
            state["connection_handshake_status"] = "PENDING"
            state["connection_state"] = "NEGOTIATION LEARNING (ANALYSIS)"
            state["predicted_event"] = (
                "NAU Δ={:.4f} freq_u={:.1f}/14 conf={:.2f} — amber HOP".format(
                    nau_delta, freq_units, conf
                )
            )
            state["tinman_action"] = "NAU Δ / freq-group pull; amber competing HOP"
            state["visual_cue_active"] = VISUAL_CUES_ENABLED
        else:
            state["tinman_context"] = "BACKGROUND"
            state["predicted_event"] = "Background — HCP available (twin); HOP idle"
            state["tinman_action"] = "HCP permanent (twin); teal background"
            state["connection_handshake_status"] = "NOT STARTED"
            state["connection_state"] = "BACKGROUND"
            state["handshake_visual_active"] = False
            if not streaming:
                state["connection_pulling"] = False

        if active:
            if (
                not state["stream_active"]
                or now - state["last_event_time"] > STREAM_JOIN_SECONDS
            ):
                state["stream_started"] = now
                state["stream_events"] = 0
            state["stream_active"] = True
            state["stream_events"] += 1
            state["last_event_time"] = now
        elif state["stream_active"] and now - state["last_event_time"] > STREAM_JOIN_SECONDS:
            state["stream_active"] = False
        state["stream_windows"] += 1

        band_mean = sum(bands.values()) / max(1, len(bands))
        for name, level in bands.items():
            target = clamp(
                (band_mean - level) * 18.0,
                -BAND_EQ_LIMIT_DB, BAND_EQ_LIMIT_DB
            )
            old = state["band_eq_db"].get(name, 0.0)
            state["band_eq_db"][name] = clamp(
                old + BAND_LEARNING_RATE * (target - old),
                -BAND_EQ_LIMIT_DB, BAND_EQ_LIMIT_DB
            )

        state["compete_delta"] = imbalance
        # Very sensitive compete write — frequency-group / hop-pull responsive
        blended = float(state.get("_blended_compete", state["compete"]))
        state["compete"] = clamp(blended, 0.0, 1.0)
        state["eq_compete_reduction"] = 0.0

        low_energy = bands.get("F1", 0.0) + bands.get("F4", 0.0)
        mid_energy = (
            bands.get("F2", 0.0) + bands.get("F5", 0.0) + bands.get("F6", 0.0)
        )
        high_energy = (
            bands.get("F3", 0.0) + bands.get("F8", 0.0)
            + bands.get("F9", 0.0) + bands.get("F10", 0.0)
        )
        total = low_energy + mid_energy + high_energy + 1e-9
        low_share, mid_share, high_share = (
            low_energy / total, mid_energy / total, high_energy / total
        )
        drive = state["compete"] * 2.0
        state["eq_low_db"] = clamp(
            (mid_share - low_share) * 8.0 + drive * 0.35,
            MIN_EQ_GAIN_DB, MAX_EQ_GAIN_DB
        )
        state["eq_mid_db"] = clamp(
            (0.34 - mid_share) * 7.0, MIN_EQ_GAIN_DB, MAX_EQ_GAIN_DB
        )
        state["eq_high_db"] = clamp(
            (mid_share - high_share) * 8.0 - drive * 0.25,
            MIN_EQ_GAIN_DB, MAX_EQ_GAIN_DB
        )
        state["controller_wave_db"] = clamp(
            BASE_DB + state["compete"] * 9.0, 45.0, 54.0
        )

        histories["left_rms"].append(left)
        histories["right_rms"].append(right)
        histories["prediction_error"].append(abs(signed_error))
        for i in range(16):
            state["workers"][i] += 1
        state["status"] = "Microphone window analysed"

    return left_opened or right_opened


# ---------------------------------------------------------------------------
# OFFLINE EQ AND WAV PROCESSING
# ---------------------------------------------------------------------------

def one_pole_filter(samples, rate, cutoff, highpass=False):
    if not samples:
        return []
    cutoff = clamp(float(cutoff), 1.0, rate * 0.45)
    dt = 1.0 / float(rate)
    rc = 1.0 / (2.0 * math.pi * cutoff)
    alpha = dt / (rc + dt)
    out = [0.0] * len(samples)

    if highpass:
        py, px = 0.0, float(samples[0])
        for i, x in enumerate(samples):
            y = alpha * (py + float(x) - px)
            out[i] = y
            py, px = y, float(x)
    else:
        y = float(samples[0])
        for i, x in enumerate(samples):
            y += alpha * (float(x) - y)
            out[i] = y
    return out


def apply_bounded_eq(samples, rate, low_db, mid_db, high_db):
    if not samples:
        return []
    raw = [float(x) for x in samples]
    low = one_pole_filter(raw, rate, 300.0)
    below_high = one_pole_filter(raw, rate, 2800.0)
    high = [x - y for x, y in zip(raw, below_high)]
    mid = [x - lo - hi for x, lo, hi in zip(raw, low, high)]
    gl, gm, gh = [
        db_to_gain(clamp(v, -6.0, 6.0))
        for v in (low_db, mid_db, high_db)
    ]
    out = [lo * gl + mi * gm + hi * gh for lo, mi, hi in zip(low, mid, high)]
    peak = max([abs(x) for x in out] or [1.0])
    if peak > 1.0:
        scale = 1.0 / peak
        out = [x * scale for x in out]
    return out


def apply_stereo_d_and_opposite_jitter(left_samples, right_samples, pan):
    """Apply bounded local stereo steering and smoothing to the opposite channel.

    This is software gain/panning plus a simple one-pole jitter-reduction
    analogue. It is not beamforming, source separation, or guaranteed isolation.
    Input/output samples here are normalized floating-point values.
    """
    pan = clamp(float(pan), -1.0, 1.0)
    left_gain = clamp(1.0 - 0.45 * max(0.0, pan), 0.55, 1.0)
    right_gain = clamp(1.0 - 0.45 * max(0.0, -pan), 0.55, 1.0)
    left_out = [float(v) * left_gain for v in left_samples]
    right_out = [float(v) * right_gain for v in right_samples]

    # Reduce rapid sample-to-sample variation on the side opposite the target.
    # This is deliberately labelled a jitter-reduction analogue, not removal.
    opposite = left_out if pan >= 0.0 else right_out
    alpha = 0.22
    if opposite:
        smooth = [opposite[0]]
        previous = opposite[0]
        for value in opposite[1:]:
            previous += alpha * (value - previous)
            smooth.append(previous)
        if pan >= 0.0:
            left_out = smooth
        else:
            right_out = smooth
    return left_out, right_out, left_gain, right_gain


def process_capture_eq(path):
    """Apply bounded EQ and optional motion-triggered stereo-D processing."""
    try:
        rate, channels, samples = read_wav_pcm16(path)
        left, right = channel_samples(samples)
        with STATE_LOCK:
            low_db = state["eq_low_db"]
            mid_db = state["eq_mid_db"]
            high_db = state["eq_high_db"]
            drive_db = state["mic_drive_gain_db"] if MIC_DRIVE_ENABLED else 0.0
            stereo_d_active = bool(state.get("stereo_d_active", False))
            target_bearing = float(state.get("stereo_d_target_bearing_deg", 0.0))
            current_heading = float(state.get("motion_heading_deg", 0.0))

        left_f = apply_bounded_eq(left, rate, low_db, mid_db, high_db)
        right_f = apply_bounded_eq(right, rate, low_db, mid_db, high_db)
        if stereo_d_active:
            relative_bearing = ((target_bearing - current_heading + 180.0) % 360.0) - 180.0
            pan = math.sin(math.radians(relative_bearing))
            left_f, right_f, left_mult, right_mult = apply_stereo_d_and_opposite_jitter(
                left_f, right_f, pan)
            with STATE_LOCK:
                state["stereo_d_relative_bearing_deg"] = relative_bearing
                state["stereo_d_pan"] = pan
                state["stereo_d_left_multiplier"] = left_mult
                state["stereo_d_right_multiplier"] = right_mult
                state["stereo_d_status"] = (
                    "ACTIVE / LOCAL STEREO GAIN + OPPOSITE-CHANNEL SMOOTHING; "
                    "NOT BEAMFORMING")
        else:
            with STATE_LOCK:
                state["stereo_d_status"] = "OFF / LOCAL STEREO GAIN SIMULATION"
                state["stereo_d_left_multiplier"] = 1.0
                state["stereo_d_right_multiplier"] = 1.0
        # Adaptive resonance/trace: report the strongest existing analysed band.
        with STATE_LOCK:
            bands_snapshot = dict(state.get("bands", {}))
            strongest = max(bands_snapshot, key=bands_snapshot.get) if bands_snapshot else "F0"
            band_ranges = ALL_BANDS.get(strongest, (0, 0))
            state["resonance_peak_hz"] = (band_ranges[0] + band_ranges[1]) * 0.5
            state["resonance_status"] = "ADAPTIVE BAND ESTIMATE (NOT A CALIBRATED RESONANCE MEASUREMENT)"
            state["trace_last_bands"] = sorted(bands_snapshot, key=bands_snapshot.get, reverse=True)[:3]
            state["trace_status"] = "LOCAL TRACE: top bands {}".format(", ".join(state["trace_last_bands"]))
            if state.get("motion_trigger") in ("B", "D"):
                state["isolation_status"] = (
                    "SOFTWARE ISOLATION ANALYSIS ACTIVE; BOUNDED EQ; "
                    "NO HARDWARE BEAMFORMING")
            else:
                state["isolation_status"] = (
                    "BOUNDED STEREO EQ; ISOLATION STANDBY; "
                    "NO HARDWARE BEAMFORMING")
            measured = float(state.get("mic_signed_error", 0.0))
            state["entropy_measured"] = abs(measured)
            state["entropy_simulated"] = clamp(abs(measured) * float(state.get("tinman_confidence", 0.0)), 0.0, 1.0)
            state["entropy_status"] = "{}; MEASURED DELTA {:.5f}; SIMULATED ADAPTATION {:.5f}".format(
                "ACTIVE / LOCAL DIAGNOSTIC" if state.get("entropy_active") else "STANDBY",
                state["entropy_measured"], state["entropy_simulated"])
            state["sunbeam_emission_status"] = "LOCAL DIAGNOSTIC ONLY / NO NETWORK TRANSMISSION"
            state["privacy_simulation_status"] = "LOCAL SOFTWARE SIMULATION ONLY; NOT VERIFIED SECURITY"
            state["mssa_privacy_status"] = "LABEL ONLY; NO MSSA SECURITY CLAIM"
        gain = db_to_gain(drive_db)
        left_f = [x * gain for x in left_f]
        right_f = [x * gain for x in right_f]

        # apply_bounded_eq returns normalized floats for ordinary PCM input;
        # convert back to signed 16-bit PCM before writing the processed WAV.
        pcm_left = [x * 32767.0 for x in left_f]
        pcm_right = [x * 32767.0 for x in right_f]
        stereo = []
        for a, b in zip(pcm_left, pcm_right):
            stereo.extend((a, b))
        write_wav_pcm16(PROCESSED_PATH, rate, 2, stereo)

        with STATE_LOCK:
            state["last_processed"] = PROCESSED_PATH
            state["amplifier_output_rms"] = rms(
                [x / 32768.0 for x in pcm_left + pcm_right]
            )
        return PROCESSED_PATH
    except Exception as exc:
        log("process_capture_eq failed: {}".format(exc))
        return path


def play_file(path):
    """Play a local WAV via Pythonista sound.Player; block until finished."""
    if not path or not os.path.isfile(path):
        raise RuntimeError("play_file: missing path {}".format(path))
    with STATE_LOCK:
        state["playback_busy"] = True
    player = None
    try:
        player = sound.Player(path)
        player.play()
        # Approximate wait: duration from WAV header
        try:
            with wave.open(path, "rb") as wf:
                dur = wf.getnframes() / float(wf.getframerate() or SAMPLE_RATE)
        except Exception:
            dur = 1.5
        time.sleep(min(8.0, max(0.2, dur + 0.05)))
    finally:
        if player is not None:
            try:
                player.stop()
            except Exception:
                pass
        with STATE_LOCK:
            state["playback_busy"] = False


def make_reference_tone_wav():
    rate = SAMPLE_RATE
    n = int(rate * REFERENCE_TONE_SECONDS)
    frames = []
    for i in range(n):
        t = i / float(rate)
        env = min(1.0, t / 0.02) * min(1.0, (REFERENCE_TONE_SECONDS - t) / 0.05)
        val = REFERENCE_TONE_AMPLITUDE * env * math.sin(
            2.0 * math.pi * REFERENCE_TONE_HZ * t
        )
        sample = int(clamp(val, -0.9, 0.9) * 32767)
        frames.extend((sample, sample))
    write_wav_pcm16(REFERENCE_FILE, rate, 2, frames)
    return REFERENCE_FILE


# ---------------------------------------------------------------------------
# NAU + TT HANDSHAKE / HOP HELPERS
# ---------------------------------------------------------------------------

def handshake_delta_nu(theta, t, hop_index):
    """Δν(θ,t) = Δν_Doppler + tt·Δν_T(θ) + Δν_ε"""
    tt_delta_nu = HANDSHAKE_TT_DELTA_NU_HZ * math.cos(
        theta + 2.0 * math.pi * 0.5 * t
    )
    pattern = HANDSHAKE_EPSILON_HOP_PATTERN[
        hop_index % len(HANDSHAKE_EPSILON_HOP_PATTERN)
    ]
    epsilon = HANDSHAKE_EPSILON_SHIFT_HZ * pattern
    return (
        HANDSHAKE_DOPPLER_SHIFT_HZ
        + HANDSHAKE_TT_OPERATOR_GAIN * tt_delta_nu
        + epsilon
    )


def nau_spectral_temporal_modifier(delta_value=0.0):
    """NAU modifier depends only on an input delta, never time/theta/hop index.

    This is a bounded software mapping, not a physical Doppler estimate.
    """
    if not NAU_SPECTRAL_TEMPORAL_ENABLED:
        return 0.0
    scale = max(1e-9, abs(NAU_TEMPORAL_DEPTH_HZ) + abs(NAU_HOP_SPREAD_HZ))
    return clamp(float(delta_value), -scale, scale)


def nau_influence(delta_value=0.0):
    """Bounded NAU influence from a measured/context delta only."""
    if not NAU_SPECTRAL_TEMPORAL_ENABLED:
        return 0.0
    denom = max(1e-6, abs(NAU_TEMPORAL_DEPTH_HZ) + abs(NAU_HOP_SPREAD_HZ))
    return clamp(abs(nau_spectral_temporal_modifier(delta_value)) / denom, 0.0, 1.0)


def make_connection_handshake_wav():
    """Generate four pairs of frequency-hopping tones with TT + NAU."""
    rate = SAMPLE_RATE
    duration = HOP_INDICATOR_SECONDS
    hop_seconds = CONNECTION_HANDSHAKE_HOP_SECONDS
    pair_count = len(CONNECTION_HANDSHAKE_FREQUENCY_PAIRS)
    frames = []
    total_samples = int(rate * duration)

    for i in range(total_samples):
        t = i / float(rate)
        hop_index = int(t / hop_seconds)
        pair_index = hop_index % pair_count
        local_t = t - hop_index * hop_seconds
        pair = CONNECTION_HANDSHAKE_FREQUENCY_PAIRS[pair_index]
        theta = 2.0 * math.pi * pair_index / float(pair_count)
        delta_nu = handshake_delta_nu(theta, t, hop_index)
        # NAU input is a separately captured context delta, not theta/time/hop-derived.
        nau_delta_nu = nau_spectral_temporal_modifier(nau_input_delta)
        combined_delta_nu = delta_nu + nau_delta_nu

        attack = min(1.0, local_t / 0.010)
        release = min(1.0, max(0.0, hop_seconds - local_t) / 0.015)
        envelope = attack * release
        tone_sum = 0.0
        for base_frequency in pair:
            frequency = max(80.0, min(rate * 0.45, base_frequency + combined_delta_nu))
            tone_sum += math.sin(2.0 * math.pi * frequency * local_t)
        value = (
            CONNECTION_HANDSHAKE_GAIN
            * CONNECTION_HANDSHAKE_PAIR_GAIN
            * envelope * 0.5 * tone_sum
        )
        sample = int(clamp(value, -0.90, 0.90) * 32767)
        frames.extend((sample, sample))

    write_wav_pcm16(CONNECTION_HANDSHAKE_PATH, rate, 2, frames)
    log("Handshake spectral-temporal modifier: NAU {} (depth={:.1f} Hz, rate={:.1f} Hz, hop spread={:.1f} Hz).".format(
        "enabled" if NAU_SPECTRAL_TEMPORAL_ENABLED else "disabled",
        NAU_TEMPORAL_DEPTH_HZ,
        NAU_TEMPORAL_RATE_HZ,
        NAU_HOP_SPREAD_HZ,
    ))
    return CONNECTION_HANDSHAKE_PATH


def make_nau_hop_indicator_wav():
    """Short musical hop with NAU spectral-temporal shifts applied to HOP_NOTES."""
    rate = SAMPLE_RATE
    frames = []
    with STATE_LOCK:
        measured_delta = float(state.get("compete_delta", 0.0))
    nau_delta = nau_spectral_temporal_modifier(measured_delta)
    for hop_index, base_hz in enumerate(HOP_NOTES):
        freq = max(80.0, min(rate * 0.45, base_hz + nau_delta))
        n = int(rate * HOP_NOTE_SECONDS)
        gap = int(rate * HOP_GAP_SECONDS)
        for i in range(n):
            t = i / float(rate)
            attack = min(1.0, t / max(1e-6, HOP_ATTACK_SECONDS))
            release = min(1.0, max(0.0, HOP_NOTE_SECONDS - t) / max(1e-6, HOP_RELEASE_SECONDS))
            env = attack * release
            val = HOP_INDICATOR_GAIN * env * math.sin(2.0 * math.pi * freq * t)
            sample = int(clamp(val, -HOP_INDICATOR_MAX_PEAK, HOP_INDICATOR_MAX_PEAK) * 32767)
            frames.extend((sample, sample))
        for _ in range(gap):
            frames.extend((0, 0))
    write_wav_pcm16(HOP_INDICATOR_PATH, rate, 2, frames)
    return HOP_INDICATOR_PATH


def report_connection_request(transport="BLE", device_name="NoName"):
    """
    Entry point for a real BLE/BTT adapter to report an incoming request.

    This function does not discover devices or fabricate a request. The
    adapter must call it only after its own API reports a connection request.
    """
    now = time.time()
    transport = str(transport or "UNKNOWN").upper()
    device_name = str(device_name or "").strip() or "NoName"

    with STATE_LOCK:
        state["connection_transport"] = transport
        state["connection_device_name"] = device_name
        state["connection_state"] = "REQUEST DETECTED"
        state["connection_confidence"] = 15
        state["connection_confidence_label"] = "Request detected; not validated"
        state["connection_read_status"] = "NOT CHECKED"
        state["connection_write_status"] = "NOT CHECKED"
        state["connection_identity_status"] = "NOT CHECKED"
        state["connection_handshake_status"] = "PENDING"
        state["connection_last_event"] = "{} request from {}".format(
            transport, device_name
        )
        state["visual_cue_active"] = VISUAL_CUES_ENABLED
        state["handshake_visual_active"] = True
        state["connection_pulling"] = False
        state["message"] = "Connection request detected; validating"
        previous_sound = state["connection_last_sound_time"]

    log("Connection request reported: transport={}, device={}".format(
        transport, device_name
    ))

    if (
        CONNECTION_HANDSHAKE_ENABLED
        and now - previous_sound >= CONNECTION_HANDSHAKE_COOLDOWN_SECONDS
    ):
        try:
            path = make_connection_handshake_wav()
            with STATE_LOCK:
                state["connection_last_sound_time"] = now
                state["last_response"] = path
                state["connection_last_event"] = (
                    "{} request from {}; local handshake cue requested".format(
                        transport, device_name
                    )
                )
            threading.Thread(
                target=play_file,
                args=(path,),
                daemon=True,
                name="ConnectionHandshakeCue"
            ).start()
            log("Local connection handshake cue requested.")
        except Exception as exc:
            with STATE_LOCK:
                state["connection_handshake_status"] = "SOUND ERROR"
                state["error"] = "Connection handshake cue: {}".format(exc)
            log("Connection handshake sound failed: {}".format(exc))
    return True


def report_connection_check(check, success, detail=""):
    """
    Record an outcome from the BLE/BTT adapter.

    Supported checks: identity, read, write, handshake. Confidence is a
    checklist-completion indicator: 15 request, 35 identity, 55 read,
    75 write, 100 verified handshake. A failed check never means success.
    """
    check = str(check).strip().lower()
    if check not in ("identity", "read", "write", "handshake"):
        raise ValueError("check must be identity, read, write, or handshake")

    with STATE_LOCK:
        if state["connection_state"] == "NO REQUEST":
            state["connection_state"] = "CHECK WITHOUT REQUEST"
            state["connection_confidence"] = 0
            state["connection_confidence_label"] = "No request to validate"

        if check == "identity":
            state["connection_identity_status"] = (
                "VERIFIED" if success else "FAILED"
            )
            if success:
                state["connection_confidence"] = max(
                    state["connection_confidence"], 35
                )
                state["connection_confidence_label"] = "Identity check passed"
        elif check == "read":
            state["connection_read_status"] = "SUPPORTED" if success else "FAILED"
            if success:
                state["connection_confidence"] = max(
                    state["connection_confidence"], 55
                )
                state["connection_confidence_label"] = "Read capability verified"
        elif check == "write":
            state["connection_write_status"] = "SUPPORTED" if success else "FAILED"
            if success:
                state["connection_confidence"] = max(
                    state["connection_confidence"], 75
                )
                state["connection_confidence_label"] = "Write capability verified"
        elif check == "handshake":
            state["connection_handshake_status"] = (
                "VERIFIED" if success else "FAILED"
            )
            if success:
                state["connection_state"] = "HANDSHAKE VERIFIED"
                state["connection_confidence"] = 100
                state["connection_confidence_label"] = (
                    "Handshake checks verified; not a trust score"
                )
                # HOP handshaked successfully → force HCP active and
                # keep handshake indicators visible while connection pulls.
                state["hcp_active"] = True
                state["handshake_visual_active"] = True
                state["connection_pulling"] = True
                state["visual_cue_active"] = VISUAL_CUES_ENABLED
                state["predicted_event"] = (
                    "HCP: handshake verified — connection pulling frames"
                )
                state["tinman_action"] = "HCP held by successful handshake"
                state["tinman_confidence"] = max(
                    float(state.get("tinman_confidence", 0.0)), 1.0
                )
            else:
                state["connection_state"] = "HANDSHAKE FAILED"
                state["connection_confidence_label"] = "Handshake failed"
                state["handshake_visual_active"] = False
                state["connection_pulling"] = False
                # Acoustic HCP may still be true; only clear handshake hold

        if not success:
            state["connection_state"] = (
                "CHECK FAILED: " + check.upper()
            )
            state["connection_confidence_label"] = (
                check.capitalize() + " check failed; connection unverified"
            )
            if check == "handshake":
                state["handshake_visual_active"] = False
                state["connection_pulling"] = False

        state["connection_last_event"] = (
            "{}: {}{}".format(
                check.upper(),
                "PASS" if success else "FAIL",
                " — " + str(detail) if detail else ""
            )
        )
        state["message"] = state["connection_last_event"]

    log("Connection check {}: {}{}".format(
        check, "PASS" if success else "FAIL",
        " ({})".format(detail) if detail else ""
    ))
    return state["connection_confidence"]


def play_hop_device_effect():
    """Play local hop cue; optionally NAU-shifted indicator, else shake.wav."""
    try:
        if NAU_HOP_FREQUENCY_APPLY and NAU_SPECTRAL_TEMPORAL_ENABLED:
            path = make_nau_hop_indicator_wav()
            play_file(path)
            log("HOP (NAU-shifted indicator) playback requested.")
            return True
    except Exception as exc:
        log("NAU hop indicator failed, falling back to shake.wav: {}".format(exc))

    path = HOP_SOUND_WAV_PATH
    if not os.path.isfile(path):
        message = "HOP sound WAV not found beside script: {}".format(path)
        log(message)
        with STATE_LOCK:
            state["error"] = message
        return False

    try:
        play_file(path)
        log("HOP on-screen: shake.wav playback requested locally.")
        return True
    except Exception as exc:
        message = "HOP shake.wav playback failed: {}".format(exc)
        log(message)
        with STATE_LOCK:
            state["error"] = message
        return False


def request_accessible_hop(reason="Acoustic event"):
    now = time.time()

    with STATE_LOCK:
        if not HOP_ENABLED or not state["alert_enabled"]:
            state["last_hop_reason"] = "Audio cue disabled"
            state["message"] = "HOP indicator not shown; audio cue disabled"
            state["visual_cue_active"] = False
            return False

        if state["playback_busy"]:
            state["last_hop_reason"] = "Playback busy"
            state["visual_cue_active"] = False
            return False

        if now - state["last_hop_time"] < HOP_COOLDOWN_SECONDS:
            state["last_hop_reason"] = "Cue cooldown"
            state["visual_cue_active"] = False
            return False

        state["visual_cue_active"] = VISUAL_CUES_ENABLED
        state["hop_state"] = "CUE REQUESTED"
        state["background_management"] = "DEVICE IN USE / SHORT CAPTURE WINDOWS; NO CONTINUOUS GENERATED AUDIO"
        state["last_hop_time"] = now
        state["last_hop_reason"] = str(reason)
        state["message"] = "Auditory hop requested"
        nau_inf = state.get("nau_influence", 0.0)

    try:
        threading.Thread(
            target=play_hop_device_effect,
            daemon=True,
            name="LocalHopDeviceEffect"
        ).start()
        log("Auditory hop requested: {}; NAU influence={:.3f}; cue dispatched".format(
            reason, nau_inf))
        return True
    except Exception as exc:
        with STATE_LOCK:
            state["error"] = str(exc)
            state["message"] = "Auditory-hop playback failed"
        log("Auditory-hop error: {}".format(exc))
        return False


# ---------------------------------------------------------------------------
# OPT-IN GENERATED-AUDIO TEST STIMULI (BACKGROUND / SPEECH-LIKE)
# ---------------------------------------------------------------------------

AUDIO_STREAM_LOCK = threading.RLock()
_audio_stream_stop_event = None
_audio_stream_player = None
_audio_stream_thread = None


def _amber_background_context():
    """True when AMBER is selected or is the saved wheel mode under a B/D override."""
    with STATE_LOCK:
        mode = state.get("consumer_mode", "BLACK")
        previous = state.get("motion_previous_consumer_mode")
        trigger = state.get("motion_trigger", "OFF")
    return mode == "AMBER" or (trigger in ("B", "D") and previous == "AMBER")


def make_background_test_wav(path=BACKGROUND_TEST_PATH):
    """Generate a soft local ambient test bed; AMBER raises sample amplitude by 35%."""
    rate = GENERATED_AUDIO_SAMPLE_RATE
    frames = int(rate * GENERATED_AUDIO_SECONDS)
    samples = []
    amber_gain = 1.35 if _amber_background_context() else 1.0
    for i in range(frames):
        t = i / float(rate)
        # Deterministic, gently varying multi-tone ambience with slow fades.
        fade_in = min(1.0, t / 0.35)
        fade_out = min(1.0, (GENERATED_AUDIO_SECONDS - t) / 0.35)
        envelope = max(0.0, min(fade_in, fade_out))
        slow = 0.70 + 0.18 * math.sin(2.0 * math.pi * 0.19 * t)
        value = BACKGROUND_TEST_AMPLITUDE * amber_gain * envelope * slow * (
            0.56 * math.sin(2.0 * math.pi * 110.0 * t)
            + 0.28 * math.sin(2.0 * math.pi * 164.81 * t + 0.3)
            + 0.16 * math.sin(2.0 * math.pi * 220.0 * t + 0.7)
        )
        sample = int(clamp(round(value * 32767.0), -32768, 32767))
        samples.extend((sample, sample))
    write_wav_pcm16(path, rate, 2, samples)
    return path


def make_speechlike_test_wav(path=SPEECHLIKE_TEST_PATH):
    """Generate nonverbal syllable-like harmonic texture, not intelligible speech."""
    rate = GENERATED_AUDIO_SAMPLE_RATE
    frames = int(rate * GENERATED_AUDIO_SECONDS)
    samples = []
    # Deliberately synthetic, non-linguistic syllable timing and pitch contour.
    syllable_seconds = (0.22, 0.17, 0.27, 0.19, 0.24, 0.16, 0.25, 0.20)
    boundaries = []
    cursor = 0.0
    for j, duration in enumerate(syllable_seconds):
        boundaries.append((cursor, cursor + duration, j))
        cursor += duration + (0.055 if j % 3 else 0.085)
    pattern_length = max(cursor, 0.1)

    for i in range(frames):
        t = i / float(rate)
        local_t = t % pattern_length
        chosen = None
        for start, end, idx in boundaries:
            if start <= local_t < end:
                chosen = (start, end, idx)
                break
        if chosen is None:
            samples.extend((0, 0))
            continue
        start, end, idx = chosen
        phase = (local_t - start) / max(1e-6, end - start)
        attack = min(1.0, phase / 0.14)
        release = min(1.0, (1.0 - phase) / 0.20)
        syllable_env = max(0.0, min(attack, release)) ** 0.7
        f0_start = (112.0, 138.0, 124.0, 151.0, 118.0, 145.0, 130.0, 106.0)[idx]
        f0_end = (132.0, 119.0, 145.0, 128.0, 142.0, 121.0, 111.0, 136.0)[idx]
        f0 = f0_start + (f0_end - f0_start) * phase
        # Broad formant-like weighting creates a voice-like texture without words.
        value = 0.0
        for harmonic in range(1, 19):
            freq = harmonic * f0
            weight = 0.0
            for formant, width, gain in ((700.0, 230.0, 1.0),
                                         (1250.0, 320.0, 0.62),
                                         (2450.0, 520.0, 0.25)):
                weight += gain * math.exp(-0.5 * ((freq - formant) / width) ** 2)
            weight += 0.035 / harmonic
            value += (weight / harmonic) * math.sin(
                2.0 * math.pi * freq * t + 0.11 * harmonic * idx)
        # Keep amplitude conservative and smoothly bounded.
        value *= SPEECHLIKE_TEST_AMPLITUDE * syllable_env
        sample = int(clamp(round(value * 32767.0), -32768, 32767))
        samples.extend((sample, sample))
    write_wav_pcm16(path, rate, 2, samples)
    return path


def _audio_stream_worker(mode, stop_event):
    global _audio_stream_player
    path = BACKGROUND_TEST_PATH if mode == "BACKGROUND" else SPEECHLIKE_TEST_PATH
    maker = make_background_test_wav if mode == "BACKGROUND" else make_speechlike_test_wav
    player = None
    try:
        if not GENERATED_AUDIO_ENABLED:
            raise RuntimeError("Generated audio disabled by configuration")
        if not os.path.isfile(path):
            maker(path)
        # Rebuild each time so edits to configured amplitude are reflected.
        maker(path)
        player = sound.Player(path)
        try:
            player.volume = float(state.get("generated_audio_volume", GENERATED_AUDIO_PLAYER_VOLUME))
        except Exception:
            pass
        # Pythonista Player supports number_of_loops on common versions.
        # Fall back to repeated finite playback if the property is unavailable.
        looping = False
        try:
            player.number_of_loops = -1
            looping = True
        except Exception:
            looping = False
        with AUDIO_STREAM_LOCK:
            _audio_stream_player = player
        player.play()
        if looping:
            while not stop_event.wait(0.10) and not STOP_EVENT.is_set():
                pass
        else:
            duration = GENERATED_AUDIO_SECONDS
            while not stop_event.is_set() and not STOP_EVENT.is_set():
                if stop_event.wait(max(0.05, duration)):
                    break
                try:
                    player.stop()
                    player = sound.Player(path)
                    try:
                        player.volume = float(state.get("generated_audio_volume", GENERATED_AUDIO_PLAYER_VOLUME))
                    except Exception:
                        pass
                    with AUDIO_STREAM_LOCK:
                        _audio_stream_player = player
                    player.play()
                except Exception:
                    break
    except Exception as exc:
        with STATE_LOCK:
            if state.get("generated_audio_mode") == mode:
                state["generated_audio_status"] = "ERROR: {}".format(exc)
                state["generated_audio_mode"] = "OFF"
                state["background_management"] = "ERROR / GENERATED AUDIO OFF"
        log("Generated audio stream error ({}): {}".format(mode, exc))
    finally:
        if player is not None:
            try:
                player.stop()
            except Exception:
                pass
        with AUDIO_STREAM_LOCK:
            if _audio_stream_player is player:
                _audio_stream_player = None
        with STATE_LOCK:
            if state.get("generated_audio_mode") == mode and (stop_event.is_set() or STOP_EVENT.is_set()):
                state["generated_audio_mode"] = "OFF"
                state["generated_audio_status"] = "OFF — LOCAL TEST STIMULI"
                state["background_management"] = "DEVICE IN USE / GENERATED AUDIO OFF"


def adjust_generated_audio_volume(delta):
    """Adjust software playback volume within a conservative bounded range."""
    global _audio_stream_player
    with STATE_LOCK:
        current = float(state.get("generated_audio_volume", GENERATED_AUDIO_PLAYER_VOLUME))
        updated = clamp(current + float(delta), 0.05, 0.65)
        state["generated_audio_volume"] = updated
        state["message"] = "Generated audio software volume {:.2f} (not calibrated SPL)".format(updated)
    with AUDIO_STREAM_LOCK:
        player = _audio_stream_player
    if player is not None:
        try:
            player.volume = updated
        except Exception as exc:
            log("Generated audio volume update warning: {}".format(exc))
    log("Generated audio software volume set to {:.2f}; not a calibrated SPL value.".format(updated))
    return updated


def stop_generated_audio_stream():
    """Stop current generated stimulus immediately and mark diagnostics OFF."""
    global _audio_stream_stop_event, _audio_stream_player
    with AUDIO_STREAM_LOCK:
        event = _audio_stream_stop_event
        player = _audio_stream_player
        if event is not None:
            event.set()
        _audio_stream_player = None
    if player is not None:
        try:
            player.stop()
        except Exception as exc:
            log("Generated audio stop warning: {}".format(exc))
    with STATE_LOCK:
        state["generated_audio_mode"] = "OFF"
        state["generated_audio_status"] = "OFF — LOCAL TEST STIMULI"
        if not STOP_EVENT.is_set():
            state["background_management"] = "DEVICE IN USE / GENERATED AUDIO OFF"
    integrity_tick('generated_audio_stop')
    log("Generated audio stream stopped.")


def set_generated_audio_mode(mode):
    """Toggle BACKGROUND or SPEECHLIKE; only one generated mode runs at once."""
    global _audio_stream_stop_event, _audio_stream_thread
    mode = str(mode).upper()
    if mode not in ("BACKGROUND", "SPEECHLIKE"):
        raise ValueError("mode must be BACKGROUND or SPEECHLIKE")
    with STATE_LOCK:
        current = state.get("generated_audio_mode", "OFF")
    if current == mode:
        stop_generated_audio_stream()
        return False
    stop_generated_audio_stream()
    if STOP_EVENT.is_set():
        return False
    event = threading.Event()
    with AUDIO_STREAM_LOCK:
        _audio_stream_stop_event = event
    with STATE_LOCK:
        state["generated_audio_mode"] = mode
        state["generated_audio_status"] = mode + " ACTIVE / LOCAL TEST STIMULUS"
        state["background_management"] = "DEVICE IN USE / {} STREAM ACTIVE".format(mode)
        state["generated_audio_mic_caveat"] = "MIC MAY INCLUDE PLAYBACK LEAKAGE"
        state["message"] = "{} stimulus active; microphone may include playback".format(mode)
    _audio_stream_thread = threading.Thread(
        target=_audio_stream_worker, args=(mode, event), daemon=True,
        name="SunbeamGeneratedAudio-" + mode)
    _audio_stream_thread.start()
    integrity_tick('generated_audio_mode:' + mode)
    log("Generated audio mode enabled: {} (local test stimulus; not participant-intent evidence).".format(mode))
    return True


# ---------------------------------------------------------------------------
# MOTION-TRIGGERED B/D MODES (LOCAL SENSOR ONLY; NO LOCATION ACCESS)
# ---------------------------------------------------------------------------

MOTION_POLL_SECONDS = 0.20
MOTION_MOVEMENT_THRESHOLD = 1.5
MOTION_HIGH_THREAT_THRESHOLD = 4.0
# Retained compatibility settings from the prior integration. The tracker-
# fidelity path below intentionally follows the attached source's direct
# thresholds (no hysteresis) so visual B/D states and audio outcomes match it.
MOTION_MOVEMENT_RELEASE_THRESHOLD = 1.2
MOTION_HIGH_THREAT_RELEASE_THRESHOLD = 3.5
_motion_started = False


def start_motion_monitor():
    """Start Pythonista motion updates when available; leave audio OFF at launch."""
    global _motion_started
    if motion is None:
        with STATE_LOCK:
            state["motion_enabled"] = False
            state["motion_status"] = "UNAVAILABLE / MOTION MODULE NOT PRESENT"
        log("Motion trigger unavailable; D cannot start without local motion samples.")
        return False
    try:
        motion.start_updates()
        _motion_started = True
        with STATE_LOCK:
            state["motion_enabled"] = True
            state["motion_status"] = "READY / WAITING FOR MOTION EVENT"
        log("Motion updates started. D speech-like stimulus will be enabled at every threat score once a sample arrives.")
        return True
    except Exception as exc:
        with STATE_LOCK:
            state["motion_enabled"] = False
            state["motion_status"] = "ERROR: {}".format(exc)
        log("Motion sensor start failed: {}".format(exc))
        return False


def stop_motion_monitor():
    global _motion_started
    if motion is not None and _motion_started:
        try:
            motion.stop_updates()
        except Exception as exc:
            log("Motion stop warning: {}".format(exc))
    _motion_started = False


def update_motion_trigger(now=None):
    """Mirror the supplied tracker's field-strength, threat and blip rules.

    B = movement range (1.5 <= threat < 4); D = high-threat/head-contact
    proxy (threat >= 4). The magnetometer does not verify a physical head
    impact. The scope is display-only; B/D semantics never depend on its UI
    position. No GPS/location API is used.
    """
    if motion is None or not _motion_started or STOP_EVENT.is_set():
        return
    now = time.monotonic() if now is None else now
    with STATE_LOCK:
        last_poll = state.get("motion_last_poll", 0.0)
    if now - last_poll < MOTION_POLL_SECONDS:
        return
    try:
        mag = motion.get_magnetic_field()
    except Exception as exc:
        with STATE_LOCK:
            state["motion_status"] = "READ ERROR: {}".format(exc)
        return
    if not mag:
        with STATE_LOCK:
            state["motion_status"] = "WAITING FOR MAGNETIC-FIELD SAMPLE"
        return

    try:
        x, y, z, accuracy = mag
        x, y, z = float(x), float(y), float(z)
        strength = math.sqrt(x ** 2 + y ** 2 + z ** 2)
        heading_deg = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
    except Exception as exc:
        with STATE_LOCK:
            state["motion_status"] = "INVALID SAMPLE: {}".format(exc)
        return

    # Exact supplied tracker formula: first previous strength is zero.
    with STATE_LOCK:
        previous_strength = float(state.get("motion_last_strength", 0.0))
        delta = abs(strength - previous_strength)
        threat = min(max((strength / 20.0) + (delta * 8.0), 0.0), 10.0)
        previous_trigger = state.get("motion_trigger", "OFF")
        state["motion_last_poll"] = now
        state["motion_last_strength"] = strength
        state["motion_strength"] = strength
        state["motion_delta"] = delta
        state["motion_threat"] = threat
        state["motion_heading_deg"] = heading_deg
        state["motion_accuracy"] = str(accuracy)
        state["motion_status"] = "ACTIVE / MAGNETOMETER PROXY"

        # Threat score controls only the diagnostic label and display alpha.
        # D is enabled at ALL scores; it is not gated by the threat thresholds.
        if threat < MOTION_MOVEMENT_THRESHOLD:
            threat_label = "Threat: Calm"
            head_alpha = 0.0
        elif threat < MOTION_HIGH_THREAT_THRESHOLD:
            threat_label = "Threat: Movement Detected"
            head_alpha = 0.6
        else:
            threat_label = "Threat: CLOSE CONTACT! (MAGNETOMETER PROXY)"
            head_alpha = 1.0
        trigger = "D"

        state["motion_threat_label"] = threat_label
        state["motion_head_contact_alpha"] = head_alpha
        state["motion_trigger"] = trigger
        active = trigger in ("B", "D")
        was_active = previous_trigger in ("B", "D")
        if active and not was_active:
            state["motion_previous_consumer_mode"] = state.get("consumer_mode", "BLACK")
            state["motion_previous_training_mode"] = bool(state.get("training_mode", False))
        if active:
            # The motion-triggered negotiation presentation is explicitly GREEN
            # and learning is marked in progress while B or D remains active.
            state["consumer_mode"] = "GREEN"
            state["training_mode"] = True
            state["motion_negotiation_active"] = True
            state["learning_mode_active"] = True
            state["entropy_active"] = True
            state["stereo_d_active"] = True
            state["stereo_d_status"] = "ACTIVE / LOCAL STEREO GAIN + OPPOSITE-CHANNEL SMOOTHING; NOT BEAMFORMING"
            state["opposite_jitter_active"] = True
            state["opposite_indicator_sound_status"] = "ACTIVE / SHORT PERIODIC CHIRP"
            state["isolation_mode"] = "ACTIVE / SOFTWARE STEREO-D + OPPOSITE-CHANNEL JITTER-REDUCTION ANALOGUE"
            state["isolation_steering"] = "BOUNDED STEREO GAINS; NO HARDWARE BEAMFORMING OR VERIFIED ISOLATION"
        else:
            if was_active:
                previous_mode = state.get("motion_previous_consumer_mode")
                previous_training = state.get("motion_previous_training_mode")
                if previous_mode in ("BLACK", "RED", "AMBER", "GREEN"):
                    state["consumer_mode"] = previous_mode
                if previous_training is not None:
                    state["training_mode"] = bool(previous_training)
            state["motion_negotiation_active"] = False
            state["learning_mode_active"] = False
            state["entropy_active"] = False
            state["stereo_d_active"] = False
            state["stereo_d_status"] = "OFF / LOCAL STEREO GAIN SIMULATION"
            state["stereo_d_left_multiplier"] = 1.0
            state["stereo_d_right_multiplier"] = 1.0
            state["opposite_jitter_active"] = False
            state["opposite_indicator_sound_status"] = "OFF"
            state["isolation_mode"] = "OFF / ADAPTIVE ISOLATION STANDBY"
            state["isolation_steering"] = "NO FREQUENCY MULTIPLIERS OR CUTOFF CHANGES"
        state["message"] = (
            "D speech-like stimulus enabled at all threat scores — GREEN negotiation learning; "
            "magnetometer is not a verified impact detector")

        # Every detected marker is also a D activation event. D means the
        # local speech-like test stimulus; it is not a confirmed impact signal.
        d_blip_event = False
        def add_detected_blip(kind, event_heading, **details):
            nonlocal d_blip_event
            blips = state.setdefault("motion_blips", [])
            marker = {"kind": kind, "created": now, "expires": now + 3.0,
                      "heading": event_heading % 360.0}
            marker.update(details)
            blips.append(marker)
            d_blip_event = True
            state["motion_d_blip_count"] = int(state.get("motion_d_blip_count", 0)) + 1
            state["motion_d_last_blip_time"] = now
            state["motion_d_last_blip_kind"] = kind
            state["motion_d_requested"] = 1.0

        # Tracker's forced centre blip remains at the centre. Label it as a
        # HEAD IMPACT, not as a measured physical impact location.
        if threat >= MOTION_HIGH_THREAT_THRESHOLD and (now - float(state.get("motion_last_center_blip_time", 0.0)) > 3.0):
            state["motion_last_center_blip_time"] = now
            add_detected_blip("center", heading_deg, event_type="high_threat_proxy",
                              strength=strength, delta=delta, threat=threat)
            state["motion_high_threat_proxy_bearing_deg"] = heading_deg

        # Tracker's directional blip rule: delta > 2, threat > 3, 0.5 s cooldown.
        if delta > 2.0 and threat > 3.0 and (
                now - float(state.get("motion_last_blip_time", 0.0)) > 0.5):
            state["motion_last_blip_time"] = now
            # Regression fix: restore the original shared "directional" marker
            # type consumed by the original scope renderer. Keep B/D semantics in
            # diagnostics/state, not in the marker schema used for drawing.
            add_detected_blip("directional", heading_deg,
                              event_type=("high_threat_proxy" if threat >= MOTION_HIGH_THREAT_THRESHOLD else
                                          "movement" if threat >= MOTION_MOVEMENT_THRESHOLD else "directional"),
                              strength=strength, delta=delta, threat=threat)
            if threat >= MOTION_HIGH_THREAT_THRESHOLD:
                state["motion_high_threat_proxy_bearing_deg"] = heading_deg
                label = "HEAD IMPACT"
            elif threat >= MOTION_MOVEMENT_THRESHOLD:
                state["motion_movement_bearing_deg"] = heading_deg
                label = "movement"
            else:
                label = "directional / low-threat sample"
            distance = max(1.0, 100.0 - threat * 20.0 - delta * 10.0)
            log("{} blip at {:.0f}° | estimated distance {:.0f} m | threat {:.1f} | field {:.1f} μT | Δ {:.2f}".format(
                label, heading_deg, distance, threat, strength, delta))

        # Keep the latest eight single-location detected events.
        state["motion_blips"] = state.get("motion_blips", [])[-8:]
        latest_directional = next(
            (b for b in reversed(state["motion_blips"])
             if b.get("kind") in ("directional", "movement", "impact_proxy")),
            None)
        # Freeze steering to the most recent directional blip while active;
        # fall back to the current heading when only a centre event exists.
        target_bearing = (float(latest_directional.get("heading", heading_deg))
                          if latest_directional else heading_deg)
        state["stereo_d_target_bearing_deg"] = target_bearing % 360.0
        state["opposite_jitter_bearing_deg"] = (target_bearing + 180.0) % 360.0
        relative_bearing = ((target_bearing - heading_deg + 180.0) % 360.0) - 180.0
        state["stereo_d_relative_bearing_deg"] = relative_bearing
        state["stereo_d_pan"] = math.sin(math.radians(relative_bearing))
        should_play_indicator = False
        if active:
            last_indicator = float(state.get("motion_last_indicator_time", 0.0))
            if (not was_active) or (now - last_indicator >= 1.5):
                state["motion_last_indicator_time"] = now
                should_play_indicator = True

    integrity_tick('motion_sample')
    integrity_ok = verify_integrity_chain()
    locked_state_update({
        'integrity_status': ('OK / HASH-CHAIN CHECK PASSED' if integrity_ok
                             else 'WARNING / INTEGRITY CHAIN MISMATCH')
    }, operation='integrity_check_result')
    with STATE_LOCK:
        state['integrity_operation_count'] = INTEGRITY_OPERATION_COUNT
        state['integrity_epsilon_total'] = INTEGRITY_EPSILON_TOTAL

    # Every newly detected centre or directional blip requests D. If D is
    # already playing, keep it running (do not toggle it off); otherwise start it.
    if d_blip_event:
        with STATE_LOCK:
            d_mode_now = state.get("generated_audio_mode", "OFF")
            d_count_now = int(state.get("motion_d_blip_count", 0))
        if d_mode_now != "SPEECHLIKE":
            set_generated_audio_mode("SPEECHLIKE")
        else:
            log("D remains active for detected blip #{} ({}).".format(
                d_count_now, state.get("motion_d_last_blip_kind", "blip")))
        integrity_tick('D_activation_for_detected_blip')

    # D speech-like stimulus is enabled for every score after a motion sample.
    # Switch only when the trigger changes, not on every scope redraw.
    if trigger != previous_trigger:
        if trigger == "OFF":
            stop_generated_audio_stream()
            with STATE_LOCK:
                restored_mode = state.get("consumer_mode", "BLACK")
            if restored_mode == "AMBER":
                with STATE_LOCK:
                    state["amber_background_active"] = True
                set_generated_audio_mode("BACKGROUND")
                log("Tracker returned to AMBER; boosted background stimulus resumed.")
            else:
                with STATE_LOCK:
                    state["amber_background_active"] = False
                log("Motion tracker stopped or trigger reset; generated audio OFF.")
        elif trigger == "B":
            set_generated_audio_mode("BACKGROUND")
            log("Tracker state: Movement detected -> B background sound.")
        else:
            set_generated_audio_mode("SPEECHLIKE")
            log("Tracker state: D speech-like stimulus enabled at ALL threat scores; magnetometer is not a verified impact detector.")
    if should_play_indicator:
        threading.Thread(target=play_motion_direction_indicator, daemon=True,
                         name="SunbeamMotionDirectionIndicator").start()


# ---------------------------------------------------------------------------
# FINITE INDICATION TONES, FM TEST STATE, AND LOCAL SIMULATION DIAGNOSTICS
# ---------------------------------------------------------------------------

def make_indication_tone(path, frequency, seconds=0.10, amplitude=0.08):
    """Write a finite, enveloped indication tone; never a continuous stream."""
    rate = SAMPLE_RATE
    count = int(rate * seconds)
    frames = []
    for i in range(count):
        t = i / float(rate)
        env = min(1.0, t / 0.01) * min(1.0, (seconds - t) / 0.02)
        v = int(clamp(amplitude * max(0.0, env) * math.sin(2.0 * math.pi * frequency * t), -0.2, 0.2) * 32767)
        frames.extend((v, v))
    write_wav_pcm16(path, rate, 2, frames)
    return path


def play_indication_tone(start=True):
    path = os.path.join(DOCS, "SUNBEAM_START.wav" if start else "SUNBEAM_STOP.wav")
    make_indication_tone(path, 880.0 if start else 440.0, 0.12, 0.06)
    try:
        play_file(path)
    except Exception as exc:
        log("Indication tone playback unavailable: {}".format(exc))
    with STATE_LOCK:
        state["start_tone_played" if start else "stop_tone_played"] = True


def play_motion_direction_indicator():
    """Play a short, finite reminder chirp while motion steering is active."""
    path = os.path.join(DOCS, "SUNBEAM_DIRECTION_ACTIVE.wav")
    try:
        make_indication_tone(path, 1040.0, 0.085, 0.045)
        play_file(path)
    except Exception as exc:
        log("Motion-direction indicator sound unavailable: {}".format(exc))


def set_fm_test(active):
    """Keep FM testing explicitly separate from HOP state and audio worker."""
    with STATE_LOCK:
        state["fm_test_active"] = bool(active)
        state["fm_test_status"] = "ARMED / LOCAL ANALYSIS ONLY" if active else "NOT RUNNING"
        if active:
            state["message"] = "FM test armed; HOP state remains separate"
        else:
            state["message"] = "FM test stopped; HOP state unchanged"
    log("FM test state changed: {} (HOP state remains independent)".format(bool(active)))


def update_privacy_simulation(delta_value):
    """Non-security simulation metric; never performs or claims hardware beamforming."""
    score = clamp(abs(float(delta_value)) / max(1e-6, GATE_OPEN_THRESHOLD), 0.0, 1.0)
    with STATE_LOCK:
        state["negative_field_simulation"] = True
        state["privacy_simulation_score"] = score
        state["privacy_simulation_status"] = "LOCAL NEGATIVE-FIELD ANALOGUE SIMULATION {:.2f}; NOT HARDWARE BEAMFORMING".format(score)
        state["mssa_privacy_status"] = "SIMULATION ONLY; SECURITY NOT VERIFIED"


# ---------------------------------------------------------------------------
# AUDIO WORKER
# ---------------------------------------------------------------------------

def audio_worker():
    log("Starting local microphone capture, learning and accessible hop loop.")
    log("NAU → HOP trigger: {} | NAU → HCP detection: {} | NAU hop tones: {}".format(
        NAU_HOP_TRIGGER_ENABLED, NAU_HCP_DETECTION_ENABLED, NAU_HOP_FREQUENCY_APPLY))

    try:
        play_indication_tone(True)
        request_accessible_hop("Startup audio test")
    except Exception as exc:
        log("Startup hop test failed: {}".format(exc))

    last_reference_play = 0.0

    while not STOP_EVENT.is_set():
        try:
            now = time.time()
            with STATE_LOCK:
                due = (
                    REFERENCE_TONE_ENABLED
                    and state["alert_enabled"]
                    and not state["playback_busy"]
                    and now - last_reference_play >= REFERENCE_AUTO_INTERVAL
                )

            if due:
                reference = make_reference_tone_wav()
                threading.Thread(
                    target=play_file,
                    args=(reference,),
                    daemon=True,
                    name="TinManReferenceTone"
                ).start()
                last_reference_play = time.time()

            path = capture_wav(CAPTURE_SECONDS)
            metrics = analyze_wav(path)
            newly_opened = update_context_controller(metrics)

            with STATE_LOCK:
                state["last_capture"] = path
                nau_inf = state.get("nau_influence", 0.0)
                hcp = state.get("hcp_active", False)

            process_capture_eq(path)

            if newly_opened:
                with STATE_LOCK:
                    histories["compete_response"].append(state["compete"])
                reason = "Microphone gate opened"
                if hcp:
                    reason = "HCP + gate opened (NAU-assisted)"
                request_accessible_hop(reason)
                log("NAU influence at HOP/HCP: {:.3f} (hcp_active={})".format(
                    nau_inf, hcp))
            else:
                with STATE_LOCK:
                    state["message"] = "Learning continues; processed WAV saved locally"

            time.sleep(0.02)

        except Exception as exc:
            with STATE_LOCK:
                state["error"] = str(exc)
                state["status"] = "Audio worker error"
                state["message"] = "Check microphone permission and Pythonista sound API"
            log("Audio worker error: {}\n{}".format(exc, traceback.format_exc()))
            time.sleep(1.0)

    log("Audio worker stopped.")


# ---------------------------------------------------------------------------
# PYTHONISTA PORTRAIT UI
# ---------------------------------------------------------------------------

def color_rgba(value):
    if isinstance(value, (tuple, list)) and len(value) >= 3:
        vals = [float(v) for v in value[:4]]
        if len(vals) == 3:
            vals.append(1.0)
        return tuple(vals)
    if isinstance(value, str) and value.startswith("#"):
        h = value[1:]
        if len(h) == 6:
            h += "FF"
        if len(h) == 8:
            try:
                return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4, 6))
            except ValueError:
                pass
    return (1.0, 1.0, 1.0, 1.0)


def draw_text(text, x, y, size=10, color="#FFFFFF", align="left"):
    value = str(text)
    scene.tint(*color_rgba(color))
    if align == "left":
        x += len(value) * size * 0.30
    elif align == "right":
        x -= len(value) * size * 0.30
    scene.text(value, "Helvetica", size, x, y)


def draw_bar(x, y, width, height, value, max_value=0.25):
    scene.no_stroke()
    scene.fill(0.16, 0.19, 0.24, 1.0)
    scene.rect(x, y, width, height)
    frac = clamp(value / max_value if max_value else 0.0, 0.0, 1.0)
    scene.fill(0.20, 0.78, 0.70, 1.0)
    scene.rect(x, y, width * frac, height)


class SurveyScene(scene.Scene):
    def setup(self):
        self.background_color = (0.035, 0.045, 0.07)
        self.audio_started = False
        self.last_visual_event = 0.0
        start_motion_monitor()  # sensor starts; generated audio remains OFF

    def update(self):
        update_motion_trigger()
        if not self.audio_started and not STOP_EVENT.is_set():
            self.audio_started = True
            threading.Thread(
                target=audio_worker,
                daemon=True,
                name="TinManAudioWorker"
            ).start()

        with STATE_LOCK:
            # Transient HOP flash times out; handshake / pulling indicators persist
            if state["visual_cue_active"] and not (
                state.get("handshake_visual_active") or state.get("connection_pulling")
            ):
                if self.last_visual_event == 0.0:
                    self.last_visual_event = time.time()
                elif time.time() - self.last_visual_event > 1.2:
                    state["visual_cue_active"] = False
                    self.last_visual_event = 0.0
            elif state.get("handshake_visual_active") or state.get("connection_pulling"):
                # Keep a soft visual_cue so the row stays live while pulling frames
                state["visual_cue_active"] = VISUAL_CUES_ENABLED
                self.last_visual_event = 0.0

    def draw(self):
        w, h = self.size.w, self.size.h
        scene.background(0.035, 0.045, 0.07)
        sx = max(20.0, w * 0.08)
        safe_y = max(24.0, h * 0.06)
        content_w = max(1.0, w - 2 * sx)
        left = sx + 8
        inner_w = content_w - 16

        with STATE_LOCK:
            s = dict(state)
            s["bands"] = dict(state["bands"])
            s["workers"] = list(state["workers"])

        def panel(y, height, shade=(0.07, 0.10, 0.15, 1.0)):
            scene.no_stroke()
            scene.fill(*shade)
            scene.rect(sx, y, content_w, height)

        def line(text, y, size=9, color="#E8F0FF"):
            draw_text(text, left + 5, y, size, color)

        y = h - safe_y - 20
        line(APP_NAME, y, 12)
        y -= 19
        line("LOCAL AUDIO / HEARING-ACCESSIBLE CUES + NAU", y, 8, "#86D9D0")
        y -= 15

        panel(y - 66, 66, (0.055, 0.12, 0.14, 1.0))
        line("ACCESSIBLE RIDE AUDIO", y - 13, 9, "#86D9D0")
        line("Route: " + s["audio_route_status"], y - 28, 7)
        line("Cue: " + s["last_hop_reason"], y - 41, 7)
        line("Conn {} {}: {}%".format(
            s["connection_transport"],
            s["connection_device_name"][:14],
            s["connection_confidence"]), y - 53, 7, "#86D9D0")
        line(s["connection_state"][:54], y - 63, 6, "#AAB4C8")
        y -= 76

        panel(y - 72, 72)
        line("STEREO RMS / LEARNED BASELINE", y - 14, 9)
        draw_text("L {:.4f} learned {:.4f}".format(
            s["left_rms"], s["left_learned"]), left + 5, y - 33, 8)
        draw_bar(left + 5, y - 43, inner_w * 0.45, 5, s["left_rms"], 0.20)
        draw_text("R {:.4f} learned {:.4f}".format(
            s["right_rms"], s["right_learned"]), left + inner_w * 0.52, y - 33, 8)
        draw_bar(left + inner_w * 0.52, y - 43, inner_w * 0.43, 5,
                 s["right_rms"], 0.20)
        draw_text("L +{:.4f} / -{:.4f}".format(
            s["left_pos_rms"], s["left_neg_rms"]), left + 5, y - 60, 7)
        draw_text("R +{:.4f} / -{:.4f}".format(
            s["right_pos_rms"], s["right_neg_rms"]),
            left + inner_w * 0.52, y - 60, 7)
        y -= 80

        panel(y - 44, 44, (0.055, 0.08, 0.12, 1.0))
        line("MICROPHONE GATES", y - 13, 9)
        draw_text("LEFT " + ("OPEN" if s["left_gate"] else "CLOSED"),
                  left + 5, y - 31, 8,
                  "#35D6A5" if s["left_gate"] else "#AAB4C8")
        draw_text("RIGHT " + ("OPEN" if s["right_gate"] else "CLOSED"),
                  left + inner_w * 0.52, y - 31, 8,
                  "#35D6A5" if s["right_gate"] else "#AAB4C8")
        y -= 52

        panel(y - 92, 92, (0.065, 0.095, 0.13, 1.0))
        line("TIN-MAN / CONTEXT + HCP (NAU)", y - 14, 9)
        line(s["tinman_context"], y - 30, 8, "#35D6A5")
        line("Action: " + s["tinman_action"][:48], y - 44, 7)
        line("Prediction: " + s["predicted_event"][:48], y - 57, 7, "#AAB4C8")
        line("Conf {:.0f}% | NAU {:.2f} | HCP {}".format(
            s["tinman_confidence"] * 100,
            s.get("nau_influence", 0.0),
            "YES" if s.get("hcp_active") else "no"), y - 70, 7)
        line("contexts {} | packets {}".format(
            s["context_count"], s["packet_count"]), y - 83, 7)
        y -= 100

        panel(y - 94, 94)
        line("MIC DRIVE / AMPLIFIER PROCESSING", y - 14, 9)
        line("Signed prediction error: {:+.5f}".format(
            s["mic_signed_error"]), y - 31, 8)
        line("Positive envelope: {:.5f}".format(
            s["mic_positive_envelope"]), y - 46, 8)
        line("Bounded output drive: +{:.2f} dB".format(
            s["mic_drive_gain_db"]), y - 61, 8, "#86D9D0")
        draw_bar(left + 5, y - 72, inner_w - 10, 5,
                 s["mic_drive_gain_db"], MIC_DRIVE_MAX_GAIN_DB)
        line("Input RMS {:.4f} | output RMS {:.4f}".format(
            s["amplifier_input_rms"], s["amplifier_output_rms"]), y - 87, 7)
        y -= 102

        panel(y - 61, 61, (0.055, 0.075, 0.12, 1.0))
        line("COMPETE / BOUNDED EQ", y - 14, 9)
        line("Compete {:.3f} | stereo delta {:+.3f}".format(
            s["compete"], s["compete_delta"]), y - 30, 8)
        line("EQ L/M/H {:+.1f} / {:+.1f} / {:+.1f} dB".format(
            s["eq_low_db"], s["eq_mid_db"], s["eq_high_db"]),
            y - 45, 8, "#86D9D0")
        line("Reference {:.0f} Hz | local response".format(
            s["reference_tone_hz"]), y - 57, 7)
        y -= 69

        panel(y - 50, 50)
        line("F0-F16 ADAPTIVE ACOUSTIC BANDS", y - 13, 8)
        keys = [
            "F0", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8",
            "F9", "F10", "F11", "F12", "F13", "F14", "F15", "F16"
        ]
        bw = (inner_w - 10) / len(keys)
        for i, key in enumerate(keys):
            bx = left + 5 + i * bw
            draw_text(key, bx, y - 27, 6, "#86D9D0")
            draw_bar(bx, y - 39, max(2, bw - 2), 3,
                     s["bands"].get(key, 0.0), 0.06)
        y -= 57

        avatar_x = w * 0.5
        avatar_y = max(safe_y + 25, y - 18)

        # Colour language:
        #   Teal   = Background — HCP permanently available (twin)
        #   Amber  = Negotiation learning / HOP competing
        #   Green  = Streaming stable HOP (compete held)
        motion_negotiation = bool(s.get("motion_negotiation_active"))
        negotiation = bool(s.get("handshake_visual_active")) and not motion_negotiation
        streaming = bool(s.get("stream_active")) and not negotiation and not motion_negotiation
        hopping = bool(s.get("visual_cue_active"))

        amber = (1.0, 0.72, 0.15, 1.0)
        teal = (0.20, 0.78, 0.70, 1.0)
        green = (0.20, 0.90, 0.45, 1.0)
        red = (1.0, 0.12, 0.12, 1.0)

        if motion_negotiation:
            left_ear = green
            right_ear = green
        elif negotiation:
            left_ear = amber
            right_ear = amber
        elif streaming:
            left_ear = green
            right_ear = green
        else:
            left_ear = teal
            right_ear = teal

        scene.no_fill()
        scene.stroke(0.20, 0.78, 0.70, 1.0)
        scene.stroke_weight(1.5)
        scene.ellipse(avatar_x - 15, avatar_y - 10, 30, 30)  # head
        scene.no_stroke()
        scene.fill(*left_ear)
        scene.ellipse(avatar_x - 26, avatar_y + 1, 13, 15)   # left ear
        scene.fill(*right_ear)
        scene.ellipse(avatar_x + 13, avatar_y + 1, 13, 15)   # right ear
        # Eyes
        scene.fill(0.20, 0.78, 0.70, 1.0)
        scene.ellipse(avatar_x - 6, avatar_y + 1, 3, 3)
        scene.ellipse(avatar_x + 3, avatar_y + 1, 3, 3)

        # Indicator row under avatar
        ind_y = safe_y + 40
        ind_x = w * 0.5 - 8

        # HOP indicator: amber when competing (negotiation), else teal/green
        if motion_negotiation:
            scene.fill(*green)
            scene.ellipse(ind_x, ind_y - 4, 16, 16)
            draw_text("NEG GREEN / LEARNING", ind_x + 22, ind_y, 8, "#35D645")
            ind_x += 118
        elif hopping or negotiation:
            hop_color = "#FFB020" if negotiation else "#86D9D0"
            scene.fill(*(amber if negotiation else teal))
            scene.ellipse(ind_x, ind_y - 4, 16, 16)
            draw_text("HOP", ind_x + 22, ind_y, 9, hop_color)
            ind_x += 48

        if streaming:
            draw_text("STREAM", ind_x + 8, ind_y, 9, "#35D645")
            ind_x += 52
        elif negotiation:
            draw_text("NEG", ind_x + 8, ind_y, 9, "#FFB020")
            ind_x += 36

        # HCP always available (twin) — teal label in background
        draw_text("HCP", ind_x + 8, ind_y, 9, "#86D9D0")

        # Compact, explicit state diagnostics (measured values vs simulation).
        diag_y = safe_y + 54
        draw_text("MODE {}{} | HOP {} | FM {}".format(
            s.get("consumer_mode", "BLACK"), " TRAIN" if s.get("training_mode") else "",
            s.get("hop_state", "IDLE"), "ON" if s.get("fm_test_active") else "OFF"),
            left, diag_y, 7, "#E8F0FF")
        draw_text("RESONANCE {:.0f}Hz estimate | PRIVACY SIM {:.2f} (not verified)".format(
            s.get("resonance_peak_hz", 0.0), s.get("privacy_simulation_score", 0.0)),
            left, diag_y + 10, 6, "#AAB4C8")
        draw_text("ENTROPY {} measured {:.4f} / simulated {:.4f} | LOCAL ONLY".format(
            "ACTIVE" if s.get("entropy_active") else "STANDBY",
            s.get("entropy_measured", 0.0), s.get("entropy_simulated", 0.0)),
            left, diag_y + 19, 6, "#AAB4C8")
        draw_text("GEN AUDIO: {} | VOL {:.2f} | MIC MAY INCLUDE PLAYBACK LEAKAGE".format(
            s.get("generated_audio_mode", "OFF"), s.get("generated_audio_volume", GENERATED_AUDIO_PLAYER_VOLUME)),
            left, diag_y + 28, 6, "#F0C878")
        draw_text("INTEGRITY {} | OPS {} | ε +{:.1e}".format(
            s.get("integrity_status", "ARMED / FIRST CHECK PENDING"),
            s.get("integrity_operation_count", 0),
            s.get("integrity_epsilon_total", 0.0)), left, safe_y + 48, 6, "#AAB4C8")
        draw_text("MOTION {} | THREAT {:.2f} | D STIMULUS: ALL SCORES".format(
            s.get("motion_trigger", "OFF"), s.get("motion_threat", 0.0)),
            left, diag_y + 37, 6, "#FFCA55")
        draw_text("STEREO D {} | Lx{:.2f} Rx{:.2f} | OPP JITTER SOUND {}".format(
            "ON" if s.get("stereo_d_active") else "OFF",
            s.get("stereo_d_left_multiplier", 1.0),
            s.get("stereo_d_right_multiplier", 1.0),
            "ON" if s.get("opposite_jitter_active") else "OFF"),
            left, diag_y + 46, 6, "#86D9D0")

        # Floating lower-screen scope mirrors the attached Motion Tracker:
        # heading sweep line, 3-second single-location blips, centre blip for D/high threat,
        # directional blips on delta > 2 and threat > 3 (0.5 s cooldown).
        # Scope rendering is independent of B/D audio mode; the same sensor sample may feed both subsystems, but scope labels/bearing never switch audio modes.
        if s.get("motion_scope_visible", True):
            scope_radius = min(48.0, max(30.0, min(w, h) * 0.105))
            scope_x = w - sx - scope_radius - 8.0
            scope_y = safe_y + scope_radius + 12.0
            heading = math.radians(float(s.get("motion_heading_deg", 0.0)))
            threat = float(s.get("motion_threat", 0.0))
            delta = float(s.get("motion_delta", 0.0))
            strength = float(s.get("motion_strength", 0.0))
            trigger = s.get("motion_trigger", "OFF")

            # Radar rings and crosshair.
            scene.no_fill()
            scene.stroke(0.20, 0.78, 0.70, 0.88)
            scene.stroke_weight(1.4)
            scene.ellipse(scope_x - scope_radius, scope_y - scope_radius,
                          scope_radius * 2.0, scope_radius * 2.0)
            scene.stroke(0.20, 0.78, 0.70, 0.50)
            scene.ellipse(scope_x - scope_radius * 0.56, scope_y - scope_radius * 0.56,
                          scope_radius * 1.12, scope_radius * 1.12)
            scene.line(scope_x - scope_radius * 0.9, scope_y,
                       scope_x + scope_radius * 0.9, scope_y)
            scene.line(scope_x, scope_y - scope_radius * 0.9,
                       scope_x, scope_y + scope_radius * 0.9)

            # Rotating heading line: same heading derived from atan2(y, x).
            sweep_x = scope_x + math.sin(heading) * scope_radius * 0.92
            sweep_y = scope_y + math.cos(heading) * scope_radius * 0.92
            scene.stroke(0.25, 1.0, 0.40, 0.95)
            scene.stroke_weight(2.0)
            scene.line(scope_x, scope_y, sweep_x, sweep_y)

            # Draw one marker per detected event at its original detected bearing.
            live_blips = []
            for blip in s.get("motion_blips", []):
                remaining = float(blip.get("expires", 0.0)) - time.monotonic()
                if remaining <= 0.0:
                    continue
                live_blips.append(blip)
                alpha = min(1.0, 0.95 * remaining / 3.0)
                a = math.radians(float(blip.get("heading", 0.0)))
                radius = scope_radius * 0.80
                # Use the same screen-space convention as the supplied scope:
                # x = centre + r*cos(angle), y = centre + r*sin(angle).
                # Pythonista scene coordinates increase upward, so invert y.
                bx = scope_x + radius * math.cos(a)
                by = scope_y - radius * math.sin(a)
                scene.no_stroke()
                if blip.get("kind") == "center":
                    # Restore the supplied tracker: HEAD IMPACT centre marker.
                    # This is a threat proxy, not a verified impact location.
                    scene.fill(1.0, 0.12, 0.12, alpha)
                    scene.ellipse(scope_x - 6.0, scope_y - 6.0, 12.0, 12.0)
                else:
                    # Restore original scope rendering: every directional
                    # detection uses one cyan/white marker at its detected bearing.
                    scene.fill(0.12, 0.88, 1.0, alpha)
                    scene.ellipse(bx - 8.0, by - 8.0, 16.0, 16.0)
                    scene.fill(1.0, 1.0, 1.0, alpha)
                    scene.ellipse(bx - 3.0, by - 3.0, 6.0, 6.0)
            # Opposite-bearing status is audible only. Do not draw a second
            # visual marker at the antipodal bearing.

            # Drop expired markers from shared state without changing detection.
            if len(live_blips) != len(s.get("motion_blips", [])):
                with STATE_LOCK:
                    state["motion_blips"] = live_blips

            # Scope display is independent of B/D audio-mode state. A centre
            # marker appears only when the original tracker creates a centre
            # blip event; no B/D state overlay is drawn on the scope itself.
            # Title reports the latest live blip's bearing relative to the
            # current scope heading, normalized to [-180, +180] degrees.
            latest_directional = next(
                (b for b in reversed(live_blips) if b.get("kind") == "directional"),
                None)
            latest_center = next(
                (b for b in reversed(live_blips) if b.get("kind") == "center"),
                None)
            if latest_directional is not None:
                heading_now = float(s.get("motion_heading_deg", 0.0))
                blip_bearing = float(latest_directional.get("heading", 0.0)) % 360.0
                relative_bearing = ((blip_bearing - heading_now + 180.0) % 360.0) - 180.0
                bearing_title = "BLIP BEARING {:+.0f}° FROM HEADING".format(relative_bearing)
                bearing_detail = "HDG {:.0f}° | BLIP {:.0f}° | REL {:+.0f}°".format(
                    heading_now, blip_bearing, relative_bearing)
            elif latest_center is not None:
                bearing_title = "HEAD IMPACT | CENTRE MARKER"
                bearing_detail = "HDG {:.0f}° | HEAD IMPACT EVENT".format(
                    float(s.get("motion_heading_deg", 0.0)))
            else:
                bearing_title = "WAVE DETECTED"
                bearing_detail = "HDG {:.0f}° | MOVE -- | PROXY --".format(
                    float(s.get("motion_heading_deg", 0.0)))
            draw_text(bearing_title, scope_x, scope_y + scope_radius + 8.0,
                      6, "#86D9D0", align="center")
            draw_text(bearing_detail,
                scope_x, scope_y - scope_radius - 10.0, 5, "#AAB4C8", align="center")
            draw_text("FIELD {:.1f} μT | Δ {:.2f}".format(strength, delta),
                scope_x, scope_y - scope_radius - 20.0, 5, "#AAB4C8", align="center")


        footer = s["stream_profile"] + " | " + s["status"]
        if s["error"]:
            footer = "ERROR: " + str(s["error"])
        draw_text(footer[:70], left, safe_y + 6, 6, "#AAB4C8")
        draw_text("SCOPE: CYAN/WHITE=DIRECTIONAL BLIP / RED=HEAD IMPACT", left, safe_y + 30, 6, "#AAB4C8")
        draw_text("Middle strip: left volume - / right volume +; upper half stops.", left, safe_y + 17, 5, "#AAB4C8")

    def touch_began(self, touch):
        # Separate lower-screen controls: mode cycle, FM, background test, and
        # synthetic speech-like test. Upper half stops the app and any stream.
        w, h = self.size.w, self.size.h
        y = touch.location.y
        if y < max(70.0, h * 0.16):
            with STATE_LOCK:
                modes = ["BLACK", "RED", "AMBER", "GREEN"]
                current = state.get("consumer_mode", "BLACK")
                old_mode = current
                state["consumer_mode"] = modes[(modes.index(current) + 1) % len(modes)]
                new_mode = state["consumer_mode"]
                state["training_mode"] = new_mode in ("AMBER", "GREEN")
                state["message"] = "Consumer wheel mode: {}{}".format(
                    new_mode, " training" if state["training_mode"] else "")
                motion_active = state.get("motion_trigger") in ("B", "D")
                if new_mode == "AMBER":
                    state["amber_background_active"] = True
                elif old_mode == "AMBER":
                    state["amber_background_active"] = False
            if new_mode == "AMBER" and not motion_active:
                # Rebuild the finite ambient WAV in AMBER context so the 35%
                # amplitude increase is applied even if background audio was
                # already running as a manual test.
                stop_generated_audio_stream()
                set_generated_audio_mode("BACKGROUND")
                log("AMBER selected: background stimulus amplitude increased by 35% (software level; not calibrated SPL).")
            elif old_mode == "AMBER" and not motion_active:
                with STATE_LOCK:
                    audio_mode = state.get("generated_audio_mode", "OFF")
                if audio_mode == "BACKGROUND":
                    stop_generated_audio_stream()
                log("AMBER deselected: AMBER-specific background boost disabled.")
            log("Consumer wheel mode changed: {}".format(new_mode))
            return
        if y < h * 0.25:
            with STATE_LOCK:
                next_fm = not state.get("fm_test_active", False)
            set_fm_test(next_fm)
            return
        if y < h * 0.34:
            set_generated_audio_mode("BACKGROUND")
            return
        if y < h * 0.43:
            set_generated_audio_mode("SPEECHLIKE")
            return
        if y < h * 0.50:
            adjust_generated_audio_volume(-0.05 if touch.location.x < w * 0.5 else 0.05)
            return
        STOP_EVENT.set()
        stop_generated_audio_stream()
        stop_motion_monitor()
        with STATE_LOCK:
            state["running"] = False
            state["status"] = "Stopping"
            state["hop_state"] = "STOPPED"
            state["background_management"] = "STOPPED / GENERATED AUDIO OFF"
            state["message"] = "Stop requested by screen tap"
        threading.Thread(target=play_indication_tone, args=(False,), daemon=True,
                         name="SunbeamStopTone").start()
        log("Stop requested by screen tap.")


def main():
    try:
        os.makedirs(DOCS, exist_ok=True)
    except Exception:
        pass

    log("=" * 58)
    log("Starting " + APP_NAME)
    log("Mode: LOCAL AUDIO PROTOTYPE + NAU on HOP/HCP")
    log("Pickup timing signatures registered for learning: {} seconds; per-mic/channel classification is metadata only in this version.".format(
        PICKUP_CAPTURE_SIGNATURES_SECONDS))
    log("HOP indicator sound enabled for {:.2f}s; digital gain {:.2f} (not calibrated SPL).".format(
        HOP_INDICATOR_SECONDS, HOP_INDICATOR_GAIN))
    log("Standard auditory-hop cues remain available; digital peak capped at {:.2f}.".format(
        HOP_MAX_PEAK))
    log("NAU spectral-temporal: enabled={} depth={:.1f}Hz rate={:.1f}Hz spread={:.1f}Hz".format(
        NAU_SPECTRAL_TEMPORAL_ENABLED, NAU_TEMPORAL_DEPTH_HZ,
        NAU_TEMPORAL_RATE_HZ, NAU_HOP_SPREAD_HZ))
    log("NAU → HOP trigger={} | HCP detection={} | hop tones={}".format(
        NAU_HOP_TRIGGER_ENABLED, NAU_HCP_DETECTION_ENABLED, NAU_HOP_FREQUENCY_APPLY))
    log("Hearing-device route is system-managed and is NOT verified by this script.")
    log("Auracast / hearing-loop broadcasting requires separate compatible hardware.")
    log("F0-F16 are acoustic analysis bands; no IR sensing is performed.")
    log("Connection confidence is protocol-check progress, not microphone loudness.")
    log("BLE/BTT adapter must call report_connection_request() on a real request.")
    log("Adapter must report identity/read/write/handshake outcomes via report_connection_check().")
    log("NAU rule: delta-only; no time(), elapsed time, theta, or hop index in NAU influence.")
    log("Privacy, negative-field, and MSSA labels are local software simulations only.")
    log("Chunk-based processing; not a live low-latency amplifier or safety system.")
    log("Generated background/speech-like streams: OFF at launch; B selects background; D selects speech-like; AMBER boosts background amplitude by 35%.")
    log("Tracker threat formula: min(max((field_strength / 20) + (delta * 8), 0), 10); D stimulus enabled at ALL scores; movement label >= {:.1f}, HEAD IMPACT label >= {:.1f}. D is not a validated impact detector.".format(
        MOTION_MOVEMENT_THRESHOLD, MOTION_HIGH_THREAT_THRESHOLD))
    integrity_tick('startup')
    log("Integrity guard: lock-protected SHA-256 operation chain; epsilon advances by {:.1e} per guarded operation. Tamper-evident, not tamper-proof.".format(INTEGRITY_EPSILON))
    log("Motion D stimulus is enabled at all threat scores; GREEN learning, entropy and stereo-D are local software states, not verified beamforming or impact detection.")
    log("Location/GPS is not imported or accessed; the supplied location display is intentionally omitted to preserve the project's no-location constraint.")
    scene.run(SurveyScene(), show_fps=False)


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# REMOTE BLE/BTT ADAPTER INTEGRATION CONTRACT
# ---------------------------------------------------------------------------
# Call these functions from the actual adapter when protocol events occur:
#
#   report_connection_request("BLE", discovered_device_name or "NoName")
#   report_connection_check("identity", identity_ok, "device identity result")
#   report_connection_check("read", read_supported, "read capability result")
#   report_connection_check("write", write_supported, "write capability result")
#   report_connection_check("handshake", handshake_response_verified,
#                           "verified response details")
#
# Do not call report_connection_request merely because a device was discovered.
# A real incoming connection/request event must be supplied by the adapter.
# This script does not itself implement BLE scanning or BTT protocol access.
