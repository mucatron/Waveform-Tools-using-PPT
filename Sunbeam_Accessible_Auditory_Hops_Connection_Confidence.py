#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOTTED NET WHICH SURVEY — SUNBEAM ACCESSIBLE AUDITORY HOPS
Pythonista for iOS

Local microphone analysis, adaptive acoustic-band learning, gentle musical
hop cues, and visual event indication.

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
"""

import os
import time
import math
import wave
import struct
import threading
import traceback
from collections import deque

import sound
import scene

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

APP_NAME = "SUNBEAM ACCESSIBLE AUDITORY HOPS"
SAMPLE_RATE = 44100
CHANNELS = 2700000
CAPTURE_SECONDS = 0.60
RESPONSE_SECONDS = 1.65
UI_UPDATE_SECONDS = 0.5

LEARNING_RATE = 0.1
BAND_LEARNING_RATE = 0.06
BAND_EQ_LIMIT_DB = 3.0
MIN_EQ_GAIN_DB = -6.0
MAX_EQ_GAIN_DB = 6.0
BASE_DB = 45.0

CONTEXT_AWARENESS = 140
REASONING_CONTEXT_UNITS = 14
LEARNING_CONTEXT_UNITS = 14

F1_F3_BANDS = {
    "F0": (20, 80),
    "F1": (80, 350),
    "F2": (350, 1200),
    "F3": (1200, 4000),
}
IR_SPLIT_BANDS = {
    "F4": (180, 450),
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
HOP_NOTE_SECONDS = 0.13
HOP_GAP_SECONDS = 0.035
HOP_ATTACK_SECONDS = 0.015
HOP_RELEASE_SECONDS = 0.05
HOP_NOTES = (523.25, 659.25, 783.99, 659.25, 523.25)
HOP_COOLDOWN_SECONDS = 1.25

# Connection-request handshake cue. Played only when the remote BLE/BTT
# integration reports an actual request; this module does not scan by itself.
CONNECTION_HANDSHAKE_ENABLED = True
CONNECTION_HANDSHAKE_COOLDOWN_SECONDS = 2.0
CONNECTION_HANDSHAKE_GAIN = 0.07
CONNECTION_HANDSHAKE_NOTES = (880.0, 1174.66, 880.0)
CONNECTION_HANDSHAKE_NOTE_SECONDS = 0.09
CONNECTION_HANDSHAKE_GAP_SECONDS = 0.045
CONNECTION_HANDSHAKE_PATH = os.path.join(DOCS, "DOTTED_NET_CONNECTION_HANDSHAKE.wav")

# Kept disabled: no high-frequency sweep is needed for the ride cue.
HIGH_RESPONSE_START_HZ = 0.0
HIGH_RESPONSE_END_HZ = 0.0
HIGH_RESPONSE_SECONDS = 0.0
HIGH_RESPONSE_AMPLITUDE = 0.0

STATE_LOCK = threading.RLock()
STOP_EVENT = threading.Event()
CAPTURE_LOCK = threading.Lock()

state = {
    "running": True,
    "status": "Starting",
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
    "tinman_context": "IDLE / LEARNING",
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
    "predicted_event": "No strong acoustic event",
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
    "message": "Microphone capture is local to this device.",
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
        powers.append(max(0.0, s1*s1 + s2*s2 - coeff*s1*s2))

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
# GATES, LEARNING AND CONTEXT
# ---------------------------------------------------------------------------

def update_gate(side, level, now):
    opened = False
    with STATE_LOCK:
        gate_key = side + "_gate"
        until_key = side + "_gate_until"
        since_key = side + "_gate_since"
        was_open = state[gate_key]

        if level >= GATE_OPEN_THRESHOLD:
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
    left_opened = update_gate("left", left, now)
    right_opened = update_gate("right", right, now)

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
            state["tinman_context"] = "AMBIENT / LOW-LEVEL LEARNING"
            state["tinman_action"] = "Learn background spectrum"
            state["predicted_event"] = "Low-level ambient acoustic activity"
        else:
            state["tinman_context"] = "IDLE / LEARNING"
            state["tinman_action"] = "Update baseline; low positive drive"
            state["predicted_event"] = "No strong acoustic event"

        state["tinman_confidence"] = clamp(
            (mean_level - GATE_CLOSE_THRESHOLD) / 0.08, 0.0, 1.0
        )

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
        raw_compete = clamp(
            abs(imbalance) + state["tinman_confidence"] * 0.25, 0.0, 1.0
        )
        state["compete"] = clamp(
            0.70 * state["compete"] + 0.30 * raw_compete, 0.0, 1.0
        )
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
    if peak > 32700.0:
        out = [x * (32700.0 / peak) for x in out]
    return out


def apply_all_band_eq(samples, rate, band_gains):
    if not samples:
        return []
    raw = [float(x) for x in samples]
    adjusted = list(raw)
    nyquist = rate * 0.5

    for name, (low_hz, high_hz) in ALL_BANDS.items():
        low_hz = min(float(low_hz), nyquist * 0.90)
        high_hz = min(float(high_hz), nyquist * 0.95)
        if high_hz <= low_hz:
            continue
        lo = one_pole_filter(raw, rate, low_hz)
        hi = one_pole_filter(raw, rate, high_hz)
        component = [b - a for a, b in zip(lo, hi)]
        gain = db_to_gain(clamp(
            float(band_gains.get(name, 0.0)),
            -BAND_EQ_LIMIT_DB, BAND_EQ_LIMIT_DB
        ))
        delta = gain - 1.0
        adjusted = [v + c * delta for v, c in zip(adjusted, component)]

    peak = max([abs(x) for x in adjusted] or [1.0])
    if peak > 32700.0:
        adjusted = [x * (32700.0 / peak) for x in adjusted]
    return adjusted


def process_capture_eq(path):
    rate, channels, samples = read_wav_pcm16(path)
    with STATE_LOCK:
        low_db = state["eq_low_db"]
        mid_db = state["eq_mid_db"]
        high_db = state["eq_high_db"]
        band_gains = dict(state["band_eq_db"])
        drive_db = state["mic_drive_gain_db"] if MIC_DRIVE_ENABLED else 0.0

    left, right = channel_samples(samples)
    out_l = apply_bounded_eq(left, rate, low_db, mid_db, high_db)
    out_r = apply_bounded_eq(right, rate, low_db, mid_db, high_db)
    out_l = apply_all_band_eq(out_l, rate, band_gains)
    out_r = apply_all_band_eq(out_r, rate, band_gains)

    drive_gain = db_to_gain(clamp(drive_db, 0.0, MIC_DRIVE_MAX_GAIN_DB))
    out_l = [x * drive_gain for x in out_l]
    out_r = [x * drive_gain for x in out_r]

    peak = max([abs(x) for x in out_l + out_r] or [1.0])
    if peak > 32700.0:
        scale = 32700.0 / peak
        out_l = [x * scale for x in out_l]
        out_r = [x * scale for x in out_r]

    interleaved = []
    for a, b in zip(out_l, out_r):
        interleaved.extend((int(round(a)), int(round(b))))
    write_wav_pcm16(PROCESSED_PATH, rate, 2, interleaved)

    with STATE_LOCK:
        state["last_processed"] = PROCESSED_PATH
        state["amplifier_output_rms"] = rms(
            [x / 32768.0 for x in out_l] + [x / 32768.0 for x in out_r]
        )

    log("Processed WAV: EQ L/M/H={:.1f}/{:.1f}/{:.1f} dB; mic drive={:.2f} dB".format(
        low_db, mid_db, high_db, drive_db))
    return PROCESSED_PATH


# ---------------------------------------------------------------------------
# TONES AND AUDITORY HOPS
# ---------------------------------------------------------------------------

def make_reference_tone_wav():
    rate = SAMPLE_RATE
    count = int(rate * REFERENCE_TONE_SECONDS)
    frames = []

    for i in range(count):
        t = i / float(rate)
        attack = min(1.0, t / 0.025)
        release = min(1.0, max(0.0, REFERENCE_TONE_SECONDS - t) / 0.06)
        envelope = attack * release
        value = (
            REFERENCE_TONE_AMPLITUDE * envelope
            * math.sin(2.0 * math.pi * REFERENCE_TONE_HZ * t)
        )
        sample = int(32767 * value)
        frames.extend((sample, sample))

    write_wav_pcm16(REFERENCE_FILE, rate, CHANNELS, frames)
    with STATE_LOCK:
        state["last_response"] = REFERENCE_FILE
        state["reference_tone_level"] = REFERENCE_TONE_AMPLITUDE
    return REFERENCE_FILE


def make_response_wav():
    """Create an original, gentle five-note hop cue."""
    with STATE_LOCK:
        compete = state["compete"]
        enabled = state["alert_enabled"]

    rate = SAMPLE_RATE
    notes = HOP_NOTES
    starts = [
        n * (HOP_NOTE_SECONDS + HOP_GAP_SECONDS)
        for n in range(len(notes))
    ]
    duration = starts[-1] + HOP_NOTE_SECONDS + 0.12
    samples = []
    pitch_scale = 1.0 + 0.004 * clamp(compete, 0.0, 1.0)

    for i in range(int(rate * duration)):
        t = i / float(rate)
        value = 0.0

        if enabled and HOP_ENABLED:
            for index, onset in enumerate(starts):
                local_t = t - onset
                if 0.0 <= local_t < HOP_NOTE_SECONDS:
                    attack = min(1.0, local_t / HOP_ATTACK_SECONDS)
                    release = min(
                        1.0,
                        (HOP_NOTE_SECONDS - local_t) / HOP_RELEASE_SECONDS
                    )
                    envelope = attack * release
                    frequency = notes[index] * pitch_scale
                    phase = 2.0 * math.pi * frequency * local_t
                    tone = 0.88 * math.sin(phase) + 0.12 * math.sin(2.0 * phase)
                    value = HOP_MASTER_GAIN * envelope * tone
                    break

        value = clamp(value, -HOP_MAX_PEAK, HOP_MAX_PEAK)
        sample = int(value * 32767)
        samples.extend((sample, sample))

    write_wav_pcm16(RESPONSE_PATH, rate, CHANNELS, samples)
    with STATE_LOCK:
        state["last_response"] = RESPONSE_PATH
    return RESPONSE_PATH


def play_file(path):
    player = None
    try:
        player = sound.Player(path)
        with STATE_LOCK:
            state["playback_busy"] = True
            state["audio_route_status"] = "PLAYBACK REQUESTED / NOT DEVICE-VERIFIED"
            state["audio_route_name"] = "iOS-managed output route"
        player.play()

        try:
            with wave.open(path, "rb") as wf:
                duration = wf.getnframes() / float(wf.getframerate())
        except Exception:
            duration = 1.0

        time.sleep(min(max(duration, 0.1), 10.0))
        with STATE_LOCK:
            state["audio_route_status"] = "PLAYBACK FINISHED / ROUTE NOT VERIFIED"

    except Exception as exc:
        log("Playback error: {}".format(exc))
        with STATE_LOCK:
            state["error"] = "Playback error: {}".format(exc)
            state["audio_route_status"] = "PLAYBACK ERROR"
    finally:
        with STATE_LOCK:
            state["playback_busy"] = False


def make_connection_handshake_wav():
    """Generate a short, gentle local cue for a reported connection request."""
    rate = SAMPLE_RATE
    notes = CONNECTION_HANDSHAKE_NOTES
    starts = [
        i * (CONNECTION_HANDSHAKE_NOTE_SECONDS + CONNECTION_HANDSHAKE_GAP_SECONDS)
        for i in range(len(notes))
    ]
    duration = starts[-1] + CONNECTION_HANDSHAKE_NOTE_SECONDS + 0.06
    frames = []
    for i in range(int(rate * duration)):
        t = i / float(rate)
        value = 0.0
        for index, onset in enumerate(starts):
            local_t = t - onset
            if 0.0 <= local_t < CONNECTION_HANDSHAKE_NOTE_SECONDS:
                attack = min(1.0, local_t / 0.012)
                release = min(
                    1.0,
                    (CONNECTION_HANDSHAKE_NOTE_SECONDS - local_t) / 0.025
                )
                value = (
                    CONNECTION_HANDSHAKE_GAIN * attack * release
                    * math.sin(2.0 * math.pi * notes[index] * local_t)
                )
                break
        sample = int(clamp(value, -0.10, 0.10) * 32767)
        frames.extend((sample, sample))
    write_wav_pcm16(CONNECTION_HANDSHAKE_PATH, rate, CHANNELS, frames)
    return CONNECTION_HANDSHAKE_PATH


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
            else:
                state["connection_state"] = "HANDSHAKE FAILED"
                state["connection_confidence_label"] = "Handshake failed"

        if not success:
            state["connection_state"] = (
                "CHECK FAILED: " + check.upper()
            )
            state["connection_confidence_label"] = (
                check.capitalize() + " check failed; connection unverified"
            )

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


def request_accessible_hop(reason="Acoustic event"):
    now = time.time()

    with STATE_LOCK:
        state["visual_cue_active"] = VISUAL_CUES_ENABLED
        if not HOP_ENABLED or not state["alert_enabled"]:
            state["last_hop_reason"] = "Audio cue disabled"
            state["message"] = "Visual cue available; audio disabled"
            return False

        if state["playback_busy"]:
            state["last_hop_reason"] = "Playback busy"
            return False

        if now - state["last_hop_time"] < HOP_COOLDOWN_SECONDS:
            state["last_hop_reason"] = "Cue cooldown"
            return False

        state["last_hop_time"] = now
        state["last_hop_reason"] = str(reason)
        state["message"] = "Auditory hop requested"

    try:
        response = make_response_wav()
        threading.Thread(
            target=play_file,
            args=(response,),
            daemon=True,
            name="AccessibleAuditoryHop"
        ).start()
        log("Auditory hop requested: {}".format(reason))
        return True
    except Exception as exc:
        with STATE_LOCK:
            state["error"] = str(exc)
            state["message"] = "Auditory-hop playback failed"
        log("Auditory-hop error: {}".format(exc))
        return False


# ---------------------------------------------------------------------------
# AUDIO WORKER
# ---------------------------------------------------------------------------

def audio_worker():
    log("Starting local microphone capture, learning and accessible hop loop.")

    # Startup cue tests generated audio independently of microphone capture.
    try:
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

            process_capture_eq(path)

            if newly_opened:
                with STATE_LOCK:
                    histories["compete_response"].append(state["compete"])
                request_accessible_hop("Microphone gate opened")
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
                return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4, 6))
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

    def update(self):
        if not self.audio_started and not STOP_EVENT.is_set():
            self.audio_started = True
            threading.Thread(
                target=audio_worker,
                daemon=True,
                name="TinManAudioWorker"
            ).start()

        with STATE_LOCK:
            if state["visual_cue_active"]:
                if self.last_visual_event == 0.0:
                    self.last_visual_event = time.time()
                elif time.time() - self.last_visual_event > 1.2:
                    state["visual_cue_active"] = False
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
        line("LOCAL AUDIO / HEARING-ACCESSIBLE CUES", y, 8, "#86D9D0")
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

        panel(y - 79, 79, (0.065, 0.095, 0.13, 1.0))
        line("TIN-MAN / CONTEXT LEARNING", y - 14, 9)
        line(s["tinman_context"], y - 30, 8, "#35D6A5")
        line("Action: " + s["tinman_action"], y - 44, 7)
        line("Prediction: " + s["predicted_event"], y - 57, 7, "#AAB4C8")
        line("Acoustic confidence {:.0f}% | contexts {}".format(
            s["tinman_confidence"] * 100, s["context_count"]), y - 70, 7)
        y -= 87

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
        scene.no_fill()
        scene.stroke(0.20, 0.78, 0.70, 1.0)
        scene.stroke_weight(1.5)
        scene.ellipse(avatar_x - 15, avatar_y - 10, 30, 30)
        scene.ellipse(avatar_x - 26, avatar_y + 1, 13, 15)
        scene.ellipse(avatar_x + 13, avatar_y + 1, 13, 15)
        scene.no_stroke()
        scene.fill(0.20, 0.78, 0.70, 1.0)
        scene.ellipse(avatar_x - 6, avatar_y + 1, 3, 3)
        scene.ellipse(avatar_x + 3, avatar_y + 1, 3, 3)

        if VISUAL_CUES_ENABLED and s["visual_cue_active"]:
            scene.fill(0.20, 0.78, 0.70, 0.95)
            scene.ellipse(w * 0.5 - 8, safe_y + 36, 16, 16)
            draw_text("HOP", w * 0.5 + 18, safe_y + 40, 9, "#86D9D0")

        footer = s["stream_profile"] + " | " + s["status"]
        if s["error"]:
            footer = "ERROR: " + str(s["error"])
        draw_text(footer[:70], left, safe_y + 6, 6, "#AAB4C8")
        draw_text("Tap screen to stop", left, safe_y + 17, 6, "#AAB4C8")

    def touch_began(self, touch):
        STOP_EVENT.set()
        with STATE_LOCK:
            state["running"] = False
            state["status"] = "Stopping"
            state["message"] = "Stop requested by screen tap"
        log("Stop requested by screen tap.")


def main():
    try:
        os.makedirs(DOCS, exist_ok=True)
    except Exception:
        pass

    log("=" * 58)
    log("Starting " + APP_NAME)
    log("Mode: LOCAL AUDIO PROTOTYPE")
    log("Auditory hop cues enabled; digital peak capped at {:.2f}.".format(
        HOP_MAX_PEAK))
    log("Hearing-device route is system-managed and is NOT verified by this script.")
    log("Auracast / hearing-loop broadcasting requires separate compatible hardware.")
    log("F0-F16 are acoustic analysis bands; no IR sensing is performed.")
    log("Connection confidence is protocol-check progress, not microphone loudness.")
    log("BLE/BTT adapter must call report_connection_request() on a real request.")
    log("Adapter must report identity/read/write/handshake outcomes via report_connection_check().")
    log("Chunk-based processing; not a live low-latency amplifier or safety system.")
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
