#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CB12 Y-Band Scope — corrected local audio analysis with multipass processing
Pythonista for iOS

- Captures short microphone buffers locally.
- Analyses each buffer in multiple passes: raw, short-window low-pass,
  long-window low-pass, and high-pass residual.
- Reports RMS, zero-crossing rate, peak, and a heuristic multipass score.
- Displays a 2 Hz visual sweep and audio-derived contacts.
- No network or location access.

Limitations:
- This analyses microphone audio, not radio-frequency energy.
- Contact positions are visualization coordinates, not physical bearings.
- "Interference score" is a heuristic measure of variation across audio
  processing passes; it does not identify the cause or source of a signal.
"""

import os
import time
import math
import wave
import struct
import threading
import tempfile
from collections import deque

import sound
import scene


# --------------------------- Configuration ---------------------------

SAMPLE_SECONDS = 3.0
PULSON_HZ = 2.0
SCOPE_HISTORY_SECONDS = 8.0
CONTACT_COOLDOWN = 0.45

RMS_GATE = 0.012
INTERFERENCE_GATE = 0.22

# Moving-average filter window durations. These are processing parameters,
# not claims about the source or transmission frequency.
SHORT_WINDOW_SECONDS = 0.004
LONG_WINDOW_SECONDS = 0.020

APP_NAME = "CB12 · Multipass Y-Band Scope"
CAPTURE_FILENAME = "cb12_yband_capture.wav"


# --------------------------- WAV decoding ---------------------------

def read_pcm_wav(path):
    """Read integer PCM WAV audio and return mono floats and sample rate."""
    with wave.open(path, "rb") as wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        frame_count = wf.getnframes()
        frames = wf.readframes(frame_count)

    if channels < 1:
        raise ValueError("WAV file has no audio channels")

    if width == 1:
        values = [(value - 128) / 128.0 for value in frames]

    elif width == 2:
        count = len(frames) // 2
        unpacked = struct.unpack(
            "<{}h".format(count),
            frames[:count * 2]
        )
        values = [value / 32768.0 for value in unpacked]

    elif width == 3:
        # WAV 24-bit PCM is little-endian signed integer.
        values = []

        for offset in range(0, len(frames) - 2, 3):
            value = (
                frames[offset]
                | (frames[offset + 1] << 8)
                | (frames[offset + 2] << 16)
            )

            if value & 0x800000:
                value -= 1 << 24

            values.append(value / 8388608.0)

    elif width == 4:
        count = len(frames) // 4
        unpacked = struct.unpack(
            "<{}i".format(count),
            frames[:count * 4]
        )
        values = [value / 2147483648.0 for value in unpacked]

    else:
        raise ValueError(
            "Unsupported PCM sample width: {}".format(width)
        )

    # Convert multichannel input to mono by averaging channels.
    if channels > 1:
        mono = []
        usable = len(values) - (len(values) % channels)

        for index in range(0, usable, channels):
            mono.append(
                sum(values[index:index + channels]) / channels
            )

        values = mono

    if not values:
        raise ValueError("WAV file contains no samples")

    return values, rate


# --------------------------- Multipass DSP ---------------------------

def moving_average(samples, window_size):
    """O(n) centered moving average, with edge values safely clamped."""
    n = len(samples)

    if n == 0:
        return []

    window_size = max(1, int(window_size))

    if window_size % 2 == 0:
        window_size += 1

    if window_size == 1:
        return list(samples)

    half = window_size // 2

    # Prefix sums make the moving average linear-time.
    prefix = [0.0] * (n + 1)

    for index, value in enumerate(samples):
        prefix[index + 1] = prefix[index] + value

    output = []

    for index in range(n):
        left = max(0, index - half)
        right = min(n, index + half + 1)

        output.append(
            (prefix[right] - prefix[left]) / (right - left)
        )

    return output


def measure_audio(samples):
    """Return RMS, zero-crossing rate, peak amplitude, and sample count."""
    if not samples:
        return 0.0, 0.0, 0.0, 0

    count = len(samples)

    rms = math.sqrt(
        sum(value * value for value in samples) / count
    )

    peak = max(abs(value) for value in samples)

    crossings = 0
    previous = samples[0]

    for value in samples[1:]:
        if (
            (previous < 0.0 <= value)
            or (previous >= 0.0 > value)
        ):
            crossings += 1

        previous = value

    zcr = crossings / float(max(1, count - 1))

    return rms, zcr, peak, count


def analyse_multipass(samples, sample_rate):
    """
    Run raw, short low-pass, long low-pass, and high-pass residual passes.

    Return metrics and a heuristic interference score in the range 0..1+.
    """
    if not samples:
        raise ValueError("Cannot analyse an empty audio buffer")

    short_window = max(
        1,
        int(sample_rate * SHORT_WINDOW_SECONDS)
    )

    long_window = max(
        short_window + 2,
        int(sample_rate * LONG_WINDOW_SECONDS)
    )

    # Pass 1: raw audio.
    raw_metrics = measure_audio(samples)

    # Pass 2: short-window moving-average filter.
    short_pass = moving_average(
        samples,
        short_window
    )

    # Pass 3: long-window moving-average filter.
    long_pass = moving_average(
        samples,
        long_window
    )

    # Pass 4: residual relative to the long-window baseline.
    high_pass = [
        original - baseline
        for original, baseline in zip(samples, long_pass)
    ]

    short_metrics = measure_audio(short_pass)
    long_metrics = measure_audio(long_pass)
    high_metrics = measure_audio(high_pass)

    raw_rms = raw_metrics[0]
    short_rms = short_metrics[0]
    long_rms = long_metrics[0]
    high_rms = high_metrics[0]

    # Relative residual energy plus disagreement between smoothing passes.
    # This is descriptive only; it is not a source classifier.
    residual_ratio = high_rms / max(raw_rms, 1e-9)

    pass_disagreement = (
        abs(short_rms - long_rms) / max(raw_rms, 1e-9)
    )

    interference_score = min(
        2.0,
        0.75 * residual_ratio + 0.25 * pass_disagreement
    )

    return {
        "raw": raw_metrics,
        "short": short_metrics,
        "long": long_metrics,
        "high": high_metrics,
        "interference_score": interference_score,
        "short_window_samples": short_window,
        "long_window_samples": long_window,
    }


def classify_measurement(result):
    """Produce descriptive labels from the multipass metrics."""
    raw_rms, raw_zcr, raw_peak, _ = result["raw"]
    high_rms, high_zcr, high_peak, _ = result["high"]
    score = result["interference_score"]

    if raw_rms < RMS_GATE:
        alpha = "Alpha · below RMS gate"
    else:
        alpha = "Alpha · audio level active"

    if raw_zcr < 0.035:
        beta = "Beta · low raw ZCR"
    elif raw_zcr < 0.16:
        beta = "Beta · mid raw ZCR"
    else:
        beta = "Beta · high raw ZCR"

    if raw_peak > 0.98:
        color = "Color · possible clipping"
    elif raw_rms >= RMS_GATE:
        color = "Color · audio above gate"
    else:
        color = "Color · baseline level"

    if high_rms >= RMS_GATE and score >= INTERFERENCE_GATE:
        delta = "Delta · elevated residual variation"
    else:
        delta = "Delta · residual variation lower"

    if score >= INTERFERENCE_GATE:
        echo = "Echo · multipass variation elevated"
    else:
        echo = "Echo · multipass variation lower"

    gamma = "Gamma · raw RMS {:.4f}".format(raw_rms)
    theta = "Theta · raw ZCR {:.4f}".format(raw_zcr)
    multipass = "Multipass · score {:.3f}".format(score)

    highpass = "Residual · RMS {:.4f}, ZCR {:.4f}".format(
        high_rms,
        high_zcr
    )

    return [
        alpha,
        beta,
        color,
        delta,
        echo,
        gamma,
        theta,
        multipass,
        highpass
    ]


# --------------------------- Capture worker ---------------------------

class AudioMonitor:
    def __init__(self):
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.recorder_lock = threading.Lock()

        self.recorder = None
        self.thread = None
        self.running = False

        self.last_event_time = 0.0
        self.event_id = 0

        self.latest = {
            "timestamp": 0.0,
            "event_id": 0,
            "rms": 0.0,
            "zcr": 0.0,
            "peak": 0.0,
            "interference_score": 0.0,
            "labels": ["CB12 · waiting for microphone"],
            "status": "Waiting for microphone permission",
            "event": False,
        }

        self.history = deque(maxlen=120)

        self.capture_path = os.path.join(
            tempfile.gettempdir(),
            CAPTURE_FILENAME
        )

    def start(self):
        if self.running:
            return

        self.running = True
        self.stop_event.clear()

        self.thread = threading.Thread(
            target=self._run,
            daemon=True
        )

        self.thread.start()

    def stop(self):
        self.running = False
        self.stop_event.set()

        # Stop an active recorder promptly rather than waiting out the full
        # capture interval. Recorder access is guarded against worker races.
        with self.recorder_lock:
            recorder = self.recorder

        if recorder is not None:
            try:
                recorder.stop()
            except Exception:
                pass

    def snapshot(self):
        with self.lock:
            return dict(self.latest), list(self.history)

    def _set_status(self, status):
        with self.lock:
            self.latest = dict(self.latest)
            self.latest["status"] = status
            self.latest["timestamp"] = time.time()

    def _run(self):
        while self.running and not self.stop_event.is_set():
            recorder = None

            try:
                self._set_status(
                    "Recording local audio · {:.1f}s".format(
                        SAMPLE_SECONDS
                    )
                )

                # Remove a stale file so a failed capture cannot silently
                # reuse the previous buffer.
                try:
                    if os.path.exists(self.capture_path):
                        os.remove(self.capture_path)
                except OSError:
                    pass

                recorder = sound.Recorder(
                    self.capture_path,
                    format="wav"
                )

                with self.recorder_lock:
                    self.recorder = recorder

                recorder.record()

                deadline = time.time() + SAMPLE_SECONDS

                while (
                    self.running
                    and not self.stop_event.is_set()
                    and time.time() < deadline
                ):
                    time.sleep(0.05)

                try:
                    recorder.stop()

                finally:
                    with self.recorder_lock:
                        if self.recorder is recorder:
                            self.recorder = None

                    recorder = None

                if not self.running or self.stop_event.is_set():
                    break

                samples, sample_rate = read_pcm_wav(
                    self.capture_path
                )

                result = analyse_multipass(
                    samples,
                    sample_rate
                )

                labels = classify_measurement(result)

                raw_rms, raw_zcr, raw_peak, count = result["raw"]
                score = result["interference_score"]
                now = time.time()

                event = (
                    raw_rms >= RMS_GATE
                    or (
                        result["high"][0] >= RMS_GATE
                        and score >= INTERFERENCE_GATE
                    )
                )

                # Cooldown controls new contact markers, not analysis itself.
                emit_contact = (
                    event
                    and now - self.last_event_time >= CONTACT_COOLDOWN
                )

                if emit_contact:
                    self.last_event_time = now
                    self.event_id += 1

                status = (
                    "Analysed {} samples at {} Hz · 4 passes".format(
                        count,
                        sample_rate
                    )
                )

                entry = {
                    "timestamp": now,
                    "event_id": self.event_id,
                    "rms": raw_rms,
                    "zcr": raw_zcr,
                    "peak": raw_peak,
                    "interference_score": score,
                    "labels": labels,
                    "status": status,
                    "event": emit_contact,
                    "rate": sample_rate,
                    "count": count,
                    "high_rms": result["high"][0],
                }

                with self.lock:
                    self.latest = entry

                    self.history.append({
                        "time": now,
                        "rms": raw_rms,
                        "zcr": raw_zcr,
                        "score": score,
                        "event": emit_contact,
                    })

                print(
                    "[CB12] rate={}Hz samples={} RMS={:.5f} "
                    "ZCR={:.5f} peak={:.4f} multipass={:.3f} "
                    "residual_RMS={:.5f}".format(
                        sample_rate,
                        count,
                        raw_rms,
                        raw_zcr,
                        raw_peak,
                        score,
                        result["high"][0]
                    )
                )

                for label in labels:
                    print("  " + label)

            except Exception as exc:
                self._set_status(
                    "Capture/analysis unavailable: {}".format(exc)
                )

                print(
                    "[CB12] Capture error: {!r}".format(exc)
                )

                self.stop_event.wait(0.75)

            finally:
                if recorder is not None:
                    try:
                        recorder.stop()
                    except Exception:
                        pass

                    with self.recorder_lock:
                        if self.recorder is recorder:
                            self.recorder = None

            self.stop_event.wait(0.05)


# --------------------------- Scope UI ---------------------------

class YBandScope(scene.Scene):
    def setup(self):
        self.background_color = (
            0.025,
            0.035,
            0.055
        )

        self.monitor = AudioMonitor()
        self.monitor.start()

        self.start_time = time.time()
        self.blips = deque(maxlen=80)
        self.last_seen_event_id = 0

        self.latest = {}
        self.history = []

        self.sweep_phase = 0.0
        self.paused = False

    def stop(self):
        if hasattr(self, "monitor"):
            self.monitor.stop()

    def update(self):
        if self.paused:
            return

        now = time.time()

        self.sweep_phase = (
            (now - self.start_time) * PULSON_HZ
        ) % 1.0

        latest, history = self.monitor.snapshot()

        self.latest = latest
        self.history = history

        event_id = latest.get("event_id", 0)

        if (
            latest.get("event")
            and event_id != self.last_seen_event_id
        ):
            self.last_seen_event_id = event_id

            # Deterministic display coordinate derived from audio metrics;
            # not a measured direction or bearing.
            zcr = latest.get("zcr", 0.0)
            score = latest.get("interference_score", 0.0)

            angle = (
                zcr * 997.0 + score * 3.1
            ) % (2.0 * math.pi)

            rms = latest.get("rms", 0.0)

            radius_fraction = (
                0.15 + min(0.72, rms * 2.5)
            )

            self.blips.append({
                "time": now,
                "angle": angle,
                "radius": radius_fraction,
                "rms": rms,
                "score": score,
            })

        while (
            self.blips
            and now - self.blips[0]["time"] > SCOPE_HISTORY_SECONDS
        ):
            self.blips.popleft()

    def draw(self):
        w, h = self.size.w, self.size.h

        cx = w * 0.5
        cy = h * 0.49

        radius = min(
            w * 0.39,
            h * 0.31
        )

        # FIX 1: use three RGB arguments for Pythonista's scene background.
        scene.background(0.025, 0.035, 0.055)

        self._text(
            APP_NAME,
            w * 0.5,
            h - 36,
            21,
            (0.85, 0.92, 1.0)
        )

        self._text(
            "LOCAL AUDIO · 4-PASS ANALYSIS · {:.1f} Hz SWEEP".format(
                PULSON_HZ
            ),
            w * 0.5,
            h - 60,
            9,
            (0.55, 0.70, 0.83)
        )

        # Ground-plane rings and radial lines.
        for fraction in (0.25, 0.5, 0.75, 1.0):
            self._circle(
                cx,
                cy,
                radius * fraction,
                (0.15, 0.33, 0.42),
                1.0
            )

        for index in range(12):
            angle = 2.0 * math.pi * index / 12.0

            self._line(
                cx,
                cy,
                cx + math.cos(angle) * radius,
                cy + math.sin(angle) * radius,
                (0.10, 0.23, 0.31),
                1.0
            )

        # Visual sweep only; this does not transmit or receive RF.
        angle = self.sweep_phase * 2.0 * math.pi

        self._line(
            cx,
            cy,
            cx + math.cos(angle) * radius,
            cy + math.sin(angle) * radius,
            (0.25, 0.85, 0.68),
            2.0
        )

        now = time.time()

        for blip in self.blips:
            age = now - blip["time"]

            fade = max(
                0.15,
                1.0 - age / SCOPE_HISTORY_SECONDS
            )

            bx = (
                cx
                + math.cos(blip["angle"])
                * radius
                * blip["radius"]
            )

            by = (
                cy
                + math.sin(blip["angle"])
                * radius
                * blip["radius"]
            )

            scene.push_matrix()
            scene.translate(bx, by)

            scene.fill(
                0.95,
                0.65,
                0.25,
                fade
            )

            scene.no_stroke()
            scene.ellipse(-4, -4, 8, 8)

            scene.pop_matrix()

        latest = self.latest or {}

        rms = latest.get("rms", 0.0)
        zcr = latest.get("zcr", 0.0)
        peak = latest.get("peak", 0.0)
        score = latest.get("interference_score", 0.0)

        status = latest.get(
            "status",
            "Starting"
        )

        self._text(
            "RMS {:.4f}   ZCR {:.4f}   PEAK {:.3f}   MP {:.3f}".format(
                rms,
                zcr,
                peak,
                score
            ),
            w * 0.5,
            cy - radius - 27,
            10,
            (0.78, 0.86, 0.91)
        )

        self._text(
            status[:76],
            w * 0.5,
            cy - radius - 46,
            8,
            (0.62, 0.72, 0.80)
        )

        labels = latest.get("labels", [])

        y = cy - radius - 70

        for label in labels:
            self._text(
                label,
                w * 0.5,
                y,
                9,
                (0.68, 0.80, 0.88)
            )

            y -= 13

        self._text(
            "Tap to pause/resume · multipass score is heuristic",
            w * 0.5,
            18,
            8,
            (0.48, 0.60, 0.69)
        )

    def touch_began(self, touch):
        self.paused = not self.paused

        if self.paused:
            self.monitor.stop()

        else:
            self.monitor = AudioMonitor()
            self.monitor.start()
            self.start_time = time.time()

    def _text(self, text, x, y, size, color):
        scene.fill(*color)

        scene.text(
            text,
            "Helvetica",
            size,
            x,
            y
        )

    def _line(self, x1, y1, x2, y2, color, width):
        # FIX 2: do not use scene.Path(), which is unavailable here.
        # Draw lines immediately without creating persistent shape nodes.
        scene.stroke(*color)
        scene.stroke_weight(width)
        scene.line(x1, y1, x2, y2)

    def _circle(self, x, y, r, color, width):
        scene.no_fill()
        scene.stroke(*color)
        scene.stroke_weight(width)

        scene.ellipse(
            x - r,
            y - r,
            r * 2,
            r * 2
        )


if __name__ == "__main__":
    scene.run(
        YBandScope(),
        show_fps=False,
        orientation=scene.PORTRAIT
    )
