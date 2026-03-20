from scene import *
import motion
import location
import sound
import random
import math
import wave
import struct
import os
from datetime import datetime

# Frequencies and audible pitches as specified
VHF_BASE = 145000000
BASE_PITCH = VHF_BASE / 100000
L1_FREQ_MIN = 1575.00e6
L1_FREQ_MAX = 1575.42e6
L1_PITCH = L1_FREQ_MAX / 100000
LORAN_FREQ = 868e6
LORAN_PITCH = LORAN_FREQ / 100000
SIDE_BAND1 = 225.0e6
SIDE_BAND1_PITCH = SIDE_BAND1 / 100000
SIDE_BAND2 = 225.15e6
SIDE_BAND2_PITCH = SIDE_BAND2 / 100000
TX5GHZ = 5000e6
TX5GHZ_PITCH = TX5GHZ / 100000
TX8GHZ = 8000e6
TX8GHZ_PITCH = TX8GHZ / 100000
CHAIN_HOME_MIN = 20e6
CHAIN_HOME_MAX = 40e6
CHAIN_HOME_PITCH = 30e6 / 100000

# Threat / detection logic (replace with real)
def calculate_threat_level():
    r = random.random()
    if r < 0.15: return random.randint(80, 100)
    elif r < 0.50: return random.randint(30, 79)
    elif r < 0.90: return random.randint(1, 29)
    return 0


def play_chain_home_pulse():
    prf = 25.0
    pulse_duration = 0.018
    carrier_freq = 440.0
    grid_freq = 50.0
    total_play_time = 1.2
    sample_rate = 44100
    
    total_samples = int(total_play_time * sample_rate)
    samples = []
    
    for i in range(total_samples):
        t = i / sample_rate
        
        pulse_index = int(t * prf)
        time_in_pulse = (t * prf) - pulse_index
        pulse_value = 0
        if time_in_pulse < pulse_duration:
            pulse_value = 18000.0 * math.sin(2 * math.pi * carrier_freq * t)
        
        hum_value = 6000.0 * math.sin(2 * math.pi * grid_freq * t)
        
        value = pulse_value + hum_value
        value = max(min(value, 32767), -32767)
        samples.append(int(value))
    
    temp_path = os.path.join(os.path.expanduser('~/Documents'), 'chain_home_440hz_pulse.wav')
    
    with wave.open(temp_path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        for sample in samples:
            w.writeframes(struct.pack('<h', sample))
    
    sound.play_effect(temp_path, volume=0.65, pitch=1.0)


class Blip(ShapeNode):
    def __init__(self, pos, threat, parent, birth_time, delta):
        self.threat = threat
        self.birth = birth_time
        self.fade_duration = 0.3  # fade after response
        self.fade_start_time = None
        self.response_sent = False
        
        if threat >= 80:
            col = '#ff4444'  # red
            radius = 18
            sound_effect = 'arcade:Explosion_2'
        elif threat >= 40:
            col = '#ffaa44'  # orange
            radius = 13
            sound_effect = 'arcade:Powerup_1'
        elif threat > 0:
            col = '#6644ff'  # indigo
            radius = 10
            sound_effect = 'digital:PowerUp7'
        else:
            col = '#224488'  # dim gray-blue
            radius = 7
            sound_effect = 'digital:PowerUp2'
        
        path = ui.Path.oval(0, 0, radius*2, radius*2)
        super().__init__(path, fill_color=col, stroke_color='clear', parent=parent)
        self.position = pos
        self.alpha = 1.0
        self.scale = 0.95
        
        sound.play_effect(sound_effect, volume=0.6)
        play_chain_home_pulse()
        
        self.add_trail(col)
        
        self.process_classify_and_respond(parent, delta)


    def add_trail(self, col):
        heading = self.parent.compute_heading() if hasattr(self.parent, 'compute_heading') else 0
        angle_rad = math.radians(90 - heading)
        trail_length = 60
        
        end_x = self.position.x - trail_length * math.cos(angle_rad)
        end_y = self.position.y - trail_length * math.sin(angle_rad)
        
        path = ui.Path()
        path.line_width = 3
        path.move_to(self.position.x, self.position.y)
        path.line_to(end_x, end_y)
        
        trail = ShapeNode(path,
                          stroke_color=col,
                          fill_color='clear',
                          parent=self)
        trail.alpha = 0.7
        self.trail = trail


    def process_classify_and_respond(self, parent, delta):
        self.response_sent = True
        self.fade_start_time = parent.t
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        heading = parent.compute_heading() if hasattr(parent, 'compute_heading') else 'unknown'
        
        mag = motion.get_magnetic_field()
        if mag and len(mag) == 4:
            x, y, z, _ = mag
            mag_ut = math.sqrt(x**2 + y**2 + z**2)
            mag_pt = mag_ut * 1_000_000
        else:
            mag_pt = 'N/A'
        
        threat = self.threat
        pos_rel = (self.position.x - parent.scope_center.x, self.position.y - parent.scope_center.y)
        
        # Random detected frequency (wide range to allow any source)
        freq_received = round(random.uniform(100e6, 9000e6), 2)
        
        source = "Unknown Threat"
        response_type = "Unknown response"
        return_message = f"Challenge reply sent at {freq_received:.2f}"
        
        if L1_FREQ_MIN <= freq_received <= L1_FREQ_MAX:
            source = "AGPS L1 signal (military/civil)"
            response_type = "Strong L1 return detected"
            return_message = f"Challenge reply sent at {freq_received:.2f} MHz"
        elif SIDE_BAND1 - 1e6 <= freq_received <= SIDE_BAND2 + 1e6:
            source = "225 MHz sideband (aviation/nav)"
            response_type = "Medium-strength sideband return"
            return_message = f"Identification request sent at {freq_received:.2f} MHz"
        elif LORAN_FREQ - 1e6 <= freq_received <= LORAN_FREQ + 1e6:
            source = "Loran-C t-beam navigation"
            response_type = "Loran navigation return"
            return_message = f"Reply sent at {freq_received:.2f} MHz"
        elif CHAIN_HOME_MIN <= freq_received <= CHAIN_HOME_MAX:
            source = "Chain Home radar signal"
            response_type = "Early-warning radar detection"
            return_message = f"Chain Home pulse reply at {freq_received:.2f} MHz"
        elif TX5GHZ - 500e6 <= freq_received <= TX5GHZ + 500e6:
            source = "5 GHz wireless (WiFi/comm)"
            response_type = "Weak incidental emission"
            return_message = f"Monitoring continued at {freq_received:.2f} MHz"
        elif TX8GHZ - 500e6 <= freq_received <= TX8GHZ + 500e6:
            source = "8 GHz microwave link/radar"
            response_type = "Microwave band detection"
            return_message = f"Reply sent at {freq_received:.2f} MHz"
        elif VHF_BASE - 10e6 <= freq_received <= VHF_BASE + 10e6:
            source = "VHF radio communication"
            response_type = "VHF band signal"
            return_message = f"Reply sent at {freq_received:.2f} MHz"
        
        # Doppler rate
        doppler = 'N/A'
        if parent.last_heading is not None:
            delta_t = parent.t - parent.last_trigger_time if parent.last_trigger_time > 0 else 0.1
            bearing_rate = (heading - parent.last_heading) / delta_t if delta_t > 0 else 0
            doppler = f'{bearing_rate:.2f} °/s'
        
        # Signal strength
        signal_strength = 'High' if mag_pt > 50000000 else 'Medium' if mag_pt > 25000000 else 'Low'
        
        # Location
        loc = location.get_location()
        lat, lon = (loc.get('latitude', 'N/A'), loc.get('longitude', 'N/A')) if loc else ('N/A', 'N/A')
        
        # Generate directional audio response
        generate_directional_response_audio(heading, source, doppler, signal_strength, freq_received)
        
        # Log entry – agnostic of threat level
        log_entry = (
            f"[{now}] BLIP DETECTED → RESPONSE SENT | "
            f"Threat: {threat} | "
            f"Bearing: {heading:.1f}° | "
            f"Mag: {mag_pt:.1f} pT | "
            f"Signal Strength: {signal_strength} | "
            f"Delta: {delta:.1f}° | "
            f"Pos: ({pos_rel[0]:.1f}, {pos_rel[1]:.1f}) | "
            f"Loc: ({lat:.5f}, {lon:.5f}) | "
            f"Freq: {freq_received:.2f} MHz | "
            f"Source: {source} | "
            f"Response type: {response_type} | "
            f"Return message: {return_message} | "
            f"Doppler rate: {doppler}\n"
        )
        
        print(log_entry)
        
        log_file = os.path.join(os.path.expanduser('~/Documents'), 'blip_log.txt')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)


def generate_directional_response_audio(heading, source, doppler, signal_strength, freq_received):
    pan_factor = (heading - 180) / 180
    left_vol = max(0, 1 - pan_factor)
    right_vol = max(0, 1 + pan_factor)
    
    duration = 1.0
    sample_rate = 44100
    total_samples = int(duration * sample_rate)
    
    samples = []
    
    # Base pitch from source/frequency
    if 'L1' in source or '1575' in str(freq_received):
        pitch = L1_PITCH
    elif 'Loran' in source or '868' in str(freq_received):
        pitch = LORAN_PITCH
    elif '225' in str(freq_received):
        pitch = float(freq_received) / 100000
    elif 'VHF' in source:
        pitch = BASE_PITCH
    elif '5 GHz' in source or '5000' in str(freq_received):
        pitch = TX5GHZ_PITCH / 10
    elif '8 GHz' in source or '8000' in str(freq_received):
        pitch = TX8GHZ_PITCH / 10
    elif 'Chain Home' in source or CHAIN_HOME_MIN <= freq_received <= CHAIN_HOME_MAX:
        pitch = CHAIN_HOME_PITCH
    else:
        pitch = 1000.0
    
    # Doppler modulation
    doppler_shift = 1.0 + (float(doppler.split()[0]) / 1000 if doppler != 'N/A' else 0)
    pitch *= doppler_shift
    
    # Amplitude based on signal strength
    amp_factor = 0.4 if signal_strength == 'Low' else 0.7 if signal_strength == 'Medium' else 1.0
    
    for i in range(total_samples):
        t = i / sample_rate
        value = math.sin(2 * math.pi * pitch * t) * 32000.0 * amp_factor
        left = int(value * left_vol)
        right = int(value * right_vol)
        left = max(min(left, 32767), -32767)
        right = max(min(right, 32767), -32767)
        samples.append((left, right))
    
    temp_path = os.path.join(os.path.expanduser('~/Documents'), 'directional_response.wav')
    
    with wave.open(temp_path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        for left, right in samples:
            w.writeframes(struct.pack('<h', left))
            w.writeframes(struct.pack('<h', right))
    
    sound.play_effect(temp_path, volume=0.8, pitch=1.0)


class YBandRadarScope(Scene):
    def setup(self):
        self.background_color = '#000400'
        
        motion.start_updates()
        location.start_updates()
        
        self.blips = []
        self.last_heading = None
        self.last_trigger_time = 0.0
        self.heading_change_threshold = 4.0
        self.cooldown = 0.5
        
        self.wave_phase = 0.0
        self.pulse_timer = 0.0
        self.pulse_state = 0
        
        self.scope_center = Point(self.size.w/2, self.size.h/2 + 40)
        self.scope_radius = min(self.size.w, self.size.h) * 0.42
        
        border_path = ui.Path.oval(0, 0, self.scope_radius*2 + 16, self.scope_radius*2 + 16)
        border_path.line_width = 6
        self.border = ShapeNode(border_path,
                                stroke_color='#88ccff',
                                fill_color='clear',
                                parent=self)
        self.border.position = self.scope_center
        
        self.sweep = ShapeNode(ui.Path(),
                               stroke_color='#aaddff',
                               fill_color='clear',
                               parent=self)
        self.sweep.line_width = 3
        
        self.bearing_label = LabelNode('---°',
                                       font=('Courier-Bold', 16),
                                       position=(0,0),
                                       color='#cceeff',
                                       parent=self)
        
        for frac in [0.25, 0.5, 0.75]:
            ring_path = ui.Path.oval(0, 0, self.scope_radius*2*frac, self.scope_radius*2*frac)
            ring = ShapeNode(ring_path,
                             stroke_color='#224466',
                             fill_color='clear',
                             parent=self)
            ring.position = self.scope_center
        
        self.threat_label = LabelNode('THREAT: ---',
                                      font=('Courier', 20),
                                      position=(self.size.w/2, 70),
                                      color='#88ccff', parent=self)
        
        self.heading_label = LabelNode('HDG: ---°',
                                       font=('Courier', 18),
                                       position=(self.size.w/2, 45),
                                       color='#77aaff', parent=self)
        
        self.location_label = LabelNode('LAT/LON/ALT: awaiting...',
                                        font=('Courier', 13),
                                        position=(self.size.w/2, 20),
                                        color='#336699', parent=self)
        
        # Top label shows current source/classification only
        self.threat_info_label = LabelNode('No active threat detected',
                                           font=('Courier', 16),
                                           position=(self.size.w/2, self.size.h - 80),
                                           color='#ffffff',
                                           parent=self)
        self.threat_info_label.number_of_lines = 0
        self.threat_info_label.line_break_mode = 0
        self.threat_info_label.size = (self.size.w - 60, 0)
        
        self.last_threat_update = 0.0
        
        print("Blips fade out after response (0.3s) – bright white pulsing waveform every 0.5s")
    
    def stop(self):
        motion.stop_updates()
        location.stop_updates()
    
    def compute_heading(self):
        mag = motion.get_magnetic_field()
        if not mag or len(mag) != 4:
            return None
        x, y, z, acc = mag
        if acc == -1:
            return None
        heading = math.degrees(math.atan2(y, x))
        if heading < 0:
            heading += 360
        return heading
    
    def update(self):
        heading = self.compute_heading()
        
        if heading is not None:
            self.heading_label.text = f'HDG: {heading:.0f}°'
            
            angle_rad = math.radians(90 - heading)
            end_x = self.scope_center.x + self.scope_radius * 0.98 * math.cos(angle_rad)
            end_y = self.scope_center.y + self.scope_radius * 0.98 * math.sin(angle_rad)
            
            path = ui.Path()
            path.line_width = 3
            path.move_to(*self.scope_center)
            path.line_to(end_x, end_y)
            self.sweep.path = path
            
            label_dist = self.scope_radius * 0.82
            lx = self.scope_center.x + label_dist * math.cos(angle_rad)
            ly = self.scope_center.y + label_dist * math.sin(angle_rad)
            self.bearing_label.position = (lx, ly)
            self.bearing_label.text = f'{int(heading)}°'
            
            if self.last_heading is not None:
                delta = min(abs(heading - self.last_heading), 360 - abs(heading - self.last_heading))
                t = self.t
                if delta > self.heading_change_threshold and (t - self.last_trigger_time) > self.cooldown:
                    self.last_trigger_time = t
                    
                    threat = calculate_threat_level()
                    
                    blip_angle = math.radians(90 - heading)
                    dist = random.uniform(self.scope_radius * 0.1, self.scope_radius * 0.88)
                    bx = self.scope_center.x + dist * math.cos(blip_angle)
                    by = self.scope_center.y + dist * math.sin(blip_angle)
                    blip = Blip((bx, by), threat, self, self.t, delta)
                    self.blips.append(blip)
                    
                    self.threat_label.text = f'THREAT: {threat}'
                    
                    self.update_threat_info(threat, heading)
        
        loc = location.get_location()
        if loc:
            lat = loc.get('latitude', '—')
            lon = loc.get('longitude', '—')
            alt = loc.get('altitude', None)
            alt_acc = loc.get('vertical_accuracy', None)
            
            if alt is not None and alt_acc is not None:
                alt_str = f'{alt:.1f}m ±{alt_acc:.1f}m'
            elif alt is not None:
                alt_str = f'{alt:.1f}m (uncertain)'
            else:
                alt_str = 'uncertain / no baro'
            
            self.location_label.text = f'LAT/LON/ALT: {lat:.5f}, {lon:.5f}, {alt_str}'
        else:
            self.location_label.text = 'LAT/LON/ALT: no fix / permission?'
        
        self.last_heading = heading or self.last_heading
    
    def update_threat_info(self, threat, heading):
        if threat == 0:
            info = "No active threat detected"
        else:
            # Show current source/classification only
            # In real use, store last source in self.last_source
            # For now placeholder – replace with actual last source
            info = f"Current Source: Detected threat {threat}"
        
        if hasattr(self, 'threat_info_label'):
            self.threat_info_label.text = info
        else:
            print("Warning: threat_info_label missing in setup")
    
    def draw(self):
        self.pulse_timer += self.dt
        if self.pulse_timer >= 0.5:
            self.pulse_timer = 0.0
            self.pulse_state = 1 - self.pulse_state
        
        no_fill()
        stroke_weight(2.5)
        
        for i in range(6):
            phase_offset = self.wave_phase + i * 1.0
            radius = (phase_offset % 3.8) * self.scope_radius * 0.9
            
            if radius < 5:
                continue
            
            alpha = 0.45 * self.pulse_state
            stroke(1.0, 1.0, 1.0, alpha)
            
            ellipse(self.scope_center.x - radius, self.scope_center.y - radius,
                    radius*2, radius*2)
            
            stroke(0.95, 0.98, 1.0, 0.35 * self.pulse_state)
            stroke_weight(4.5)
            ellipse(self.scope_center.x - radius*0.95, self.scope_center.y - radius*0.95,
                    radius*1.9, radius*1.9)
            stroke_weight(2.5)
        
        self.wave_phase += 0.06
    
    def did_finish_update(self):
        to_remove = []
        current_time = self.t
        
        for blip in self.blips:
            if blip.response_sent and blip.fade_start_time is not None:
                fade_age = current_time - blip.fade_start_time
                fade_progress = fade_age / blip.fade_duration
                
                blip.alpha = max(0, 1.0 - fade_progress)
                if hasattr(blip, 'trail') and blip.trail:
                    blip.trail.alpha = max(0, 0.7 - fade_progress * 0.7)
                
                if fade_progress >= 1.0:
                    to_remove.append(blip)
            else:
                blip.alpha = 1.0
                blip.scale = 1.0
                if hasattr(blip, 'trail') and blip.trail:
                    blip.trail.alpha = 0.7
        
        for n in to_remove:
            n.remove_from_parent()
            self.blips.remove(n)


if __name__ == '__main__':
    run(YBandRadarScope(), PORTRAIT, show_fps=False)
