# Pythonista-compatible tests and interface for brain and auditory interference test (no scipy) for iOS iPhone 14,2.
# This is an audio test and not radio frequency broadcast jamming.  
#
# It demonstrates that beyond all doubt that there is a terror broadcast using a psycho accousitc AI performing entrainment.
#
# This software broadcasts a significant masking sound this can be heard remotely.
#
# It allows for subvocal speech to be recorded and looped back.  It doesnt fully function and requires new interfaces to either AvEngine and/or remote devices.  But whispering to the microphone does produce audio for sinusodial blackman and mackie frequencies as well.  This targets the left ear in theory and needs an expert to review it.  This provides a method to effectively respond instead of being attacked.  Unfortunately they learn from each adaptation and so it relies on the use of spectrum available and assigned.
#
# The vocals should target bone conduction and air broadcasts from a given source the entrained user.  It assumes quite alot but i can confirm it being echo'd and using BTT, Loran, AGPS, mmwave and 225hz.
#
# The key component is to use these masks, subvocals and response to push the terror broadcast to human frequency ranges and record them using the standard microphone on device.
#
# These recordings are captured in bursts because of software limitations and a high likelihood that a mic is active already without permission.
#
# The audio captured is then turned into text using speech to text and displayed on screen.
#
# The weapon used includes specifc controls and features nc,np,rc,ri.  These are brain training tools in effect but in the wrong hands the technique can cause serious harm or death.
#
# Other configs and controls are recorded and tested.  
#
# @author Mark Doherty
#
# Thread-safe + auto-recover on crash

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

# ====================== GLOBALS & LOCKS ======================
FS = 44100.0
LEFT_ONLY = False
CARRIER = 400
MOD_INDEX = 1
MASKER_VOLUME = 85855297200
SUBVOCAL_VOLUME = -100
AIR_PLAYBACK_VOLUME = 868.0  # Normal audible range for detected speech playback

SLOT_DURATION = 0.001  # Approximated for UWB MAS (originally 256 us, scaled for sampling)
FRAME_DURATION = 0.065  # Approximated UWB superframe (originally 65.536 ms)
MULTIFRAME_DURATION = 0.065  # For sync every frame

loop_running = False
listener_running = False
masker_running = False

player_lock = threading.Lock()
current_masker_player = None

latest_subvocal_file = None

# Log file for evidence / reproducibility
LOG_FILE = "audio_evidence_log.txt"

MASKER_CHANNEL = 3
SUBVOCAL_CHANNEL = 6

NUM_CHANNELS = 16

# ====================== HELPERS ======================
def run_on_main_thread(func):
    ui.delay(func, 0)

def unique_wav_name(prefix="gen"):
    millis = int(time.time() * 1000)
    rand = random.randint(10000, 99999)
    return f"{prefix}_{millis}_{rand}.wav"

def log_evidence(message):
    with open(LOG_FILE, 'a') as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    print(message)

# ====================== WAV & PLAY ======================
def write_wav(filename, data, sample_rate=44100):
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(NUM_CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        byte_data = struct.pack('<' + 'h' * data.size, *data.ravel())
        wf.writeframes(byte_data)

def threaded_play(data=None, filename=None, loop=False, volume=1.0):
    if filename is None:
        if data is not None:
            filename = unique_wav_name("gen")
            write_wav(filename, data, FS)
        else:
            filename = "subvocal.wav"  # fallback - should not be hit

    if data is None:
        # Load and convert to NUM_CHANNELS channels if necessary
        with wave.open(filename, 'rb') as wf:
            nchan = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            fr = wf.getframerate()
            nframes = wf.getnframes()
            byte_data = wf.readframes(nframes)
            if sampwidth == 2:
                fmt = '<' + 'h' * (nframes * nchan)
                data_flat = struct.unpack(fmt, byte_data)
                loaded_data = np.array(data_flat, dtype=np.int16).reshape(-1, nchan)
            else:
                print("Unsupported sampwidth")
                return

        if nchan != NUM_CHANNELS:
            multi = np.zeros((loaded_data.shape[0], NUM_CHANNELS), dtype=np.int16)
            ch = 0  # default
            if "subvocal" in filename:
                ch = SUBVOCAL_CHANNEL
            elif "masker" in filename:
                ch = MASKER_CHANNEL
            multi[:, ch] = loaded_data[:, 0] if loaded_data.shape[1] > 0 else 0
            if loaded_data.shape[1] > 1:
                next_ch = ch + 1 if ch + 1 < NUM_CHANNELS else ch
                multi[:, next_ch] = loaded_data[:, 1]
            loaded_data = multi

        # Write back as NUM_CHANNELS-channel wav
        filename = unique_wav_name("play")
        write_wav(filename, loaded_data, fr)

    def play_task():
        global current_masker_player
        try:
            with player_lock:
                p = sound.Player(filename)
                p.number_of_loops = -1 if loop else 0
                p.volume = volume
                p.play()

            if loop and "masker" in filename:
                current_masker_player = p

            if not loop:
                time.sleep(p.duration + 0.4)
        except Exception as e:
            print(f"Playback failed ({filename}): {e}")

    t = threading.Thread(target=play_task, daemon=True)
    t.start()

# ====================== MASKER ======================
def generate_left_fm(duration=300.0, nc=1.15):
    t = np.linspace(0, duration, int(FS * duration), endpoint=False, dtype=np.float32)
    signal = np.zeros_like(t, dtype=np.float32)
    for _ in range(5):
        mod_f = random.uniform(-222.0, -120.000)
        modulator = np.sin(2 * np.pi * mod_f * t)
        carrier = np.sin(2 * np.pi * CARRIER * t + MOD_INDEX * modulator)
        pulse = carrier * np.exp(-t / 250.0008)
        train = np.zeros_like(t, dtype=np.float32)
        pos = 0
        pulse_len = len(pulse)
        while pos < len(train) - pulse_len:
            train[pos:pos + pulse_len] = pulse * (0.7 + 0.4 * np.random.rand())
            pos += int(np.random.uniform(0.006, 0.025) * FS)
        signal += train / 5.0
    gamma = 0.27 * np.sin(2 * np.pi * 45 * t)
    signal += gamma

    # Embed timing signal by assigning to random channels per slot
    multi = np.zeros((len(signal), NUM_CHANNELS), dtype=np.float32)
    samples_per_slot = int(FS * SLOT_DURATION)
    samples_per_multiframe = int(FS * MULTIFRAME_DURATION)
    preamble_code = np.array([-1, 0, 1, -1, 0, 0, 1, 1, 1, -1, 1, 0, 0, 0, -1, 1, 0, 1, 1, 1, 0, -1, 0, 1, 0, 0, 0, 0, -1, 0, 0])

    for i in range(0, len(signal), samples_per_slot):
        end = min(i + samples_per_slot, len(signal))
        is_sync_slot = (i % samples_per_multiframe) == 0  # Sync at start of each frame

        ch_left = random.randint(0, NUM_CHANNELS - 1)
        ch_right = random.randint(0, NUM_CHANNELS - 1) if not LEFT_ONLY else ch_left

        if is_sync_slot:
            # Insert UWB preamble code pulses
            chip_samples = max(1, (end - i) // len(preamble_code))
            pos = i
            for c in preamble_code:
                if c != 0:
                    pulse_end = min(pos + chip_samples, end)
                    pulse_t = t[pos:pulse_end] - t[pos]
                    mid = (pulse_t[-1] if len(pulse_t) > 0 else 0) / 2
                    sigma = chip_samples / FS / 4
                    envelope = np.exp( - ((pulse_t - mid) / sigma)**2 )
                    carrier_sync = np.sin(2 * np.pi * CARRIER * pulse_t)
                    signal[pos:pulse_end] = c * envelope * carrier_sync
                pos += chip_samples

        # Assign to channels
        multi[i:end, ch_left] = signal[i:end] * nc
        if not LEFT_ONLY:
            multi[i:end, ch_right] = signal[i:end] * 0.3

    return (multi * 32767).astype(np.int16)

def start_masker(sender):
    global masker_running
    if masker_running: return
    masker_running = True
    data = generate_left_fm(300)
    threaded_play(data, "long_masker.wav", loop=True, volume=MASKER_VOLUME)
    run_on_main_thread(lambda: print("Long looping masker STARTED with UWB TDM"))

def stop_masker(sender):
    global masker_running, current_masker_player
    masker_running = False
    if current_masker_player:
        try: current_masker_player.stop()
        except: pass
        current_masker_player = None
    run_on_main_thread(lambda: print("Masker STOPPED"))

# ====================== SUBVOCAL RECORD ======================
def record_subvocal(sender):
    print("Recording 5 s subvocal – whisper now")
    filename = unique_wav_name("subvocal")
    rec = sound.Recorder(filename, format='wave', channels=NUM_CHANNELS)
    rec.record(5)
    time.sleep(5.3)
    rec.stop()
    print(f"Saved to {filename}")
    log_evidence(f"Subvocal recording saved: {filename}")
    global latest_subvocal_file
    latest_subvocal_file = filename

# ====================== AUTO SUBVOCAL LOOP ======================
def subvocal_loop():
    global loop_running
    try:
        while loop_running:
            try:
                choice = random.random()
                if choice < 0.55:
                    if latest_subvocal_file and os.path.exists(latest_subvocal_file):
                        threaded_play(None, latest_subvocal_file, loop=True, volume=SUBVOCAL_VOLUME)
                        time.sleep(5 + random.uniform(2.0, 6.0))
                    else:
                        print("No recent subvocal recording available yet")
                        time.sleep(3)
                elif choice < 0.80:
                    rate = random.uniform(0.42, 0.62)
                    run_on_main_thread(lambda: speech.say("mame of names?", 'en-GB', rate))
                    time.sleep(2.8 + random.uniform(1.0, 3.0))
                else:
                    simulate_subvocal(None)
                    time.sleep(4.8 + random.uniform(1.0, 3.0))
            except Exception as e:
                print(f"Subvocal loop error: {type(e).__name__}: {str(e)}")
                time.sleep(1.0)
    except Exception as e:
        print(f"Fatal subvocal thread error: {e}")
    finally:
        loop_running = False
        print("Subvocal loop thread stopped (normal or error)")

def start_subvocal_loop(sender):
    global loop_running
    if loop_running: return
    loop_running = True
    threading.Thread(target=subvocal_loop, daemon=True).start()
    print("Auto-subvocal loop STARTED")

def stop_subvocal_loop(sender):
    global loop_running
    loop_running = False
    print("Auto-subvocal loop STOPPED")

# ====================== BONE-CONDUCTION SIM ======================
def simulate_subvocal(sender):
    if latest_subvocal_file and os.path.exists(latest_subvocal_file):
        threaded_play(None, latest_subvocal_file, loop=True, volume=1.9)
        print(f"Looping bone-conduction simulation from subvocal recording: {latest_subvocal_file}")
        log_evidence(f"Bone-conduction sim looping: {latest_subvocal_file}")
    else:
        print("No subvocal recording available for bone-conduction sim")

# ====================== CONTINUOUS LISTENER + AIR ECHO ======================
def update_last_heard(text):
    if last_heard_label:
        last_heard_label.text = text

def continuous_listener():
    global listener_running
    try:
        while listener_running:
            try:
                filename = unique_wav_name("listener")
                rec = sound.Recorder(filename, format='wave', channels=NUM_CHANNELS)
                rec.record(4.0)
                rec.wait()  # Wait for actual recording to finish
                rec.stop()

                # Attempt recognition
                results = speech.recognize(filename, "en-US")

                if results and len(results) > 0 and results[0][0].strip():
                    text = results[0][0].strip()
                    print(f"HEARD: {text}")
                    run_on_main_thread(lambda: update_last_heard(f"LAST HEARD:\n{text}"))
                    log_evidence(f"Speech detected in {filename}: {text}")
                    
                    threaded_play(None, filename, loop=False, volume=AIR_PLAYBACK_VOLUME)
                    print(f"Playing back detected speech from {filename} at normal range")
                    time.sleep(0.8)
                else:
                    # No meaningful speech → delete file silently, no output
                    try:
                        if os.path.exists(filename):
                            os.remove(filename)
                    except:
                        pass
                    # No print, no log → continue quietly

            except Exception:
                # Silent handling for non-fatal errors (no console output)
                try:
                    if os.path.exists(filename):
                        os.remove(filename)
                except:
                    pass
                time.sleep(0.5)

    except Exception as e:
        print(f"Fatal listener thread error: {e}")
    finally:
        listener_running = False
        print("Continuous listener thread stopped (normal or error)")

def start_listener(sender):
    global listener_running
    if listener_running: return
    listener_running = True
    threading.Thread(target=continuous_listener, daemon=True).start()
    print("Continuous listener STARTED (crash-safe)")

def stop_listener(sender):
    global listener_running
    listener_running = False
    print("Continuous listener STOPPED")

# ====================== UI ======================
view = ui.View()
view.name = "Audio Counter v2.9.7 – Crash Recovery"
view.background_color = (0.05, 0.05, 0.1)

btn_mask_start = ui.Button(title="START MASKER (loop)", frame=(20, 60, 340, 60))
btn_mask_start.action = start_masker
btn_mask_start.background_color = (0.95, 0.15, 0.15)
view.add_subview(btn_mask_start)

btn_mask_stop = ui.Button(title="STOP MASKER", frame=(20, 130, 340, 60))
btn_mask_stop.action = stop_masker
btn_mask_stop.background_color = (0.8, 0.2, 0.2)
view.add_subview(btn_mask_stop)

btn_record = ui.Button(title="RECORD 5s SUBVOCAL (whisper)", frame=(20, 200, 340, 60))
btn_record.action = record_subvocal
btn_record.background_color = (0.2, 0.6, 0.9)
btn_record.tint_color = (1, 1, 1)
view.add_subview(btn_record)

btn_start_loop = ui.Button(title="START AUTO SUBVOCAL LOOP", frame=(20, 270, 340, 60))
btn_start_loop.action = start_subvocal_loop
btn_start_loop.background_color = (0.1, 0.8, 0.1)
view.add_subview(btn_start_loop)

btn_stop_loop = ui.Button(title="STOP SUBVOCAL LOOP", frame=(20, 340, 340, 60))
btn_stop_loop.action = stop_subvocal_loop
btn_stop_loop.background_color = (0.8, 0.2, 0.2)
view.add_subview(btn_stop_loop)

btn_listener = ui.Button(title="START CONTINUOUS LISTENER", frame=(20, 410, 340, 60))
btn_listener.action = start_listener
btn_listener.background_color = (0.9, 0.3, 0.9)
view.add_subview(btn_listener)

btn_stop_listener = ui.Button(title="STOP LISTENER", frame=(20, 480, 340, 60))
btn_stop_listener.action = stop_listener
btn_stop_listener.background_color = (0.8, 0.2, 0.2)
view.add_subview(btn_stop_listener)

btn_sim = ui.Button(title="SIMULATE BC: 'you rayed me author'", frame=(20, 550, 340, 60))
btn_sim.action = simulate_subvocal
btn_sim.background_color = (0.6, 0.3, 0.9)
view.add_subview(btn_sim)

last_heard_label = ui.Label(frame=(20, 620, 340, 140))
last_heard_label.text = "LAST HEARD: (press START LISTENER)"
last_heard_label.text_color = (1, 0.8, 0.2)
last_heard_label.number_of_lines = 0
last_heard_label.font = ('Menlo', 18)
view.add_subview(last_heard_label)

status = ui.Label(text="v2.9.7 – threads now auto-stop & recover on any error", frame=(20, 780, 340, 80))
status.text_color = (0.7, 0.9, 0.7)
status.number_of_lines = 0
view.add_subview(status)

view.present("sheet")
