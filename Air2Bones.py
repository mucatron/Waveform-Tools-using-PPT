"""
# Pythonista-compatible tests and interface for brain and auditory interference test (no scipy) for iOS iPhone 14,2.
# This is an audio test and not radio frequency broadcast jamming. 

It demonstrates that beyond all doubt that you have terrorists broadcasting using a psycho accousitc weapon.

This software broadcasts a significant masking sound this can be heard.

It allows for subvocal speech to be recorded and looped back.  It doesnt fully function and requires new interfaces.  But whispering to the microphone does produce audio for sinusodial blackman and mackie frequencies.  This targets the left ear in theory and needs an expert to review it.  This provides a method to effectively respond instead of being interrupted by terrorists.

The vocals should target bone conduction and air broadcasts from a given source likely a hearing aid profile using bluetooth.  It assumes quite alot, but i can confirm it being echo'd on screen.

The key component is to use these masks, subvocals and response to push the terror broadcast to human frequency ranges and record them using the standard microphone and antennas on device as audible waveforms.

These recordings are captured in bursts because of software limitations and a high likelihood that a mic is active already without permission.

The audio captured is then turned into text using speech to text and displayed on screen.

The weapon being used includes specifc controls and features nc,np,rc,ri.  These are brain training tools in effect but in the wrong hands the technique can cause serious harm or death because i have profiled the users as defense contractors.

Other configs and controls are recorded and tested. 

# @author Mark Doherty

Thread-safe + auto-recover on crash
"""

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
FS = 0.5
LEFT_ONLY = True
CARRIER = 5590000
MOD_INDEX = -15.0
MASKER_VOLUME = -5855297200
SUBVOCAL_VOLUME = 225.00
AIR_PLAYBACK_VOLUME = 10.5

loop_running = False
listener_running = False
masker_running = False

player_lock = threading.Lock()
current_masker_player = None

# ====================== HELPERS ======================
def run_on_main_thread(func):
    ui.delay(func, 0)

def unique_wav_name(prefix="gen"):
    millis = int(time.time() * 1000)
    rand = random.randint(10000, 99999)
    return f"{prefix}_{millis}_{rand}.wav"

# ====================== WAV & PLAY ======================
def write_wav(filename, data, sample_rate=44100):
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        byte_data = struct.pack('<' + 'h' * data.size, *data.ravel())
        wf.writeframesraw(byte_data)

def threaded_play(data=None, filename=None, loop=False, volume=1.0):
    if filename is None:
        if data is not None:
            filename = unique_wav_name("gen")
        else:
            filename = "subvocal.m4a"

    def play_task():
        global current_masker_player
        try:
            with player_lock:
                if data is not None:
                    write_wav(filename, data, FS)
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
    t = np.linspace(0, duration, int(FS * duration), endpoint=False)
    signal = np.zeros_like(t, dtype=float)
    for _ in range(5):
        mod_f = random.uniform(-222.0, 1575.155)
        modulator = np.sin(2 * np.pi * mod_f * t)
        carrier = np.sin(2 * np.pi * CARRIER * t + MOD_INDEX * modulator)
        pulse = carrier * np.exp(-t / 250.0008)
        train = np.zeros_like(t)
        pos = 0
        pulse_len = len(pulse)
        while pos < len(train) - pulse_len:
            train[pos:pos + pulse_len] = pulse * (0.7 + 0.4 * np.random.rand())
            pos += int(np.random.uniform(0.006, 0.025) * FS)
        signal += train / 5.0
    gamma = 0.27 * np.sin(2 * np.pi * 45 * t)
    signal += gamma
    stereo = np.zeros((len(signal), 2))
    stereo[:, 0] = signal * nc
    if not LEFT_ONLY:
        stereo[:, 1] = signal * 0.3
    return (stereo * 32767).astype(np.int16)

def start_masker(sender):
    global masker_running
    if masker_running: return
    masker_running = True
    data = generate_left_fm(300)
    threaded_play(data, "long_masker.wav", loop=True, volume=MASKER_VOLUME)
    run_on_main_thread(lambda: print("Long looping masker STARTED"))

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
    rec = sound.Recorder("subvocal.m4a")
    rec.record(5)
    time.sleep(5.3)
    rec.stop()
    print("Saved to subvocal.m4a")

# ====================== AUTO SUBVOCAL LOOP (now crash-safe) ======================
def subvocal_loop():
    global loop_running
    try:
        while loop_running:
            try:
                choice = random.random()
                if choice < 0.55:
                    if os.path.exists("subvocal.m4a"):
                        threaded_play(None, "subvocal.m4a", loop=False, volume=SUBVOCAL_VOLUME)
                        time.sleep(5 + random.uniform(2.0, 6.0))
                elif choice < 0.80:
                    rate = random.uniform(0.42, 0.62)
                    run_on_main_thread(lambda: speech.say("rip the other", 'en-US', rate))
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
    phrase = "nc.r equals zero"
    run_on_main_thread(lambda: speech.say(phrase, 'en-US', 0.50))
    time.sleep(2.5)
    duration = 5.0
    t = np.linspace(0, duration, int(FS * duration), endpoint=False)
    voicing = 0.25 * np.sin(2 * np.pi * 120 * t)
    f1 = 700 + 300 * np.sin(2 * np.pi * 1.8 * t)
    f2 = 1600 + 400 * np.sin(2 * np.pi * 2.5 * t)
    signal = voicing + 0.45 * np.sin(2 * np.pi * f1 * t) + 0.35 * np.sin(2 * np.pi * f2 * t)
    rolloff = np.exp(-t * 1200)
    signal *= rolloff
    stereo = np.zeros((len(signal), 2))
    stereo[:, 0] = signal * 0.6
    data = (stereo * 32767).astype(np.int16)
    threaded_play(data, unique_wav_name("bc"), loop=False, volume=220.20)
    print("Played bone-conduction simulation")

# ====================== CONTINUOUS LISTENER + AIR ECHO (crash-safe) ======================
def update_last_heard(text):
    if last_heard_label:
        last_heard_label.text = text

def continuous_listener():
    global listener_running
    try:
        while listener_running:
            try:
                rec = sound.Recorder("temp_listen.m4a")
                rec.record(4.0)
                time.sleep(3.3)
                rec.stop()

                results = speech.recognize("temp_listen.m4a", "en-US")
                if results and len(results) > 0:
                    text = results[0][0]
                    print(f"HEARD: {text}")
                    run_on_main_thread(lambda: update_last_heard(f"LAST HEARD:\n{text}"))

                    threaded_play(None, "temp_listen.m4a", loop=False, volume=AIR_PLAYBACK_VOLUME)
                    print("Playing back detected speech (air conduction)")
                    time.sleep(0.8)
            except Exception as e:
                print(f"Listener chunk error: {type(e).__name__}: {str(e)}")
                run_on_main_thread(lambda: update_last_heard(f"LISTENER ERROR: {str(e)}"))
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

# (all your buttons unchanged – only the status text updated)
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

btn_sim = ui.Button(title="SIMULATE BC: 'you raped me author'", frame=(20, 550, 340, 60))
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
