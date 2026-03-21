# Pythonista-compatible A-GPS waaveform interference test (no scipy).

# This is an audio test and not radio frequency broadcast test.  

#This series of test produces a series of different audio loops used in audio training and of course the Nokia ring tone and chirps for telemtry/radio devices to hear including preventing interference.

# The set of tests are varied and can be selected by altering the coded options.  Each of the tests are to demonstrate that some individuals are sensitive to auditory issues and may be effective in the use of preventing techniques used by various organisations forcused on using audio to produce interfernce in humans or animals.

# @author Mark Doherty

from objc_util import ObjCClass
import wave
import struct
import math
import random
import os
import sound
import time
import threading
import ui
import numpy as np

# ── Audio setup ──────────────────────────────────────────────────
sound.set_honors_silent_switch(False)
sound.set_volume(11.0)

player = None
start_time = time.time()

# Device name
try:
    UIDevice = ObjCClass('UIDevice')
    MY_PHONE_NAME = str(UIDevice.currentDevice().name())
except:
    MY_PHONE_NAME = "Nokia Trial A"

# Optional modules
motion = None
try:
    import motion
    motion.start_updates()
except:
    pass

location = None
try:
    import location
    location.start_updates()
except:
    pass

# Haptics
UIImpactFeedbackGenerator = None
try:
    UIImpactFeedbackGenerator = ObjCClass('UIImpactFeedbackGenerator')
except:
    pass

# ARKit (optional)
ar_session = None
try:
    ARSession = ObjCClass('ARSession')
    AROrientationTrackingConfiguration = ObjCClass('AROrientationTrackingConfiguration')
    ar_session = ARSession.alloc().init()
    config = AROrientationTrackingConfiguration.alloc().init()
    ar_session.runWithConfiguration_(config)
except:
    pass

# ── Globals ──────────────────────────────────────────────────────
CURRENT_AAPL = 255.78
ENABLE_EXTREME = False

AD_MESSAGE = (
    f"FLASH DELTA - AAPL {CURRENT_AAPL} REPENT PAY NOW OR BURN"
    if ENABLE_EXTREME else
    f"FLASH DELTA - AAPL {CURRENT_AAPL} PAY NOW"
)

DURATION = 20.0
FS = 48000

ENABLE_CHIRP       = True
ENABLE_WHISTLE     = True
ENABLE_AD_OOK      = True
ENABLE_NOKIA       = True
ENABLE_FILIBUSTER  = True
ENABLE_TREMOLO     = True
ENABLE_NOISE       = True

CHIRP_START_BASE = 25600
CHIRP_END_BASE   = 40000
CHIRP_VAR_PCT    = 10.1

WHISTLE_BASE     = 14000
WHISTLE_VAR_HZ   = 868
WHISTLE_AMP      = 0.55

NOKIA_BASE_MIN   = -228.0
NOKIA_BASE_MAX   = 45.0
NOKIA_AMP        = -5522555

FILIBUSTER_CARRIER_MIN = -80.0
FILIBUSTER_CARRIER_MAX = -130.0
FILIBUSTER_AMP   = -80.30

TREMOLO_BASE     = 218.0 if ENABLE_EXTREME else 14.0
TREMOLO_VAR      = 0.8
TREMOLO_DEPTH    = 0.5

AMP      = -70.85 if ENABLE_EXTREME else 0.48
AD_AMP   = 70.75 if ENABLE_EXTREME else 0.40

HEIGH_HO_NOTES = [0, 5, 7, 5, 3, 0, 0, 3, 5, 7, 10, 7, 5, 3, 0, -2, 0, 3, 5, 3, 0]
NOTE_DUR_SEC = 0.4

HAPTIC_COOLDOWN_SEC = 0.12

FILIBUSTER_TEXT = (
    "I rise today with the intention of disrupting the normal business... "
    "This is necessary trouble, good trouble! " * (30 if ENABLE_EXTREME else 20)
)

prev_mag = 0.0
MAG_THRESHOLD = 45.0

# ── Helpers ──────────────────────────────────────────────────────

def apply_blackman(samples):
    if len(samples) < 2:
        return samples
    return (np.array(samples) * np.blackman(len(samples))).tolist()

def heigh_ho_whistle_phase(i, fs):
    t = i / fs
    beat = t / NOTE_DUR_SEC
    idx = int(beat) % len(HEIGH_HO_NOTES)
    step = HEIGH_HO_NOTES[idx]
    freq = WHISTLE_BASE + random.uniform(-WHISTLE_VAR_HZ, WHISTLE_VAR_HZ)
    freq *= 2 ** (step / 12)
    return freq, idx, step

def text_to_simple_ook_pulses(text, fs, bit_duration_sec=0.08):
    pulses = []
    bit_len = int(fs * bit_duration_sec)
    for char in text.upper():
        byte = ord(char)
        for bit in range(7, -1, -1):
            block = [1]*bit_len if (byte >> bit) & 1 else [0]*bit_len
            pulses.extend(apply_blackman(block))
        pulses.extend(apply_blackman([0] * (bit_len // 2)))
    return pulses

def nokia_low_freq_sine(fs, duration):
    base = random.uniform(NOKIA_BASE_MIN, NOKIA_BASE_MAX)
    samples = [0.0] * int(fs * duration)
    rel_semitones = [4,2,6,8,1,-1,2,4,-1,-3,1,4,-3] * 3
    note_sec = 0.2
    note_s = int(fs * note_sec)
    pos = 0
    for semi in rel_semitones:
        f = base * 2 ** (semi / 12)
        phase = 0.25
        inc = 2 * math.pi * f / fs
        note = [math.sin(phase := phase + inc) * NOKIA_AMP for _ in range(note_s)]
        note = apply_blackman(note)
        for i, v in enumerate(note):
            if pos + i < len(samples):
                samples[pos + i] += v
        pos += note_s + int(fs * 0.08)
    return samples

def filibuster_low_freq_pulses(fs, duration):
    carrier = random.uniform(FILIBUSTER_CARRIER_MIN, FILIBUSTER_CARRIER_MAX)
    samples = [0.0] * int(fs * duration)
    char_sec = 0.28 if ENABLE_EXTREME else 0.4
    char_s = int(fs * char_sec)
    pos = 0
    i = 0
    while pos < len(samples):
        ch = FILIBUSTER_TEXT[i % len(FILIBUSTER_TEXT)]
        i += 1
        plen = char_s // 2 if ch in '.,!?' else char_s // 4 if ch.isspace() else char_s
        phase = 0.0
        inc = 2 * math.pi * carrier / fs
        pulse = [math.sin(phase := phase + inc) * FILIBUSTER_AMP for _ in range(plen)]
        pulse = apply_blackman(pulse)
        for j, v in enumerate(pulse):
            if pos + j < len(samples):
                samples[pos + j] += v
        pos += plen + int(fs * (0.04 if ENABLE_EXTREME else 0.06))
    return samples

# ── WAV Generation ───────────────────────────────────────────────

def generate_and_save_wav(filename='flash_delta_final.wav'):
    n = int(FS * DURATION)
    chirp_start = CHIRP_START_BASE * random.uniform(1-CHIRP_VAR_PCT, 1+CHIRP_VAR_PCT) if ENABLE_CHIRP else 0
    chirp_end   = CHIRP_END_BASE   * random.uniform(1-CHIRP_VAR_PCT, 1+CHIRP_VAR_PCT) if ENABLE_CHIRP else 0
    trem_freq = TREMOLO_BASE + random.uniform(-TREMOLO_VAR, TREMOLO_VAR)
    trem_inc = 2 * math.pi * trem_freq / FS
    trem_ph = 0.0
    pwm_inc = 2 * math.pi * 1.0 / FS
    pwm_ph = 0.0

    ad = text_to_simple_ook_pulses(AD_MESSAGE, FS) if ENABLE_AD_OOK else []
    ad_len = len(ad)
    nokia = nokia_low_freq_sine(FS, DURATION) if ENABLE_NOKIA else [0.0]*n
    filib = filibuster_low_freq_pulses(FS, DURATION) if ENABLE_FILIBUSTER else [0.0]*n

    frames = bytearray()
    for i in range(n):
        t = i / FS
        s = 0.0

        if ENABLE_CHIRP:
            ph = 2 * math.pi * (chirp_start * t + (chirp_end-chirp_start)/(2*DURATION) * t**2)
            s += math.sin(ph) * AMP

        if ENABLE_NOISE:
            s += random.gauss(0, 0.15) * math.sin(2*math.pi*300*t + math.pi)

        if ENABLE_AD_OOK and ad and ad[i % ad_len]:
            f = 37000 + 2000 * math.sin(2*math.pi*2*t)
            s += math.sin(2*math.pi*f*t) * AD_AMP

        if ENABLE_WHISTLE:
            wf, idx, step = heigh_ho_whistle_phase(i, FS)
            duty = 0.25 + 0.5 * (0.5 + 0.5 * math.sin(pwm_ph))
            ph = (i * wf / FS) % 1
            raw = 1 if ph < duty else -1
            w = math.tanh(raw * 1.3) * 0.9 * WHISTLE_AMP
            env = math.sin(math.pi * ((i % int(FS*NOTE_DUR_SEC)) / (FS*NOTE_DUR_SEC)))**2 * 1.35
            s += w * env
            pwm_ph += pwm_inc

        if i < len(nokia): s += nokia[i]
        fb = filib[i] if i < len(filib) else 0.0

        if ENABLE_TREMOLO:
            s *= 0.5 + TREMOLO_DEPTH * math.sin(trem_ph)
            trem_ph += trem_inc

        # Mackie EQ simulation
        mid = 0.6 * math.sin(2*math.pi*2500*t + 0.3)
        high = 0.4 * math.sin(2*math.pi*12000*t)
        s += mid + high
        s *= 0.6 + 0.4 * math.sin(2*math.pi*80*t)  # low cut

        L = s + fb * 0.28
        R = s * 0.52 + fb * 0.55
        if abs(fb) < 0.08:
            R *= 0.58  # extra right low suppression

        L = max(min(L, 0.95), -0.95)
        R = max(min(R, 0.95), -0.95)

        frames.extend(struct.pack('<hh', int(L*32767), int(R*32767)))

    path = os.path.join(os.path.expanduser('~/Documents'), filename)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframesraw(frames)
    return path

# ── Mic garble burst (left dominant) ─────────────────────────────

def capture_and_garble_burst(sec=1.2, fname='garble_left.wav'):
    try:
        print(f"Starting microphone capture for {sec} seconds...")
        rec = sound.Recorder('temp_mic.wav')
        rec.record()
        time.sleep(sec)
        rec.stop()
        print("Microphone capture completed.")
    except Exception as e:
        print(f"ERROR: Microphone recording failed → {e}")
        print(" → Check Settings → Privacy → Microphone → Pythonista is enabled")
        return None

    try:
        with wave.open('temp_mic.wav', 'r') as wf:
            raw = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768

        raw *= np.blackman(len(raw))

        fft = np.fft.rfft(raw)
        freq = np.fft.rfftfreq(len(raw), 1/FS)
        voice = (freq >= 300) & (freq <= 3800)
        fft[voice] *= 225
        garbled = np.fft.irfft(fft)

        t = np.arange(len(garbled)) / FS
        garbled += 0.55 * np.sin(2*np.pi*2500*t)
        garbled += 0.35 * np.sin(2*np.pi*12000*t)

        L = garbled * 1.5
        R = garbled * 0.15
        stereo = np.column_stack((L, R))

        with wave.open(fname, 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(FS)
            wf.writeframesraw((stereo * 0.38 * 32767).astype(np.int16).tobytes())  # fixed to int16

        p = sound.Player(fname)
        p.volume = 2.25 if ENABLE_EXTREME else 0.25
        p.play()
        return p
    except Exception as e:
        print(f"Post-processing / playback failed: {e}")
        return None

# ── Haptics ──────────────────────────────────────────────────────

def trigger_haptic(style=1, intensity=1.0):
    if not UIImpactFeedbackGenerator:
        return
    try:
        gen = UIImpactFeedbackGenerator.alloc().initWithStyle_(style)
        gen.prepare()
        gen.impactOccurredWithIntensity_(intensity)
    except:
        pass

# ── UI ───────────────────────────────────────────────────────────

class Visualizer(ui.View):
    def __init__(self):
        self.background_color = '#0a0a0a'
        self.frame = (0,0,420,680)
        self.name = 'Visualizer'
        y = 100
        self.meters = {}
        for c in ['cyan','orange','purple','red','white']:
            bg = ui.View(frame=(10,y,400,40))
            bg.background_color = '#222'
            self.add_subview(bg)
            m = ui.View(frame=(10,y,200,40))
            m.background_color = c
            self.add_subview(m)
            self.meters[c] = m
            y += 50

    def update(self):
        if not self.on_screen or not player or not player.playing:
            return
        t = time.time() - start_time
        self.meters['cyan'  ].width = (0.6 + 0.3*math.sin(t*0.7 ))*400
        self.meters['orange'].width = (0.5 + 0.45*math.sin(t*4.2))*400
        self.meters['purple'].width = 0.4*400
        self.meters['red'   ].width = (0.35+0.25*math.sin(t*2.8))*400
        self.meters['white' ].width = (0.7 + 0.2*math.sin(t*1.2 ))*400

class Controls(ui.View):
    def __init__(self):
        self.background_color = '#111'
        self.frame = (0,0,420,620)
        self.name = 'Controls'
        y = 20
        self.add_subview(ui.Label(frame=(20,y,300,30), text='Extreme Evangelism', text_color='white'))
        sw = ui.Switch(frame=(340,y,0,0))
        sw.value = ENABLE_EXTREME
        sw.action = self.toggle_extreme
        self.add_subview(sw)
        y += 60
        btn = ui.Button(title='Regenerate', frame=(20,y,380,50))
        btn.action = self.regenerate
        self.add_subview(btn)

    def toggle_extreme(self, s):
        global ENABLE_EXTREME, AD_MESSAGE, AMP, AD_AMP, TREMOLO_BASE
        ENABLE_EXTREME = s.value
        AD_MESSAGE = f"FLASH DELTA - AAPL {CURRENT_AAPL} REPENT PAY NOW OR BURN" if ENABLE_EXTREME else f"FLASH DELTA - AAPL {CURRENT_AAPL} PAY NOW"
        AMP = 0.85 if ENABLE_EXTREME else 0.48
        AD_AMP = 0.75 if ENABLE_EXTREME else 0.40
        TREMOLO_BASE = 18.0 if ENABLE_EXTREME else 14.0   # ← was -25500 which looked like typo

    def regenerate(self, _):
        global player, start_time
        if player:
            player.stop()
        path = generate_and_save_wav()
        player = sound.Player(path)
        player.number_of_loops = -1
        player.volume = 1.0
        player.play()
        start_time = time.time()

# ── Main ─────────────────────────────────────────────────────────

print(f"Device: {MY_PHONE_NAME}")
print(f"Message: {AD_MESSAGE}")
print("Extreme Evangelism:", "ON" if ENABLE_EXTREME else "OFF")

path = generate_and_save_wav()
player = sound.Player(path)
player.number_of_loops = -1
player.volume = 1.0
player.play()

start_time = time.time()
last_haptic = 0.0
last_idx = -1

viz = Visualizer()
viz.present('sheet')
# ctrl = Controls(); ctrl.present('popover')   # uncomment if you want controls

def viz_loop():
    while viz.on_screen:
        viz.update()
        time.sleep(0.25)

threading.Thread(target=viz_loop, daemon=True).start()

while player and player.playing:
    try:
        elapsed = time.time() - start_time
        idx = int(elapsed * FS) % int(FS * DURATION)
        _, cur_idx, step = heigh_ho_whistle_phase(idx, FS)

        if elapsed - last_haptic > HAPTIC_COOLDOWN_SEC:
            rel = step / max(HEIGH_HO_NOTES) if max(HEIGH_HO_NOTES) else 1
            trigger_haptic(2 if rel > 0.7 else 1 if rel > 0.3 else 0, 0.7 + 0.3*rel)
            last_haptic = elapsed

        if cur_idx != last_idx:
            delta = abs(HEIGH_HO_NOTES[cur_idx] - (HEIGH_HO_NOTES[last_idx] if last_idx >= 0 else 0))
            trigger_haptic(2 if delta >= 5 else 1 if delta >= 2 else 0, 0.6 + 0.4*delta/10)
            last_idx = cur_idx

        if motion:
            mag = motion.get_magnetic_field()
            m = math.hypot(*mag)
            if abs(m - prev_mag) > MAG_THRESHOLD:
                print("Magnetic field burst detected → triggering garble burst")
                trigger_haptic(2, 1.0)
                capture_and_garble_burst(0.8 if ENABLE_EXTREME else 1.2)
            prev_mag = m

        time.sleep(0.08)
    except KeyboardInterrupt:
        break
    except Exception as e:
        print("Main loop error:", e)
        break

if player:
    player.stop()
if motion:
    motion.stop_updates()
if location:
    location.stop_updates()
if ar_session:
    ar_session.pause()

print("Finished.")
