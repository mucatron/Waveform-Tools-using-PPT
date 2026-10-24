#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WHOLE-SCOPE L-BAND ROTOR + OPPOSITION LEARNING
Pythonista / iOS

Features:
- 12 rotor sectors across the whole scope.
- Each sector generates a soundform and inverted opposition.
- Per-sector measurements are learned locally.
- A continuous stereo WAV is written to Documents/wav.
- JSON stores local learning measurements.
- Scope labels are rendered with bitmap rectangles, not scene.text().

This is a local synthetic audio model. It does not transmit or receive
actual L-band radio signals and does not capture microphone audio.
"""

import os
import math
import json
import time
import wave
import queue
import threading

from scene import *


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

SAMPLE_RATE = 22050
CHANNELS = 2
SAMPLE_WIDTH_BYTES = 2

SECTOR_COUNT = 12
BASE_AUDIO_HZ = 92.0
SECTOR_STEP_HZ = 13.0
MAX_AUDIO_HZ = 700.0

ROTOR_SPEED = 0.45
ROTOR_DEPTH = 0.18
OPPOSITION_AMPLIFICATION = 1.50

LEARNING_RATE = 0.08
MASTER_GAIN = 0.38
OUTPUT_LIMIT = 0.92

WAV_BLOCK_SAMPLES = 512
WRITER_QUEUE_BLOCKS = 24

APP_FOLDER = os.path.expanduser('~/Documents/wav')

WAV_PATH = os.path.join(
    APP_FOLDER,
    'scope_lband_rotor_opposition_learning.wav'
)

STATE_PATH = os.path.join(
    APP_FOLDER,
    'scope_lband_learning_state.json'
)


# ------------------------------------------------------------
# Bitmap font: no scene.text() calls
# ------------------------------------------------------------

_BITMAP_FONT = {
    'A': ('01110','10001','10001','11111','10001','10001','10001'),
    'B': ('11110','10001','10001','11110','10001','10001','11110'),
    'C': ('01111','10000','10000','10000','10000','10000','01111'),
    'D': ('11110','10001','10001','10001','10001','10001','11110'),
    'E': ('11111','10000','10000','11110','10000','10000','11111'),
    'F': ('11111','10000','10000','11110','10000','10000','10000'),
    'G': ('01111','10000','10000','10111','10001','10001','01111'),
    'H': ('10001','10001','10001','11111','10001','10001','10001'),
    'I': ('11111','00100','00100','00100','00100','00100','11111'),
    'J': ('00111','00010','00010','00010','10010','10010','01100'),
    'K': ('10001','10010','10100','11000','10100','10010','10001'),
    'L': ('10000','10000','10000','10000','10000','10000','11111'),
    'M': ('10001','11011','10101','10101','10001','10001','10001'),
    'N': ('10001','11001','10101','10011','10001','10001','10001'),
    'O': ('01110','10001','10001','10001','10001','10001','01110'),
    'P': ('11110','10001','10001','11110','10000','10000','10000'),
    'Q': ('01110','10001','10001','10001','10101','10010','01101'),
    'R': ('11110','10001','10001','11110','10100','10010','10001'),
    'S': ('01111','10000','10000','01110','00001','00001','11110'),
    'T': ('11111','00100','00100','00100','00100','00100','00100'),
    'U': ('10001','10001','10001','10001','10001','10001','01110'),
    'V': ('10001','10001','10001','10001','10001','01010','00100'),
    'W': ('10001','10001','10001','10101','10101','10101','01010'),
    'X': ('10001','10001','01010','00100','01010','10001','10001'),
    'Y': ('10001','10001','01010','00100','00100','00100','00100'),
    'Z': ('11111','00001','00010','00100','01000','10000','11111'),

    '0': ('01110','10001','10011','10101','11001','10001','01110'),
    '1': ('00100','01100','00100','00100','00100','00100','01110'),
    '2': ('01110','10001','00001','00010','00100','01000','11111'),
    '3': ('11110','00001','00001','01110','00001','00001','11110'),
    '4': ('00010','00110','01010','10010','11111','00010','00010'),
    '5': ('11111','10000','10000','11110','00001','00001','11110'),
    '6': ('01110','10000','10000','11110','10001','10001','01110'),
    '7': ('11111','00001','00010','00100','01000','01000','01000'),
    '8': ('01110','10001','10001','01110','10001','10001','01110'),
    '9': ('01110','10001','10001','01111','00001','00001','01110'),

    '.': ('00000','00000','00000','00000','00000','00110','00110'),
    ',': ('00000','00000','00000','00000','00110','00100','01000'),
    ':': ('00000','00110','00110','00000','00110','00110','00000'),
    ';': ('00000','00110','00110','00000','00110','00100','01000'),
    '-': ('00000','00000','00000','11111','00000','00000','00000'),
    '+': ('00000','00100','00100','11111','00100','00100','00000'),
    '/': ('00001','00010','00010','00100','01000','01000','10000'),
    '|': ('00100','00100','00100','00100','00100','00100','00100'),
    '%': ('11001','11010','00100','01000','10110','00110','00000'),
    '*': ('00000','10101','01110','11111','01110','10101','00000'),
    '_': ('00000','00000','00000','00000','00000','00000','11111'),
    '=': ('00000','11111','00000','11111','00000','00000','00000'),
    '(': ('00010','00100','01000','01000','01000','00100','00010'),
    ')': ('01000','00100','00010','00010','00010','00100','01000'),
    '[': ('01110','01000','01000','01000','01000','01000','01110'),
    ']': ('01110','00010','00010','00010','00010','00010','01110'),
    "'": ('00100','00100','00010','00000','00000','00000','00000'),
    ' ': ('00000','00000','00000','00000','00000','00000','00000'),
}


def draw_label(value, x, y, size=12):
    """Draw centered bitmap text using scene rectangles."""
    label = str(value).upper()

    cell = max(0.75, float(size) / 7.0)
    gap = cell
    advance = 5.0 * cell + gap

    total_width = max(
        0.0,
        len(label) * advance - gap
    )

    start_x = float(x) - total_width * 0.5
    start_y = float(y) - 3.5 * cell

    pixel_inset = max(0.0, cell * 0.08)
    pixel_size = max(0.5, cell - pixel_inset)

    no_stroke()

    for char_index, char in enumerate(label):
        glyph = _BITMAP_FONT.get(
            char,
            _BITMAP_FONT[' ']
        )

        gx = start_x + char_index * advance

        for row_index, row in enumerate(glyph):
            # Glyph rows are top-to-bottom.
            # Scene coordinates increase upward.
            py = start_y + (6 - row_index) * cell

            for col_index, bit in enumerate(row):
                if bit == '1':
                    px = gx + col_index * cell
                    rect(
                        px,
                        py,
                        pixel_size,
                        pixel_size
                    )


# ------------------------------------------------------------
# Continuous stereo WAV writer
# ------------------------------------------------------------

class ContinuousWavWriter:

    def __init__(self, path):
        self.path = path
        self.queue = queue.Queue(
            maxsize=WRITER_QUEUE_BLOCKS
        )

        self.stop_event = threading.Event()
        self.thread = None
        self.error = None
        self.frames_written = 0
        self.dropped_blocks = 0
        self.started_at = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return

        os.makedirs(
            os.path.dirname(self.path),
            exist_ok=True
        )

        self.queue = queue.Queue(
            maxsize=WRITER_QUEUE_BLOCKS
        )

        self.stop_event.clear()
        self.error = None
        self.frames_written = 0
        self.dropped_blocks = 0
        self.started_at = time.time()

        self.thread = threading.Thread(
            target=self._worker,
            name='LocalWavWriter',
            daemon=True
        )

        self.thread.start()

    def submit(self, block):
        if self.stop_event.is_set() or self.error:
            return False

        try:
            self.queue.put_nowait(block)
            return True

        except queue.Full:
            self.dropped_blocks += 1
            return False

    def _worker(self):
        try:
            with wave.open(self.path, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(SAMPLE_WIDTH_BYTES)
                wf.setframerate(SAMPLE_RATE)

                while (
                    not self.stop_event.is_set()
                    or not self.queue.empty()
                ):
                    try:
                        block = self.queue.get(timeout=0.15)

                    except queue.Empty:
                        continue

                    try:
                        wf.writeframesraw(block)

                        self.frames_written += (
                            len(block)
                            // (
                                CHANNELS
                                * SAMPLE_WIDTH_BYTES
                            )
                        )

                    finally:
                        self.queue.task_done()

                # The wave module finalises the header on close.

        except Exception as exc:
            self.error = str(exc)

    def stop(self, timeout=5.0):
        self.stop_event.set()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=timeout)

    @property
    def elapsed_seconds(self):
        if not self.started_at:
            return 0.0

        return max(
            0.0,
            time.time() - self.started_at
        )


# ------------------------------------------------------------
# One rotor / opposition learner per sector
# ------------------------------------------------------------

class SectorRotor:

    def __init__(self, index):
        self.index = index

        self.angle = (
            2.0 * math.pi * index / SECTOR_COUNT
        )

        self.phase = index * 0.713
        self.rotor_phase = index * 0.37

        self.frequency = min(
            MAX_AUDIO_HZ,
            BASE_AUDIO_HZ + index * SECTOR_STEP_HZ
        )

        self.rms = 0.0
        self.opposition_rms = 0.0
        self.learned_rms = 0.0
        self.learned_opposition = 0.0
        self.opposition_score = 0.0
        self.samples_seen = 0
        self.activity = 0.0

    def next_block(self, count, sample_rate, elapsed):
        original = []
        opposite = []

        omega = (
            2.0 * math.pi
            * self.frequency
            / float(sample_rate)
        )

        rotor_rate = (
            ROTOR_SPEED
            * (0.75 + self.index * 0.035)
        )

        depth = (
            ROTOR_DEPTH
            * (0.8 + (self.index % 4) * 0.12)
        )

        sum_sq = 0.0
        opp_sq = 0.0
        error_sum = 0.0

        for n in range(count):
            p = self.phase + omega * n

            rp = (
                self.rotor_phase
                + rotor_rate
                * (
                    elapsed
                    + n / float(sample_rate)
                )
                * 2.0 * math.pi
            )

            rotor_gain = (
                1.0 - depth
                + depth
                * (
                    0.5
                    + 0.5 * math.sin(rp)
                )
            )

            sample = (
                0.72 * math.sin(p)
                + 0.20 * math.sin(
                    2.0 * p + self.index * 0.11
                )
                + 0.08 * math.sin(
                    3.0 * p + self.index * 0.23
                )
            ) * rotor_gain

            # Full polarity inversion with configurable amplification.
            opp = -sample * OPPOSITION_AMPLIFICATION

            original.append(sample)
            opposite.append(opp)

            sum_sq += sample * sample
            opp_sq += opp * opp

            error_sum += abs(
                sample
                + opp / OPPOSITION_AMPLIFICATION
            )

        self.phase = (
            self.phase + omega * count
        ) % (2.0 * math.pi)

        self.rotor_phase = (
            self.rotor_phase
            + rotor_rate * count / float(sample_rate)
        ) % (2.0 * math.pi)

        self.rms = math.sqrt(
            sum_sq / max(1, count)
        )

        self.opposition_rms = math.sqrt(
            opp_sq / max(1, count)
        )

        self.activity = min(
            1.0,
            self.rms * 1.8
        )

        mean_error = error_sum / max(1, count)

        self.opposition_score = max(
            0.0,
            min(1.0, 1.0 - mean_error)
        )

        # Exponential local learning of sector levels.
        self.learned_rms += LEARNING_RATE * (
            self.rms - self.learned_rms
        )

        self.learned_opposition += LEARNING_RATE * (
            self.opposition_rms
            - self.learned_opposition
        )

        self.samples_seen += count

        return original, opposite


# ------------------------------------------------------------
# Whole-scope mixer and local learning state
# ------------------------------------------------------------

class WholeScopeLearningEngine:

    def __init__(self):
        self.sectors = [
            SectorRotor(i)
            for i in range(SECTOR_COUNT)
        ]

        self.writer = ContinuousWavWriter(WAV_PATH)

        self.recording = False
        self.total_samples_generated = 0
        self.learning_cycles = 0

        self.last_mix_rms = 0.0
        self.last_opposition_rms = 0.0
        self.overall_score = 0.0
        self.last_save = 0.0
        self.message = 'Ready'

    def start(self):
        if self.recording:
            return

        self.writer.start()
        self.recording = True
        self.message = 'LOCAL WAV LEARNING ACTIVE'

    def stop(self):
        if not self.recording:
            return

        self.recording = False
        self.writer.stop()
        self.save_state()

        self.message = (
            'WAV ERROR: ' + self.writer.error
            if self.writer.error
            else 'WAV FINALIZED'
        )

    def toggle(self):
        if self.recording:
            self.stop()
        else:
            self.start()

    def process(self, count, sample_rate, elapsed):
        if count <= 0:
            return

        left_mix = [0.0] * count
        right_mix = [0.0] * count
        score_sum = 0.0

        # Process every sector for each audio block.
        for sector in self.sectors:
            original, opposite = sector.next_block(
                count,
                sample_rate,
                elapsed
            )

            score_sum += sector.opposition_score

            for i in range(count):
                left_mix[i] += (
                    original[i] / SECTOR_COUNT
                )

                right_mix[i] += (
                    opposite[i] / SECTOR_COUNT
                )

        peak = max(
            max(
                (abs(v) for v in left_mix),
                default=0.0
            ),
            max(
                (abs(v) for v in right_mix),
                default=0.0
            )
        )

        normalizer = (
            0.95 / peak
            if peak > 0.95
            else 1.0
        )

        pcm = bytearray()
        left_sq = 0.0
        right_sq = 0.0

        for left, right in zip(
            left_mix,
            right_mix
        ):
            left = max(
                -OUTPUT_LIMIT,
                min(
                    OUTPUT_LIMIT,
                    left * MASTER_GAIN * normalizer
                )
            )

            right = max(
                -OUTPUT_LIMIT,
                min(
                    OUTPUT_LIMIT,
                    right * MASTER_GAIN * normalizer
                )
            )

            left_sq += left * left
            right_sq += right * right

            pcm.extend(
                int(left * 32767.0).to_bytes(
                    2,
                    byteorder='little',
                    signed=True
                )
            )

            pcm.extend(
                int(right * 32767.0).to_bytes(
                    2,
                    byteorder='little',
                    signed=True
                )
            )

        self.last_mix_rms = math.sqrt(
            left_sq / max(1, count)
        )

        self.last_opposition_rms = math.sqrt(
            right_sq / max(1, count)
        )

        self.overall_score = (
            score_sum / max(1, len(self.sectors))
        )

        self.total_samples_generated += count
        self.learning_cycles += 1

        if self.recording:
            self.writer.submit(bytes(pcm))

        now = time.time()

        if now - self.last_save >= 5.0:
            self.save_state()
            self.last_save = now

    def save_state(self):
        try:
            os.makedirs(
                APP_FOLDER,
                exist_ok=True
            )

            state = {
                'saved_at_unix': time.time(),
                'mode': 'local synthetic audio learning model',
                'sample_rate': SAMPLE_RATE,
                'channels': CHANNELS,
                'wav_path': WAV_PATH,
                'recording': self.recording,
                'total_samples_generated': (
                    self.total_samples_generated
                ),
                'learning_cycles': self.learning_cycles,
                'opposition_amplification': (
                    OPPOSITION_AMPLIFICATION
                ),
                'rotor_speed': ROTOR_SPEED,
                'rotor_depth': ROTOR_DEPTH,

                'sectors': [
                    {
                        'sector': s.index + 1,
                        'frequency_hz': round(
                            s.frequency, 3
                        ),
                        'rms': round(s.rms, 6),
                        'opposition_rms': round(
                            s.opposition_rms, 6
                        ),
                        'learned_rms': round(
                            s.learned_rms, 6
                        ),
                        'learned_opposition': round(
                            s.learned_opposition, 6
                        ),
                        'opposition_score': round(
                            s.opposition_score, 6
                        ),
                        'samples_seen': s.samples_seen,
                    }
                    for s in self.sectors
                ],
            }

            with open(STATE_PATH, 'w') as f:
                json.dump(
                    state,
                    f,
                    indent=2
                )

        except Exception as exc:
            self.message = (
                'STATE SAVE ERROR: ' + str(exc)
            )


# ------------------------------------------------------------
# Scope UI
# ------------------------------------------------------------

class LBandWholeScope(Scene):

    def setup(self):
        self.background_color = (
            0.025,
            0.035,
            0.075
        )

        self.engine = WholeScopeLearningEngine()
        self.engine.start()

        self.elapsed = 0.0
        self.last_update = time.time()
        self.sample_accumulator = 0.0
        self.selected_sector = 0

    def update(self):
        now = time.time()

        dt = max(
            0.0,
            min(0.1, now - self.last_update)
        )

        self.last_update = now
        self.elapsed += dt

        self.sample_accumulator += (
            dt * SAMPLE_RATE
        )

        while (
            self.sample_accumulator
            >= WAV_BLOCK_SAMPLES
        ):
            self.sample_accumulator -= (
                WAV_BLOCK_SAMPLES
            )

            self.engine.process(
                WAV_BLOCK_SAMPLES,
                SAMPLE_RATE,
                self.elapsed
            )

    def draw(self):
        w, h = self.size.w, self.size.h

        cx = w * 0.5
        cy = h * 0.53

        radius = min(
            w * 0.39,
            h * 0.34
        )

        self._draw_background(w, h)
        self._draw_scope(cx, cy, radius)
        self._draw_selected_panel(w, h)
        self._draw_footer(w, h)

    def _draw_background(self, w, h):
        no_fill()
        stroke(0.10, 0.22, 0.32, 0.7)
        stroke_weight(1)

        for i in range(1, 7):
            r = min(w, h) * i / 14.0

            ellipse(
                w * 0.5 - r,
                h * 0.53 - r,
                2 * r,
                2 * r
            )

        line(
            0,
            h * 0.53,
            w,
            h * 0.53
        )

        line(
            w * 0.5,
            0,
            w * 0.5,
            h
        )

    def _draw_scope(self, cx, cy, radius):
        no_fill()
        stroke(0.20, 0.65, 0.85, 0.85)
        stroke_weight(1.5)

        ellipse(
            cx - radius,
            cy - radius,
            radius * 2,
            radius * 2
        )

        ellipse(
            cx - radius * 0.70,
            cy - radius * 0.70,
            radius * 1.40,
            radius * 1.40
        )

        ellipse(
            cx - radius * 0.38,
            cy - radius * 0.38,
            radius * 0.76,
            radius * 0.76
        )

        sweep = (
            self.elapsed
            * ROTOR_SPEED
            * 2.0 * math.pi
        )

        sx = cx + math.cos(sweep) * radius
        sy = cy + math.sin(sweep) * radius

        stroke(0.25, 0.85, 0.70, 0.75)
        stroke_weight(2)

        line(
            cx,
            cy,
            sx,
            sy
        )

        for sector in self.engine.sectors:
            a = sector.angle

            x = (
                cx
                + math.cos(a) * radius * 0.84
            )

            y = (
                cy
                + math.sin(a) * radius * 0.84
            )

            rotor_r = 8 + 9 * sector.activity

            # Opposing radial vector.
            ox = (
                cx
                + math.cos(a + math.pi)
                * radius
                * (
                    0.68
                    + 0.10 * sector.opposition_score
                )
            )

            oy = (
                cy
                + math.sin(a + math.pi)
                * radius
                * (
                    0.68
                    + 0.10 * sector.opposition_score
                )
            )

            stroke(1.0, 0.28, 0.72, 0.65)
            stroke_weight(1)

            line(
                x,
                y,
                ox,
                oy
            )

            no_stroke()

            if sector.index == self.selected_sector:
                fill(
                    1.0,
                    0.88,
                    0.25,
                    1.0
                )
            else:
                fill(
                    0.20,
                    0.72,
                    0.98,
                    0.9
                )

            ellipse(
                x - rotor_r,
                y - rotor_r,
                rotor_r * 2,
                rotor_r * 2
            )

            rotor_angle = (
                sector.rotor_phase * 2.0 * math.pi
            )

            stroke(1.0, 0.40, 0.78, 1.0)
            stroke_weight(2)

            line(
                x,
                y,
                x + math.cos(rotor_angle) * rotor_r * 1.8,
                y + math.sin(rotor_angle) * rotor_r * 1.8
            )

            # Bitmap labels: no calls to scene.text().
            draw_label(
                sector.index + 1,
                x,
                y - rotor_r - 13,
                11
            )

        no_stroke()
        fill(
            1.0,
            0.85,
            0.25,
            0.95
        )

        ellipse(
            cx - 6,
            cy - 6,
            12,
            12
        )

        fill(
            0.85,
            0.94,
            1.0,
            1.0
        )

        draw_label(
            'L-BAND ROTOR MODEL',
            cx,
            cy - radius - 25,
            13
        )

    def _draw_selected_panel(self, w, h):
        sector = self.engine.sectors[
            self.selected_sector
        ]

        left = 12
        top_y = h - 54

        fill(
            0.86,
            0.94,
            1.0,
            1.0
        )

        draw_label(
            'WHOLE-SCOPE OPPOSITION LEARNING',
            left + 150,
            top_y,
            15
        )

        fill(
            0.30,
            0.82,
            1.0,
            1.0
        )

        draw_label(
            'SECTOR %02d | %.1f Hz | rotor %.2f'
            % (
                sector.index + 1,
                sector.frequency,
                ROTOR_SPEED
            ),
            left + 145,
            top_y - 21,
            12
        )

        fill(
            1.0,
            0.43,
            0.78,
            1.0
        )

        draw_label(
            'OPPOSITION -1 polarity | amplification x%.2f'
            % OPPOSITION_AMPLIFICATION,
            left + 165,
            top_y - 39,
            11
        )

        fill(
            0.85,
            0.90,
            1.0,
            1.0
        )

        draw_label(
            'Sector RMS %.4f | learned %.4f'
            % (
                sector.rms,
                sector.learned_rms
            ),
            left + 125,
            top_y - 56,
            10
        )

        draw_label(
            'Opposition RMS %.4f | learned %.4f'
            % (
                sector.opposition_rms,
                sector.learned_opposition
            ),
            left + 145,
            top_y - 71,
            10
        )

    def _draw_footer(self, w, h):
        engine = self.engine

        fill(
            0.90,
            0.96,
            1.0,
            1.0
        )

        draw_label(
            'LOCAL LEARNING: %s'
            % (
                'ON'
                if engine.recording
                else 'PAUSED'
            ),
            95,
            45,
            12
        )

        draw_label(
            'Opposition accuracy %.1f%% | sectors %d | cycles %d'
            % (
                engine.overall_score * 100.0,
                SECTOR_COUNT,
                engine.learning_cycles
            ),
            w * 0.49,
            27,
            11
        )

        draw_label(
            'L RMS %.3f | R RMS %.3f'
            % (
                engine.last_mix_rms,
                engine.last_opposition_rms
            ),
            95,
            10,
            10
        )

        button_w = 112
        button_h = 30

        bx = w - button_w - 12
        by = 12

        no_stroke()

        if engine.recording:
            fill(
                0.15,
                0.55,
                0.38,
                0.95
            )
        else:
            fill(
                0.60,
                0.20,
                0.24,
                0.95
            )

        rect(
            bx,
            by,
            button_w,
            button_h
        )

        fill(
            1.0,
            1.0,
            1.0,
            1.0
        )

        draw_label(
            (
                'RECORDING'
                if engine.recording
                else 'START WAV'
            ),
            bx + button_w / 2,
            by + button_h / 2,
            11
        )

        fill(
            0.72,
            0.81,
            0.90,
            1.0
        )

        draw_label(
            os.path.basename(WAV_PATH),
            w * 0.5,
            h - 77,
            9
        )

        if engine.writer.error:
            fill(
                1.0,
                0.25,
                0.25,
                1.0
            )

            draw_label(
                'WAV ERROR: ' + engine.writer.error,
                w * 0.5,
                h - 93,
                9
            )

        elif engine.writer.dropped_blocks:
            fill(
                1.0,
                0.70,
                0.25,
                1.0
            )

            draw_label(
                'Writer queue drops: %d'
                % engine.writer.dropped_blocks,
                w * 0.5,
                h - 93,
                9
            )

    def touch_began(self, touch):
        x = touch.location.x
        y = touch.location.y

        w = self.size.w
        h = self.size.h

        # Tap lower-right recording button to stop or restart WAV.
        if x > w - 135 and y < 55:
            self.engine.toggle()
            return

        # Tap near a rotor to select that sector.
        cx = w * 0.5
        cy = h * 0.53

        radius = min(
            w * 0.39,
            h * 0.34
        )

        nearest_index = None
        nearest_distance = None

        for sector in self.engine.sectors:
            sx = (
                cx
                + math.cos(sector.angle)
                * radius * 0.84
            )

            sy = (
                cy
                + math.sin(sector.angle)
                * radius * 0.84
            )

            distance = (
                (x - sx) ** 2
                + (y - sy) ** 2
            )

            if (
                nearest_distance is None
                or distance < nearest_distance
            ):
                nearest_distance = distance
                nearest_index = sector.index

        if (
            nearest_index is not None
            and nearest_distance < (radius * 0.45) ** 2
        ):
            self.selected_sector = nearest_index

    def stop(self):
        self.engine.stop()


# ------------------------------------------------------------
# Run the scope
# ------------------------------------------------------------

if __name__ == '__main__':
    run(
        LBandWholeScope(),
        show_fps=False
    )
