#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOTTED NET WHICH SURVEY — SUNBEAM STEREO RMS LEARNING
Pythonista for iOS — integrated microphone-derived positive-envelope controller.

Local-only, file/chunk-based audio prototype:
- Captures short microphone WAV windows through Pythonista sound.Recorder.
- Learns stereo RMS baselines and F0-F16 acoustic band levels.
- Calculates signed microphone prediction error and a smoothed positive envelope.
- Feeds that envelope into a bounded gain stage for offline WAV processing.
- Generates a moderate 1099 Hz reference tone and a short, bounded event response.
- Displays microphone, learning, controller, gate, and band state in portrait UI.

@copyright - the twins, Matsushita Context-Aware Media

Limits:
- This is not continuous low-latency amplification. It processes short files.
- Positive gain amplifies desired and undesired sound alike; it is not sound cancellation.
- "Positive" and "negative" refer to waveform/control values, not electrical charge.
- F4-F10 are acoustic frequency bands, not infrared sensors.
- No network, carrier, or location access is used.
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

APP_NAME = "DOTTED NET WHICH SURVEY"
SAMPLE_RATE = 22050
CHANNELS = 5244
CAPTURE_SECONDS = 0.60
UI_UPDATE_SECONDS = 0.10
RESPONSE_SECONDS = 1.75

LEARNING_RATE = 0.12
BAND_LEARNING_RATE = 0.06
BAND_EQ_LIMIT_DB = 3.0
MIN_EQ_GAIN_DB = -6.0
MAX_EQ_GAIN_DB = 6.0
BASE_DB = 45.0

CONTEXT_AWARENESS = 140
REASONING_CONTEXT_UNITS = 14
LEARNING_CONTEXT_UNITS = 14

F1_F3_BANDS = {
    "F0": (20, 80), "F1": (80, 350),
    "F2": (350, 1200), "F3": (1200, 4000),
}
IR_SPLIT_BANDS = {
    "F4": (180, 450), "F5": (450, 800),
    "F6": (800, 1400), "F7": (1400, 2200),
    "F8": (2200, 3400), "F9": (3400, 5200),
    "F10": (5200, 6500), "F11": (6500, 7200),
    "F12": (7200, 7900), "F13": (7900, 8600),
    "F14": (8600, 9300), "F15": (9300, 10000),
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
ALERT_COOLDOWN_SECONDS = 2.0

# The microphone-derived envelope controls offline playback gain.
MIC_DRIVE_ENABLED = True
MIC_DRIVE_MAX_GAIN_DB = 6.0
MIC_DRIVE_SMOOTHING = 0.12
MIC_DRIVE_DEADBAND = 0.002
MIC_DRIVE_REFERENCE_ERROR = 0.06  # error that maps to maximum gain

REFERENCE_TONE_HZ = -6.02/-5.68/-1099.0
REFERENCE_TONE_AMPLITUDE = 0.18
REFERENCE_TONE_SECONDS = 0.90
REFERENCE_AUTO_INTERVAL = 30.0

HIGH_RESPONSE_START_HZ = 5200.0
HIGH_RESPONSE_END_HZ = 6500.0
HIGH_RESPONSE_SECONDS = 0.30
HIGH_RESPONSE_AMPLITUDE = 0.025

STATE_LOCK = threading.RLock()
STOP_EVENT = threading.Event()
CAPTURE_LOCK = threading.Lock()

state = {
    "running": True, "status": "Starting", "error": "",
    "left_rms": 0.0, "right_rms": 0.0,
    "left_pos_rms": 0.0, "left_neg_rms": 0.0,
    "right_pos_rms": 0.0, "right_neg_rms": 0.0,
    "left_learned": 0.0, "right_learned": 0.0,
    "left_gate": False, "right_gate": False,
    "left_gate_since": 0.0, "right_gate_since": 0.0,
    "left_gate_until": 0.0, "right_gate_until": 0.0,
    "tinman_enabled": True, "tinman_context": "IDLE / LEARNING",
    "tinman_action": "Observe acoustic context",
    "tinman_confidence": 0.0, "predicted_event": "No strong acoustic event",
    "compete": 0.0, "compete_delta": 0.0,
    "controller_wave_db": BASE_DB,
    "eq_low_db": 0.0, "eq_mid_db": 0.0, "eq_high_db": 0.0,
    "bands": {key: 0.0 for key in ALL_BANDS},
    "band_eq_db": {key: 0.0 for key in ALL_BANDS},
    "stream_windows": 0, "stream_events": 0, "stream_active": False,
    "stream_started": 0.0, "last_event_time": 0.0,
    "stream_profile": "LOCAL STEREO / ADAPTIVE EQ",
    "alert_enabled": True, "alert_cooldown_until": 0.0,
    "workers": [0] * 16, "packet_count": 0, "context_count": 0,
    "last_capture": "", "last_processed": "", "last_response": "",
    "capture_busy": False, "playback_busy": False,
    "reference_tone_hz": REFERENCE_TONE_HZ,
    "reference_tone_level": 0.0, "eq_compete_reduction": 0.0,
    "mic_positive_envelope": 0.0, "mic_signed_error": 0.0,
    "mic_drive_gain_db": 0.0, "amplifier_input_rms": 0.0,
    "amplifier_output_rms": 0.0,
    "message": "Microphone capture is local to this device.",
}

histories = {
    "left_rms": deque(maxlen=CONTEXT_AWARENESS),
    "right_rms": deque(maxlen=CONTEXT_AWARENESS),
    "prediction_error": deque(maxlen=CONTEXT_AWARENESS),
    "compete_response": deque(maxlen=CONTEXT_AWARENESS),
}


def log(message):
    line = "[{}] {}".format(time.strftime("%Y-%m-%d %H:%M:%S"), message)
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def clamp(value, low, high):
    return max(low, min(high, value))


def rms(values):
    if len(values) == 0:
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
    packed = struct.pack("<{}h".format(len(samples)), *[
        int(clamp(round(v), -32768, 32767)) for v in samples
    ])
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(packed)


def capture_wav(seconds=CAPTURE_SECONDS):
    """Capture a short microphone WAV and validate the finished recording.

    Keep record() argument-free for compatibility with Pythonista's
    sound.Recorder API. Stop explicitly, then allow the file to be finalised.
    """
    with CAPTURE_LOCK:
        safe_unlink(CAPTURE_PATH)
        with STATE_LOCK:
            state["capture_busy"] = True
            state["status"] = "Recording microphone window"
            state["error"] = ""

        recorder = None
        try:
            os.makedirs(os.path.dirname(CAPTURE_PATH), exist_ok=True)
            recorder = sound.Recorder(CAPTURE_PATH)
            recorder.record()
            time.sleep(max(0.2, float(seconds)))

            # Stop recording before opening the file; the header may not be
            # complete until stop() has returned.
            recorder.stop()
            recorder = None

            # iOS may need a short interval to flush the final audio data.
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
                    "Microphone recorder did not create the capture file. "
                    "Check Pythonista microphone permission and recorder startup."
                )

            file_size = os.path.getsize(CAPTURE_PATH)
            if file_size <= 44:
                raise RuntimeError(
                    "Recorder output is empty or incomplete ({} bytes). "
                    "Check microphone permission, then stop any competing "
                    "audio session and retry.".format(file_size)
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
                raise RuntimeError(
                    "Recorder output is not a readable PCM WAV: {}. "
                    "The Pythonista recorder may be writing a different audio "
                    "container format.".format(exc)
                )

            log("Microphone capture OK: {} bytes, {} Hz, {} channel(s), {} frames.".format(
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
# ANALYSIS
# ---------------------------------------------------------------------------

def channel_samples(samples):
    return samples[0::2], samples[1::2]


def goertzel_power(samples, sample_rate, low_hz, high_hz):
    """Estimate band energy from a small set of Goertzel bins."""
    if not samples:
        return 0.0
    n = len(samples)
    if n < 4:
        return 0.0
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
    bands = {name: goertzel_power(mono, rate, low, high)
             for name, (low, high) in ALL_BANDS.items()}
    return {
        "rate": rate,
        "left_rms": rms(left_n), "right_rms": rms(right_n),
        "left_pos_rms": half_rms(left_n, True),
        "left_neg_rms": half_rms(left_n, False),
        "right_pos_rms": half_rms(right_n, True),
        "right_neg_rms": half_rms(right_n, False),
        "bands": bands, "samples": samples,
    }


# ---------------------------------------------------------------------------
# GATE, BASELINE LEARNING, CONTEXT AND POSITIVE ENVELOPE
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
        # Compare against the PREVIOUS baseline before updating it.
        previous_baseline = (state["left_learned"] + state["right_learned"]) * 0.5
        signed_error = mean_level - previous_baseline
        positive_error = max(0.0, signed_error - MIC_DRIVE_DEADBAND)
        previous_envelope = state["mic_positive_envelope"]
        envelope = ((1.0 - MIC_DRIVE_SMOOTHING) * previous_envelope
                    + MIC_DRIVE_SMOOTHING * positive_error)
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

        # Continue baseline learning even when both gates are closed.
        state["left_learned"] = ((1.0 - LEARNING_RATE) * state["left_learned"]
                                 + LEARNING_RATE * left)
        state["right_learned"] = ((1.0 - LEARNING_RATE) * state["right_learned"]
                                  + LEARNING_RATE * right)

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
            state["tinman_action"] = "Learn background spectrum; gates remain independent"
            state["predicted_event"] = "Low-level ambient acoustic activity"
        else:
            state["tinman_context"] = "IDLE / LEARNING"
            state["tinman_action"] = "Update baseline; low positive drive"
            state["predicted_event"] = "No strong acoustic event"

        state["tinman_confidence"] = clamp(
            (mean_level - GATE_CLOSE_THRESHOLD) / 0.08, 0.0, 1.0
        )

        if active:
            if not state["stream_active"] or now - state["last_event_time"] > STREAM_JOIN_SECONDS:
                state["stream_started"] = now
                state["stream_events"] = 0
            state["stream_active"] = True
            state["stream_events"] += 1
            state["last_event_time"] = now
        elif state["stream_active"] and now - state["last_event_time"] > STREAM_JOIN_SECONDS:
            state["stream_active"] = False
        state["stream_windows"] += 1

        # Bounded per-band adaptive profile.
        band_mean = sum(bands.values()) / max(1, len(bands))
        for name, level in bands.items():
            target = clamp((band_mean - level) * 18.0,
                           -BAND_EQ_LIMIT_DB, BAND_EQ_LIMIT_DB)
            old = state["band_eq_db"].get(name, 0.0)
            state["band_eq_db"][name] = clamp(
                old + BAND_LEARNING_RATE * (target - old),
                -BAND_EQ_LIMIT_DB, BAND_EQ_LIMIT_DB
            )

        state["compete_delta"] = imbalance
        raw_compete = clamp(abs(imbalance) + state["tinman_confidence"] * 0.25, 0.0, 1.0)
        previous_compete = state["compete"]
        state["compete"] = clamp(0.70 * previous_compete + 0.30 * raw_compete, 0.0, 1.0)
        state["eq_compete_reduction"] = 0.0

        low_energy = bands.get("F1", 0.0) + bands.get("F4", 0.0)
        mid_energy = bands.get("F2", 0.0) + bands.get("F5", 0.0) + bands.get("F6", 0.0)
        high_energy = bands.get("F3", 0.0) + bands.get("F8", 0.0) + bands.get("F9", 0.0) + bands.get("F10", 0.0)
        total = low_energy + mid_energy + high_energy + 1e-9
        low_share, mid_share, high_share = low_energy/total, mid_energy/total, high_energy/total
        drive = state["compete"] * 2.0
        state["eq_low_db"] = clamp((mid_share-low_share)*8.0 + drive*0.35,
                                   MIN_EQ_GAIN_DB, MAX_EQ_GAIN_DB)
        state["eq_mid_db"] = clamp((0.34-mid_share)*7.0, MIN_EQ_GAIN_DB, MAX_EQ_GAIN_DB)
        state["eq_high_db"] = clamp((mid_share-high_share)*8.0-drive*0.25,
                                    MIN_EQ_GAIN_DB, MAX_EQ_GAIN_DB)
        state["controller_wave_db"] = clamp(BASE_DB + state["compete"]*9.0, 45.0, 54.0)

        histories["left_rms"].append(left)
        histories["right_rms"].append(right)
        histories["prediction_error"].append(abs(signed_error))
        for i in range(16):
            state["workers"][i] += 1
        state["status"] = "Microphone window analysed"
    return left_opened or right_opened


# ---------------------------------------------------------------------------
# OFFLINE EQ AND OUTPUT FILES
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
    high = [x-y for x, y in zip(raw, below_high)]
    mid = [x-lo-hi for x, lo, hi in zip(raw, low, high)]
    gl, gm, gh = [db_to_gain(clamp(v, -6.0, 6.0))
                  for v in (low_db, mid_db, high_db)]
    out = [lo*gl + mi*gm + hi*gh for lo, mi, hi in zip(low, mid, high)]
    peak = max([abs(x) for x in out] or [1.0])
    if peak > 32700.0:
        out = [x * (32700.0/peak) for x in out]
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
        component = [b-a for a, b in zip(lo, hi)]
        gain = db_to_gain(clamp(float(band_gains.get(name, 0.0)),
                                -BAND_EQ_LIMIT_DB, BAND_EQ_LIMIT_DB))
        delta = gain - 1.0
        adjusted = [v + c*delta for v, c in zip(adjusted, component)]
    peak = max([abs(x) for x in adjusted] or [1.0])
    if peak > 32700.0:
        adjusted = [x * (32700.0/peak) for x in adjusted]
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

    # Microphone-derived positive envelope is fed into the output gain stage.
    # Apply the same bounded gain to both channels to preserve stereo balance.
    drive_gain = db_to_gain(clamp(drive_db, 0.0, MIC_DRIVE_MAX_GAIN_DB))
    out_l = [x * drive_gain for x in out_l]
    out_r = [x * drive_gain for x in out_r]

    peak = max([abs(x) for x in out_l + out_r] or [1.0])
    if peak > 32700.0:
        scale = 32700.0 / peak
        out_l = [x*scale for x in out_l]
        out_r = [x*scale for x in out_r]

    interleaved = []
    for a, b in zip(out_l, out_r):
        interleaved.extend((int(round(a)), int(round(b))))
    write_wav_pcm16(PROCESSED_PATH, rate, 2, interleaved)

    # Display normalized output RMS after bounded gain and peak protection.
    with STATE_LOCK:
        state["last_processed"] = PROCESSED_PATH
        state["amplifier_output_rms"] = (
            rms([x / 32768.0 for x in out_l] +
                [x / 32768.0 for x in out_r])
        )
    log("Processed WAV: EQ L/M/H={:.1f}/{:.1f}/{:.1f} dB; mic drive={:.2f} dB".format(
        low_db, mid_db, high_db, drive_db))
    return PROCESSED_PATH


def make_reference_tone_wav():
    rate = SAMPLE_RATE
    count = int(rate * REFERENCE_TONE_SECONDS)
    frames = []
    for i in range(count):
        t = i / float(rate)
        env = min(1.0, t/0.025) * min(1.0, (REFERENCE_TONE_SECONDS-t)/0.06)
        sample = int(32767.0 * REFERENCE_TONE_AMPLITUDE * env *
                     math.sin(2.0*math.pi*REFERENCE_TONE_HZ*t))
        frames.extend((sample, sample))
    write_wav_pcm16(REFERENCE_FILE, rate, 2, frames)
    with STATE_LOCK:
        state["last_response"] = REFERENCE_FILE
        state["reference_tone_level"] = REFERENCE_TONE_AMPLITUDE
    return REFERENCE_FILE


def make_response_wav():
    with STATE_LOCK:
        compete = state["compete"]
        confidence = state["tinman_confidence"]
        enabled = state["alert_enabled"]
    rate = SAMPLE_RATE
    count = int(rate * RESPONSE_SECONDS)
    samples = []
    frequencies = (523.25, 659.25 + 25.0*compete, 783.99)
    starts = (0.08, 0.43, 0.78)
    for i in range(count):
        t = i / float(rate)
        value = 0.0
        for idx, onset in enumerate(starts):
            local_t = t-onset
            if 0.0 <= local_t < 0.22:
                env = min(1.0, local_t/0.012) * math.exp(-8.0*local_t)
                f = frequencies[idx]
                value = (0.075 + 0.02*confidence) * env * (
                    0.72*math.sin(2*math.pi*f*local_t) +
                    0.20*math.sin(2*math.pi*f*2.01*local_t) +
                    0.08*math.sin(2*math.pi*f*3.02*local_t))
                break
        ref_t = t - 0.24
        if enabled and 0.0 <= ref_t < 0.62:
            env = min(1.0, ref_t/0.025) * min(1.0, (0.62-ref_t)/0.06)
            value += REFERENCE_TONE_AMPLITUDE * env * math.sin(
                2*math.pi*REFERENCE_TONE_HZ*ref_t)
        sweep_t = t - 1.08
        if enabled and 0.0 <= sweep_t < HIGH_RESPONSE_SECONDS:
            p = sweep_t / HIGH_RESPONSE_SECONDS
            f = HIGH_RESPONSE_START_HZ + (HIGH_RESPONSE_END_HZ-HIGH_RESPONSE_START_HZ)*p
            value += HIGH_RESPONSE_AMPLITUDE * (math.sin(math.pi*p)**2) * math.sin(
                2*math.pi*f*sweep_t)
        if not enabled:
            value = 0.0
        sample = int(32767.0 * clamp(value, -0.8, 0.8))
        samples.extend((sample, sample))
    write_wav_pcm16(RESPONSE_PATH, rate, 2, samples)
    with STATE_LOCK:
        state["last_response"] = RESPONSE_PATH
    return RESPONSE_PATH


def play_file(path):
    player = None
    try:
        player = sound.Player(path)
        with STATE_LOCK:
            state["playback_busy"] = True
        player.play()
        try:
            with wave.open(path, "rb") as wf:
                duration = wf.getnframes() / float(wf.getframerate())
        except Exception:
            duration = 1.0
        time.sleep(min(max(duration, 0.1), 10.0))
    except Exception as exc:
        log("Playback error: {}".format(exc))
    finally:
        with STATE_LOCK:
            state["playback_busy"] = False


# ---------------------------------------------------------------------------
# AUDIO WORKER
# ---------------------------------------------------------------------------

def audio_worker():
    log("Starting local microphone capture and Tin-Man learning loop.")
    last_reference_play = 0.0
    try:
        reference = make_reference_tone_wav()
        with STATE_LOCK:
            enabled = state["alert_enabled"]
        if enabled:
            threading.Thread(target=play_file, args=(reference,), daemon=True,
                             name="TinManReferenceTone").start()
            last_reference_play = time.time()
            log("1099 Hz reference tone generated and playback requested.")
    except Exception as exc:
        log("Reference tone setup failed: {}".format(exc))

    while not STOP_EVENT.is_set():
        try:
            now = time.time()
            with STATE_LOCK:
                due = (state["alert_enabled"] and not state["playback_busy"]
                       and now-last_reference_play >= REFERENCE_AUTO_INTERVAL)
            if due:
                reference = make_reference_tone_wav()
                threading.Thread(target=play_file, args=(reference,), daemon=True,
                                 name="TinManReferenceTone").start()
                last_reference_play = time.time()

            path = capture_wav(CAPTURE_SECONDS)
            metrics = analyze_wav(path)
            newly_opened = update_context_controller(metrics)
            with STATE_LOCK:
                state["last_capture"] = path
            processed = process_capture_eq(path)

            if newly_opened:
                now = time.time()
                with STATE_LOCK:
                    should_alert = (state["alert_enabled"] and
                                    not state["playback_busy"] and
                                    now >= state["alert_cooldown_until"])
                    if should_alert:
                        state["alert_cooldown_until"] = now + ALERT_COOLDOWN_SECONDS
                    histories["compete_response"].append(state["compete"])
                    state["message"] = ("Acoustic event: response played" if should_alert
                                         else "Event captured; alert on cooldown/disabled")
                if should_alert:
                    response = make_response_wav()
                    threading.Thread(target=play_file, args=(response,), daemon=True).start()
                    log("Gate opened: local response requested.")
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
# PYTHONISTA SCENE UI
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
                return tuple(int(h[i:i+2], 16)/255.0 for i in (0,2,4,6))
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
    scene.rect(x, y, width*frac, height)


class SurveyScene(scene.Scene):
    def setup(self):
        self.background_color = (0.035, 0.045, 0.07)
        self.audio_started = False

    def update(self):
        if not self.audio_started and not STOP_EVENT.is_set():
            self.audio_started = True
            threading.Thread(target=audio_worker, daemon=True,
                             name="TinManAudioWorker").start()

    def draw(self):
        w, h = self.size.w, self.size.h
        scene.background(0.035, 0.045, 0.07)
        sx = max(20.0, w*0.08)
        safe_y = max(24.0, h*0.06)
        content_w = max(1.0, w-2*sx)
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
            draw_text(text, left+5, y, size, color)

        y = h-safe_y-20
        line(APP_NAME, y, 14)
        y -= 19
        line("SUNBEAM STEREO RMS LEARNING / LOCAL", y, 8, "#86D9D0")
        y -= 15

        panel(y-72, 72)
        line("STEREO RMS / LEARNED BASELINE", y-14, 9)
        draw_text("L {:.4f}  learned {:.4f}".format(s["left_rms"], s["left_learned"]),
                  left+5, y-33, 8)
        draw_bar(left+5, y-43, inner_w*0.45, 5, s["left_rms"], 0.20)
        draw_text("R {:.4f}  learned {:.4f}".format(s["right_rms"], s["right_learned"]),
                  left+inner_w*0.52, y-33, 8)
        draw_bar(left+inner_w*0.52, y-43, inner_w*0.43, 5, s["right_rms"], 0.20)
        draw_text("L +{:.4f} / -{:.4f}".format(s["left_pos_rms"], s["left_neg_rms"]),
                  left+5, y-60, 7)
        draw_text("R +{:.4f} / -{:.4f}".format(s["right_pos_rms"], s["right_neg_rms"]),
                  left+inner_w*0.52, y-60, 7)
        y -= 80

        panel(y-44, 44, (0.055, 0.08, 0.12, 1.0))
        line("MICROPHONE GATES", y-13, 9)
        draw_text("LEFT " + ("OPEN" if s["left_gate"] else "CLOSED"),
                  left+5, y-31, 8, "#35D6A5" if s["left_gate"] else "#AAB4C8")
        draw_text("RIGHT " + ("OPEN" if s["right_gate"] else "CLOSED"),
                  left+inner_w*0.52, y-31, 8,
                  "#35D6A5" if s["right_gate"] else "#AAB4C8")
        y -= 52

        panel(y-79, 79, (0.065, 0.095, 0.13, 1.0))
        line("TIN-MAN / CONTEXT LEARNING", y-14, 9)
        line(s["tinman_context"], y-30, 8, "#35D6A5")
        line("Action: " + s["tinman_action"], y-44, 7)
        line("Prediction: " + s["predicted_event"], y-57, 7, "#AAB4C8")
        line("Confidence {:.0f}% | contexts {}".format(
            s["tinman_confidence"]*100, s["context_count"]), y-70, 7)
        y -= 87

        panel(y-94, 94)
        line("MIC DRIVE / AMPLIFIER PROCESSING", y-14, 9)
        line("Signed prediction error: {:+.5f}".format(s["mic_signed_error"]), y-31, 8)
        line("Positive envelope: {:.5f}".format(s["mic_positive_envelope"]), y-46, 8)
        line("Bounded output drive: +{:.2f} dB".format(s["mic_drive_gain_db"]), y-61, 8, "#86D9D0")
        draw_bar(left+5, y-72, inner_w-10, 5, s["mic_drive_gain_db"], MIC_DRIVE_MAX_GAIN_DB)
        line("Input RMS {:.4f} | output RMS {:.4f}".format(
            s["amplifier_input_rms"], s["amplifier_output_rms"]), y-87, 7)
        y -= 102

        panel(y-61, 61, (0.055, 0.075, 0.12, 1.0))
        line("COMPETE / BOUNDED EQ", y-14, 9)
        line("Compete {:.3f} | stereo delta {:+.3f}".format(
            s["compete"], s["compete_delta"]), y-30, 8)
        line("EQ L/M/H {:+.1f} / {:+.1f} / {:+.1f} dB".format(
            s["eq_low_db"], s["eq_mid_db"], s["eq_high_db"]), y-45, 8, "#86D9D0")
        line("Reference {:.0f} Hz | response local".format(s["reference_tone_hz"]), y-57, 7)
        y -= 69

        panel(y-50, 50)
        line("F0-F16 ADAPTIVE ACOUSTIC BANDS", y-13, 8)
        keys = ["F0","F1","F2","F3","F4","F5","F6","F7","F8",
                "F9","F10","F11","F12","F13","F14","F15","F16"]
        bw = (inner_w-10)/len(keys)
        for i, key in enumerate(keys):
            bx = left+5+i*bw
            draw_text(key, bx, y-27, 6, "#86D9D0")
            draw_bar(bx, y-39, max(2, bw-2), 3, s["bands"].get(key, 0.0), 0.06)
        y -= 57

        # Small Tin-Man avatar in its own safe area.
        avatar_x = w*0.5
        avatar_y = max(safe_y+25, y-18)
        scene.no_fill()
        scene.stroke(0.20, 0.78, 0.70, 1.0)
        scene.stroke_weight(1.5)
        scene.ellipse(avatar_x-15, avatar_y-10, 30, 30)
        scene.ellipse(avatar_x-26, avatar_y+1, 13, 15)
        scene.ellipse(avatar_x+13, avatar_y+1, 13, 15)
        scene.no_stroke()
        scene.fill(0.20, 0.78, 0.70, 1.0)
        scene.ellipse(avatar_x-6, avatar_y+1, 3, 3)
        scene.ellipse(avatar_x+3, avatar_y+1, 3, 3)

        footer = s["stream_profile"] + " | " + s["status"]
        if s["error"]:
            footer = "ERROR: " + str(s["error"])
        draw_text(footer[:70], left, safe_y+6, 6, "#AAB4C8")
        draw_text("Tap screen to stop", left, safe_y+17, 6, "#AAB4C8")

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
    log("Microphone-derived positive envelope enabled; output gain capped at +{:.1f} dB.".format(
        MIC_DRIVE_MAX_GAIN_DB))
    log("F0-F16 are acoustic bands; F4-F10 labels do not measure infrared.")
    log("File/chunk processing only; no claim of live hardware amplification or sound cancellation.")
    scene.run(SurveyScene(), show_fps=False)


if __name__ == "__main__":
    main()
