from objc_util import ObjCClass
import wave
import struct
import math
import random
import os
import sound
import time
import threading
import urllib.request
import re
import ui

# ── Try to read real device name (with fallback) ─────────────────
try:
    UIDevice = ObjCClass('UIDevice')
    MY_PHONE_NAME = str(UIDevice.currentDevice().name())
    print(f"Device name read successfully: {MY_PHONE_NAME}")
except Exception as e:
    print(f"Could not read device name: {e}")
    MY_PHONE_NAME = "My iPhone"
    print(f"Using fallback name: {MY_PHONE_NAME}")

# ── Optional sensor/location imports ─────────────────────────────
try:
    import motion
except ImportError:
    motion = None
    print("motion module not available – skipping Core Motion")

try:
    import location
except ImportError:
    location = None
    print("location module not available – skipping GPS / geo-location")

# ── Haptics support ───────────────────────────────────────────────
try:
    UIImpactFeedbackGenerator = ObjCClass('UIImpactFeedbackGenerator')
except:
    UIImpactFeedbackGenerator = None
    print("Haptics not available")

# ── ARKit classes ────────────────────────────────────────────────
ARSession = None
AROrientationTrackingConfiguration = None
try:
    ARSession = ObjCClass('ARSession')
    AROrientationTrackingConfiguration = ObjCClass('AROrientationTrackingConfiguration')
    print("ARKit classes loaded")
except Exception as e:
    print(f"ARKit not available: {e}")

ar_session = None

def start_arkit():
    global ar_session
    if ARSession is None or AROrientationTrackingConfiguration is None:
        return False
    try:
        ar_session = ARSession.alloc().init()
        config = AROrientationTrackingConfiguration.alloc().init()
        ar_session.runWithConfiguration_(config)
        print("ARKit orientation tracking started")
        return True
    except Exception as e:
        print(f"ARKit start failed: {e}")
        return False

def get_arkit_motion():
    if ar_session is None:
        return None
    try:
        frame = ar_session.currentFrame()
        if frame is None or frame.camera is None:
            return None
        
        transform = frame.camera.transform()
        
        m11, m12, m13 = transform.m11, transform.m12, transform.m13
        m23, m33 = transform.m23, transform.m33
        
        yaw   = math.atan2(m12, m11)
        pitch = math.asin(-m13)
        roll  = math.atan2(m23, m33)
        
        pos_x = transform.m41
        pos_y = transform.m42
        pos_z = transform.m43
        
        return {
            'yaw_deg':   math.degrees(yaw),
            'pitch_deg': math.degrees(pitch),
            'roll_deg':  math.degrees(roll),
            'position':  (pos_x, pos_y, pos_z),
            'state':     frame.camera.trackingState
        }
    except Exception as e:
        print(f"ARKit frame error: {e}")
        return None

# ── Fetch latest AAPL price from Yahoo Finance ───────────────────
def get_current_aapl_price():
    fallback = 273.68
    try:
        url = "https://finance.yahoo.com/quote/AAPL"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            match = re.search(r'(\d{1,3}(?:,\d{3})*\.\d{2})', html)
            if match:
                price_str = match.group(1).replace(',', '')
                price = float(price_str)
                if 100 < price < 500:
                    return round(price, 2)
        print("Price parse failed – using fallback")
    except Exception as e:
        print(f"Price fetch failed: {e} – using fallback")
    return fallback

CURRENT_AAPL = get_current_aapl_price()
AD_MESSAGE = f"FLASH DELTA - AAPL {CURRENT_AAPL} PAY NOW"
print(f"Using AAPL price: {CURRENT_AAPL}")

# ── Config ───────────────────────────────────────────────────────
DURATION = 20.0
FS = 192000

CHIRP_START_BASE = 25000
CHIRP_END_BASE   = 40000
CHIRP_VAR_PCT    = 0.12

WHISTLE_BASE     = 14000
WHISTLE_VAR_HZ   = 900
WHISTLE_AMP      = 0.55

NOKIA_BASE_MIN   = 28.0
NOKIA_BASE_MAX   = 42.0
NOKIA_AMP        = 0.20

FILIBUSTER_CARRIER_MIN = 80.0
FILIBUSTER_CARRIER_MAX = 130.0
FILIBUSTER_AMP   = 0.30

TREMOLO_BASE     = 14.0
TREMOLO_VAR      = 0.8
TREMOLO_DEPTH    = 0.5

AMP, AD_AMP = 0.48, 0.40
ADD_NOISE = True

HEIGH_HO_NOTES = [0, 5, 7, 5, 3, 0, 0, 3, 5, 7, 10, 7, 5, 3, 0, -2, 0, 3, 5, 3, 0]
NOTE_DUR_SEC = 0.4

PWM_MIN_DUTY = 0.25
PWM_MAX_DUTY = 0.75
PWM_MOD_FREQ = 1.0

HAPTIC_COOLDOWN_SEC = 0.12

FILIBUSTER_TEXT = (
    "I rise today with the intention of disrupting the normal business of the United States Senate for as long as I am physically able. "
    "These are not normal times in America, and they should not be treated as such in the United States Senate. "
    "We are witnessing threats to democracy, to our institutions, to our communities, to the rule of law itself. "
    "I am here to give voice to those who are being harmed, to those who have no recourse, to those who are afraid. "
    "This is not about politics — this is about the soul of America. "
    "How much more will we take? How much more will we allow? "
    "I will not yield the floor until I have said what needs to be said. "
    "The limits of tyranny are prescribed by the endurance of those who are oppressed. "
    "We must stand up, we must speak out, we must resist. "
    "I will keep speaking, I will keep going, this is necessary trouble, good trouble! "
    "We are in a moment of moral crisis. The question is not what will happen to us, but what we will do about it. "
    "This is not normal. This is not acceptable. This is not America. " * 20
)

# ── Helpers ──────────────────────────────────────────────────────
def heigh_ho_whistle_phase(i, fs):
    t_total = i / fs
    beat = t_total / NOTE_DUR_SEC
    motif_len = len(HEIGH_HO_NOTES)
    idx = int(beat) % motif_len
    step = HEIGH_HO_NOTES[idx]
    freq_offset = random.uniform(-WHISTLE_VAR_HZ, WHISTLE_VAR_HZ)
    freq = WHISTLE_BASE + freq_offset
    freq *= (2 ** (step / 12.0))
    return freq, idx, step

def text_to_simple_ook_pulses(text, fs, bit_duration_sec=0.08):
    pulses = []
    bit_len = int(fs * bit_duration_sec)
    for char in text.upper():
        byte = ord(char)
        for bit in range(7, -1, -1):
            pulses.extend([1] * bit_len if (byte >> bit) & 1 else [0] * bit_len)
        pulses.extend([0] * (bit_len // 2))
    return pulses

def nokia_low_freq_sine(fs, duration):
    base_freq = random.uniform(NOKIA_BASE_MIN, NOKIA_BASE_MAX)
    num_samples = int(fs * duration)
    samples = [0.0] * num_samples
    
    rel_semitones = [4, 2, 6, 8, 1, -1, 2, 4, -1, -3, 1, 4, -3] * 3
    
    note_duration_sec = 0.6
    note_samples = int(fs * note_duration_sec)
    
    current_sample = 0
    for semitone in rel_semitones:
        freq = base_freq * (2 ** (semitone / 12.0))
        phase_inc = 2 * math.pi * freq / fs
        phase = 0.0
        
        for s in range(note_samples):
            if current_sample + s >= num_samples:
                break
            samples[current_sample + s] += math.sin(phase) * NOKIA_AMP
            phase += phase_inc
        
        current_sample += note_samples + int(fs * 0.08)
    
    return samples

def filibuster_low_freq_pulses(fs, duration):
    carrier_freq = random.uniform(FILIBUSTER_CARRIER_MIN, FILIBUSTER_CARRIER_MAX)
    num_samples = int(fs * duration)
    samples = [0.0] * num_samples
    
    char_duration_sec = 0.4
    char_samples = int(fs * char_duration_sec)
    
    current_sample = 0
    text_index = 0
    
    while current_sample < num_samples:
        ch = FILIBUSTER_TEXT[text_index % len(FILIBUSTER_TEXT)]
        text_index += 1
        
        if ch in '.,!?':
            pulse_len = char_samples // 2
        elif ch.isspace():
            pulse_len = char_samples // 4
        else:
            pulse_len = char_samples
        
        phase_inc = 2 * math.pi * carrier_freq / fs
        phase = 0.0
        
        for s in range(pulse_len):
            if current_sample + s >= num_samples:
                break
            carrier = math.sin(phase)
            samples[current_sample + s] += carrier * FILIBUSTER_AMP
            phase += phase_inc
        
        current_sample += pulse_len + int(fs * 0.06)
    
    return samples

# ── Generate stereo WAV ──────────────────────────────────────────
def generate_and_save_wav(temp_filename='flash_delta_jammer_stereo.wav'):
    num_samples = int(FS * DURATION)
    print(f"Generating {num_samples:,} samples ({DURATION}s @ {FS/1000} kHz STEREO)...")
    
    chirp_start = CHIRP_START_BASE * random.uniform(1 - CHIRP_VAR_PCT, 1 + CHIRP_VAR_PCT)
    chirp_end   = CHIRP_END_BASE   * random.uniform(1 - CHIRP_VAR_PCT, 1 + CHIRP_VAR_PCT)
    
    tremolo_freq = TREMOLO_BASE + random.uniform(-TREMOLO_VAR, TREMOLO_VAR)
    tremolo_phase_inc = 2 * math.pi * tremolo_freq / FS
    tremolo_phase = 0.0
    
    pwm_lfo_phase_inc = 2 * math.pi * PWM_MOD_FREQ / FS
    pwm_lfo_phase = 0.0
    
    ad_pulses = text_to_simple_ook_pulses(AD_MESSAGE, FS)
    ad_len = len(ad_pulses)
    
    nokia_layer = nokia_low_freq_sine(FS, DURATION)
    filibuster_layer = filibuster_low_freq_pulses(FS, DURATION)
    
    left_frames = bytearray()
    right_frames = bytearray()
    
    for i in range(num_samples):
        t = i / FS
        
        phase_chirp = 2 * math.pi * (chirp_start * t + (chirp_end - chirp_start) / (2 * DURATION) * t**2)
        sample_mono = math.sin(phase_chirp) * AMP
        
        if ADD_NOISE:
            sample_mono += random.gauss(0, 0.15) * math.sin(2 * math.pi * 300 * t + math.pi)
        
        if ad_pulses[i % ad_len]:
            ad_freq = 37000 + 2000 * math.sin(2 * math.pi * 2 * t)
            sample_mono += math.sin(2 * math.pi * ad_freq * t) * AD_AMP
        
        whistle_freq, _, step = heigh_ho_whistle_phase(i, FS)
        
        lfo = math.sin(pwm_lfo_phase)
        duty = PWM_MIN_DUTY + (PWM_MAX_DUTY - PWM_MIN_DUTY) * (0.5 + 0.5 * lfo)
        
        phase = (i * whistle_freq / FS) % 1.0
        whistle_raw = 1.0 if phase < duty else -1.0
        
        whistle = whistle_raw * 1.3
        whistle = math.tanh(whistle) * 0.9
        whistle *= WHISTLE_AMP
        
        env_phase = (i % int(FS * NOTE_DUR_SEC)) / (FS * NOTE_DUR_SEC)
        env = math.sin(math.pi * env_phase) ** 2 * 1.35
        sample_mono += whistle * env
        
        pwm_lfo_phase += pwm_lfo_phase_inc
        
        if i < len(nokia_layer):
            sample_mono += nokia_layer[i]
        
        filibuster = 0.0
        if i < len(filibuster_layer):
            filibuster = filibuster_layer[i]
        
        tremolo = 0.5 + TREMOLO_DEPTH * math.sin(tremolo_phase)
        sample_mono *= tremolo
        
        left  = sample_mono + filibuster * 0.2
        right = sample_mono + filibuster * 1.0
        
        left  = max(min(left,  0.95), -0.95)
        right = max(min(right, 0.95), -0.95)
        
        left_frames.extend(struct.pack('<h', int(left * 32767)))
        right_frames.extend(struct.pack('<h', int(right * 32767)))
        
        tremolo_phase += tremolo_phase_inc
    
    stereo_frames = bytearray()
    for i in range(num_samples):
        stereo_frames.extend(left_frames[i*2:i*2+2])
        stereo_frames.extend(right_frames[i*2:i*2+2])
    
    path = os.path.join(os.path.expanduser('~/Documents'), temp_filename)
    try:
        with wave.open(path, 'wb') as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(FS)
            w.writeframes(stereo_frames)
        print(f"Stereo WAV generated: {path}")
        print(f"  • AAPL: {CURRENT_AAPL}")
        print(f"  • Chirp: ~{int(chirp_start)} → {int(chirp_end)} Hz")
        print(f"  • Tremolo: ~{tremolo_freq:.2f} Hz")
        return path
    except Exception as e:
        print(f"Write error: {e}")
        return None

def trigger_haptic(style=1, intensity=1.0):
    if UIImpactFeedbackGenerator is None:
        return
    try:
        gen = UIImpactFeedbackGenerator.alloc().initWithStyle_(style)
        gen.prepare()
        gen.impactOccurredWithIntensity_(intensity)
    except:
        pass

# ── UI Visualizer (no labels, no text, just animated bars) ───────
class AudioVisualizer(ui.View):
    def __init__(self):
        self.background_color = '#0a0a0a'
        self.frame = (0, 0, 420, 680)
        self.name = "Visualizer"  # minimal title in sheet
        
        # Layer meters (colored ui.View bars only – no labels)
        y = 100
        self.layer_meters = {}
        colors = ['cyan', 'orange', 'purple', 'red', 'white']
        for color in colors:
            bg = ui.View(frame=(10, y, 400, 40))
            bg.background_color = '#222'
            self.add_subview(bg)
            
            meter = ui.View(frame=(10, y, 200, 40))
            meter.background_color = color
            self.add_subview(meter)
            self.layer_meters[color] = meter  # use color as key for simplicity
            
            y += 50
    
    def update(self):
        if not self.on_screen or not player.playing:
            return
        
        t = time.time() - start_time
        
        # Animate bars (sine-based pulsing)
        self.layer_meters['cyan'].width = (0.6 + 0.3 * math.sin(t * 0.7)) * 400   # Chirp
        self.layer_meters['orange'].width = (0.5 + 0.45 * math.sin(t * 4.2)) * 400  # Whistle (strong pulse)
        self.layer_meters['purple'].width = 0.4 * 400                               # Nokia
        self.layer_meters['red'].width = (0.35 + 0.25 * math.sin(t * 2.8)) * 400    # Filibuster
        self.layer_meters['white'].width = (0.7 + 0.2 * math.sin(t * 1.2)) * 400    # Overall
    
    def will_close(self):
        pass  # no cleanup needed

# ── Main execution ───────────────────────────────────────────────
print(f"Device name: {MY_PHONE_NAME}")
print(f"Ad message:  {AD_MESSAGE}")

if motion:
    motion.start_updates()
    print("Core Motion updates started")

if location:
    location.start_updates()
    print("Location services started – permission prompt may appear")

start_arkit()

wav_path = None

try:
    wav_path = generate_and_save_wav()
    if not wav_path:
        print("Generation failed – exiting.")
    else:
        player = sound.Player(wav_path)
        player.number_of_loops = -1
        player.play()
        print("\nPlaying stereo: Jammer + FLASH DELTA (live AAPL) + PWM Whistle + Nokia + Filibuster + 14 Hz tremolo")
        print("→ UI visualizer launched (silent bars only – no labels)")
        print("→ Stop with Pythonista ■ button or Ctrl+C")
        
        last_idx = -1
        start_time = time.time()
        last_print = 0
        last_haptic_time = 0.0
        
        # Launch visualizer in its own thread
        viz = AudioVisualizer()
        viz.present('sheet', hide_title_bar=False)
        
        def viz_updater():
            while viz.on_screen:
                viz.update()
                time.sleep(0.25)
        
        threading.Thread(target=viz_updater, daemon=True).start()
        
        while player.playing:
            elapsed = time.time() - start_time
            sample_idx = int(elapsed * FS) % int(FS * DURATION)
            
            whistle_freq, current_idx, step = heigh_ho_whistle_phase(sample_idx, FS)
            
            if elapsed - last_haptic_time > HAPTIC_COOLDOWN_SEC:
                rel_step = step / max(HEIGH_HO_NOTES) if max(HEIGH_HO_NOTES) != 0 else 1.0
                if rel_step > 0.7:
                    style, intensity = 0, 0.7
                elif rel_step > 0.3:
                    style, intensity = 1, 0.85
                else:
                    style, intensity = 2, 1.0
                trigger_haptic(style, intensity)
                last_haptic_time = elapsed
            
            if current_idx != last_idx:
                delta = abs(HEIGH_HO_NOTES[current_idx] - (HEIGH_HO_NOTES[last_idx] if last_idx >= 0 else 0))
                if delta >= 5:
                    style, intensity = 2, 1.0
                elif delta >= 2:
                    style, intensity = 1, 0.8
                else:
                    style, intensity = 0, 0.6
                trigger_haptic(style, intensity)
                last_idx = current_idx
            
            time.sleep(0.08)
            
            if elapsed - last_print > 3:
                last_print = elapsed
                
                if motion:
                    user_accel = motion.get_user_acceleration()
                    gravity_vec = motion.get_gravity()
                    attitude = motion.get_attitude()
                    print(f"\n[Motion @ {time.strftime('%H:%M:%S')}]")
                    print(f"  User Accel (g): x={user_accel[0]:.3f} y={user_accel[1]:.3f} z={user_accel[2]:.3f}")
                    print(f"  Gravity (g):    x={gravity_vec[0]:.3f} y={gravity_vec[1]:.3f} z={gravity_vec[2]:.3f}")
                    print(f"  Attitude (deg): roll={math.degrees(attitude[0]):.1f} pitch={math.degrees(attitude[1]):.1f} yaw={math.degrees(attitude[2]):.1f}°")
                
                if location:
                    loc = location.get_location()
                    if loc:
                        print(f"[Location @ {time.strftime('%H:%M:%S')}] Lat: {loc.get('latitude', 'N/A'):.6f} Lon: {loc.get('longitude', 'N/A'):.6f} Acc: ±{loc.get('horizontal_accuracy', 'N/A'):.1f} m")
                
                ar_data = get_arkit_motion()
                if ar_data:
                    print(f"[ARKit] Yaw: {ar_data['yaw_deg']:.1f}° Pitch: {ar_data['pitch_deg']:.1f}° Roll: {ar_data['roll_deg']:.1f}°")
except KeyboardInterrupt:
    print("Stopped by user")
except Exception as e:
    print(f"Runtime error: {e}")
finally:
    if wav_path is not None:
        if 'player' in locals() and player.playing:
            player.stop()
    if motion:
        motion.stop_updates()
        print("Core Motion stopped")
    if location:
        location.stop_updates()
        print("Location stopped")
    if ar_session:
        ar_session.pause()
        print("ARKit paused")
