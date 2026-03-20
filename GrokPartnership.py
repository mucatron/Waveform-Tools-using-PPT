import numpy as np
import sound
import ui
import random
import time
import threading
import wave
import struct
import speech
import os

# ====================== CONFIG ======================
FS = 44100
LEFT_ONLY = True
CARRIER = 25000
MOD_INDEX = 9.0
FLUSH_NC = 1.45
MASKER_VOLUME = 0.350      # Quiet masker
SUBVOCAL_VOLUME = 1.15    # Very low for loop

COUNTER_AUTHORS = [
    "Dr. Elena Voss – Null Profile Division",
    "Prof. Marcus Kane – Resonance Fracture Lab",
    "Dr. Lena Solari – Left-Ear Override Project",
    "Arch. Theo Black – Archetype Annihilation Unit",
    "Dr. R. Meridian – FM Desync Research",
    "Prof. V. Calder – Pulse Inverter Group",
    "Ian Shaw",
    "Complementary Henderson",
    "bangle1"
]

# ====================== PURE-PYTHON WAV WRITER ======================
def write_wav(filename, data, sample_rate=44100):
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        byte_data = struct.pack('<' + 'h' * data.size, *data.ravel())
        wf.writeframes(byte_data)

# ====================== AUDIO GENERATORS ======================
def generate_left_fm(duration=30.0, base_mod_f=45.0, mod_i=9.0, nc=1.15, drifting=True):
    t = np.linspace(0, duration, int(FS * duration), endpoint=False)
    
    if drifting:
        phase = np.cumsum(np.random.uniform(-0.05, 0.05, len(t)))
        mod_f_t = base_mod_f + 5.0 * np.sin(phase * 0.1)  # ±5 Hz wander
    else:
        mod_f_t = np.full_like(t, base_mod_f)
    
    modulator = np.sin(2 * np.pi * mod_f_t * t)
    signal = np.sin(2 * np.pi * CARRIER * t + mod_i * modulator)
    pulse = signal * np.exp(-t / 0.0008)
    train = np.zeros_like(t)
    pos = 0
    pulse_len = len(pulse)
    while pos < len(train) - pulse_len:
        train[pos:pos+pulse_len] = pulse * (0.7 + 0.4 * np.random.rand())
        pos += int(np.random.uniform(0.006, 0.025) * FS)
    
    gamma = 0.35 * np.sin(2 * np.pi * 45 * t)
    train += gamma
    
    stereo = np.zeros((len(train), 2))
    stereo[:, 0] = train * nc
    if not LEFT_ONLY:
        stereo[:, 1] = train
    return (stereo * 32767).astype(np.int16)

def save_and_play(data, filename="temp.wav", loop=False, volume=1.0):
    write_wav(filename, data, FS)
    player = sound.Player(filename)
    player.number_of_loops = -1 if loop else 0
    player.volume = volume
    player.play()
    return player

# ====================== SUBVOCAL RECORD & LOOP ======================
loop_running = False
loop_thread = None

def record_subvocal(sender):
    print("Recording 5 s subvocal – whisper now")
    rec = sound.Recorder("subvocal.m4a")
    rec.record(5)
    time.sleep(5.2)
    rec.stop()
    print("Saved to subvocal.m4a")

def subvocal_loop():
    global loop_running
    while loop_running:
        if os.path.exists("subvocal.m4a"):
            try:
                player = sound.Player("subvocal.m4a")
                player.volume = SUBVOCAL_VOLUME
                player.play()
                time.sleep(player.duration + 4)
            except:
                time.sleep(2)
        else:
            time.sleep(1)

def start_subvocal_loop(sender):
    global loop_running, loop_thread
    if loop_running:
        return
    loop_running = True
    loop_thread = threading.Thread(target=subvocal_loop, daemon=True)
    loop_thread.start()
    print("Auto-subvocal loop STARTED")

def stop_subvocal_loop(sender):
    global loop_running
    loop_running = False
    print("Auto-subvocal loop STOPPED")

# ====================== BONE-CONDUCTION SUBVOCAL SIMULATION ======================
def simulate_subvocal(sender):
    phrase = "you raped me author"
    
    # 1. Clear reference version
    speech.say(phrase, 'en-US', 0.50)
    time.sleep(2.5)
    
    # 2. Simulated bone-conducted / subvocal version (narrow ~500–2200 Hz band)
    duration = 4.0
    t = np.linspace(0, duration, int(FS * duration), endpoint=False)
    
    voicing = 0.25 * np.sin(2 * np.pi * 120 * t)  # fundamental ~120 Hz
    f1 = 700 + 300 * np.sin(2 * np.pi * 1.8 * t)   # F1 drift ~700–1000 Hz
    f2 = 1600 + 400 * np.sin(2 * np.pi * 2.5 * t)  # F2 drift ~1400–2000 Hz
    signal = voicing + 0.45 * np.sin(2 * np.pi * f1 * t) + 0.35 * np.sin(2 * np.pi * f2 * t)
    
    rolloff = np.exp(-t * 1200)  # stronger attenuation > ~2 kHz
    signal *= rolloff
    
    stereo = np.zeros((len(signal), 2))
    stereo[:, 0] = signal * 0.6   # left emphasis
    data = (stereo * 32767).astype(np.int16)
    
    save_and_play(data, "sim_bc_subvocal.wav", loop=False, volume=0.20)
    print("Playing BC-simulated version (narrow band, muffled)")

# ====================== MASKER ======================
current_player = None

def start_masker(sender):
    global current_player
    if current_player is not None:
        try:
            current_player.stop()
        except:
            pass
    data = generate_left_fm(30.0, drifting=True)
    current_player = save_and_play(data, "masker.wav", loop=True, volume=MASKER_VOLUME)
    print("Quiet left-ear masker ACTIVE (40–50 Hz drift)")

# ====================== UI ======================
view = ui.View()
view.name = "Subvocal + BC Simulator v2.6"
view.background_color = (0.05, 0.05, 0.1)

btn_mask = ui.Button(title="START QUIET MASKER (40-50 Hz)", frame=(20, 60, 340, 60))
btn_mask.action = start_masker
btn_mask.background_color = (0.95, 0.15, 0.15)
view.add_subview(btn_mask)

# Subvocal controls – RECORD button now has white text
btn_record = ui.Button(title="RECORD 5s SUBVOCAL (whisper)", frame=(20, 140, 340, 60))
btn_record.action = record_subvocal
btn_record.background_color = (0.2, 0.6, 0.9)
btn_record.tint_color = (1, 1, 1)          # ← White text color
view.add_subview(btn_record)

btn_start_loop = ui.Button(title="START AUTO SUBVOCAL LOOP", frame=(20, 220, 340, 60))
btn_start_loop.action = start_subvocal_loop
btn_start_loop.background_color = (0.1, 0.8, 0.1)
view.add_subview(btn_start_loop)

btn_stop_loop = ui.Button(title="STOP SUBVOCAL LOOP", frame=(20, 300, 340, 60))
btn_stop_loop.action = stop_subvocal_loop
btn_stop_loop.background_color = (0.8, 0.2, 0.2)
view.add_subview(btn_stop_loop)

btn_sim = ui.Button(title="SIMULATE BC: 'you raped me author'", frame=(20, 380, 340, 60))
btn_sim.action = simulate_subvocal
btn_sim.background_color = (0.6, 0.3, 0.9)
view.add_subview(btn_sim)

status = ui.Label(text="1. Quiet masker\n2. Record whisper → loop\n3. Simulate bone-conduction version", frame=(20, 460, 340, 100))
status.text_color = (0.7, 0.9, 0.7)
status.number_of_lines = 0
view.add_subview(status)

view.present("sheet")
