# Motion Tracker – Stable Version (No Blip Sound, No Crash)
# Pythonista iOS – Blips 3 s, Heading/Distance in Console, Head Contact Overlay

import motion
import sound
import ui
import location
import math
import time
import console

L1_FREQ = 1575.41345
BASE_PITCH = L1_FREQ * 1000

try:
    motion.start_updates()
    time.sleep(0.8)
except Exception as e:
    console.hud_alert(f"Motion failed: {e}", 'error')
    raise SystemExit

location.start_updates()

class TrackerView(ui.View):
    def __init__(self):
        self.background_color = '#000022'
        self.name = 'Motion Tracker + GPS'
        
        self.threat_label = ui.Label()
        self.threat_label.flex = 'W'
        self.threat_label.text_color = 'lime'
        self.threat_label.font = ('Menlo', 24)
        self.threat_label.alignment = ui.ALIGN_CENTER
        self.threat_label.text = 'Threat: Calm'
        self.threat_label.y = 40
        self.threat_label.height = 50
        self.add_subview(self.threat_label)

        self.field_label = ui.Label()
        self.field_label.flex = 'W'
        self.field_label.text_color = 'yellow'
        self.field_label.font = ('Menlo', 16)
        self.field_label.number_of_lines = 0
        self.field_label.text = 'Field: --- μT   Δ: ---'
        self.field_label.y = 100
        self.field_label.height = 60
        self.field_label.x = 20
        self.add_subview(self.field_label)

        self.location_label = ui.Label()
        self.location_label.flex = 'W'
        self.location_label.text_color = '#88ff88'
        self.location_label.font = ('Menlo', 14)
        self.location_label.number_of_lines = 0
        self.location_label.text = 'Location: ---'
        self.location_label.y = 170
        self.location_label.height = 80
        self.location_label.x = 20
        self.add_subview(self.location_label)

        self.heading_label = ui.Label()
        self.heading_label.flex = 'W'
        self.heading_label.text_color = 'cyan'
        self.heading_label.font = ('Menlo', 20)
        self.heading_label.alignment = ui.ALIGN_CENTER
        self.heading_label.text = 'Heading: --- deg'
        self.heading_label.y = 260
        self.heading_label.height = 40
        self.add_subview(self.heading_label)

        self.head_contact_label = ui.Label()
        self.head_contact_label.text = 'Head Contact'
        self.head_contact_label.text_color = 'red'
        self.head_contact_label.font = ('Menlo-Bold', 28)
        self.head_contact_label.alignment = ui.ALIGN_CENTER
        self.head_contact_label.alpha = 0.0
        self.add_subview(self.head_contact_label)

        self.sweep_container = ui.View()
        self.sweep_container.background_color = '#001122'
        self.sweep_container.border_width = 3
        self.sweep_container.border_color = 'lime'
        self.add_subview(self.sweep_container)

        self.sweep_line = ui.View()
        self.sweep_line.background_color = 'lime'
        self.sweep_container.add_subview(self.sweep_line)

        # Blip pool – no labels, no sound
        self.blip_pool = []
        self.blip_next_index = 0
        for _ in range(8):
            blip = ui.View(background_color='red', corner_radius=6, alpha=0.0)
            blip.frame = (0, 0, 12, 12)
            self.sweep_container.add_subview(blip)
            self.blip_pool.append(blip)

        self.last_blip_time = 0
        self.last_center_blip_time = 0
        self.last_strength = 0
        self.fil_voltage = 3.27

        self.schedule_update()

    def layout(self):
        w, h = self.width, self.height
        self.threat_label.width = w
        self.field_label.width = w - 40
        self.location_label.width = w - 40
        self.heading_label.width = w
        self.head_contact_label.width = w
        self.head_contact_label.center = (w/2, h/2 - 50)

        sweep_size = min(w, h) * 0.55
        self.sweep_container.frame = (w/2 - sweep_size/2, h - sweep_size - 20, sweep_size, sweep_size)
        self.sweep_container.corner_radius = sweep_size / 2
        self.sweep_line.frame = (sweep_size/2 - 2, 0, 4, sweep_size/2)

    def schedule_update(self):
        self.update()
        ui.delay(self.schedule_update, 0.2)

    def update(self):
        mag = motion.get_magnetic_field()
        if not mag:
            return

        x, y, z, acc = mag
        strength = math.sqrt(x**2 + y**2 + z**2)
        delta = abs(strength - self.last_strength)
        self.last_strength = strength

        heading_rad = math.atan2(y, x)
        heading_deg = (math.degrees(heading_rad) + 360) % 360
        self.heading_label.text = f'Heading: {heading_deg:.1f}° (acc: {acc})'
        angle = math.radians(heading_deg)
        self.sweep_line.transform = ui.Transform.rotation(angle)

        threat = (strength / 20) + (delta * 8)
        threat = min(max(threat, 0), 10)

        current_time = time.time()

        # Threat + Head Contact + forced center blip
        if threat < 1.5:
            self.threat_label.text = 'Threat: Calm'
            self.threat_label.text_color = 'lime'
            self.head_contact_label.alpha = 0.0
        elif threat < 4:
            self.threat_label.text = 'Threat: Movement Detected'
            self.threat_label.text_color = 'yellow'
            self.head_contact_label.alpha = 0.6
        else:
            self.threat_label.text = 'Threat: CLOSE CONTACT!'
            self.threat_label.text_color = 'red'
            self.head_contact_label.alpha = 1.0

            if current_time - self.last_center_blip_time > 3.0:
                self.last_center_blip_time = current_time
                idx = self.blip_next_index
                blip = self.blip_pool[idx]
                self.blip_next_index = (idx + 1) % len(self.blip_pool)

                sweep_size = self.sweep_container.width
                blip.frame = (sweep_size/2 - 6, sweep_size/2 - 6, 12, 12)
                blip.alpha = 0.9

                def fade_center():
                    blip.alpha = 0.0

                ui.delay(fade_center, 3.0)

        self.field_label.text = f'Field: {strength:.1f} μT   Δ: {delta:.2f}'

        loc = location.get_location()
        if loc:
            lat = loc.get('latitude', '---')
            lon = loc.get('longitude', '---')
            alt = loc.get('altitude', '---')
            hacc = loc.get('horizontal_accuracy', '---')
            self.location_label.text = (f'Lat: {lat:.6f}  Lon: {lon:.6f}\n'
                                       f'Alt: {alt:.1f} m   Acc: ±{hacc:.1f} m')
        else:
            self.location_label.text = 'Location: Not available'

        # Directional blip – print info to console
        current_time = time.time()
        if delta > 2 and threat > 3 and (current_time - self.last_blip_time > 0.5):
            self.last_blip_time = current_time

            idx = self.blip_next_index
            blip = self.blip_pool[idx]
            self.blip_next_index = (idx + 1) % len(self.blip_pool)

            sweep_size = self.sweep_container.width
            blip_radius = sweep_size / 2 * 0.8
            blip_x = sweep_size/2 + blip_radius * math.cos(angle) - 6
            blip_y = sweep_size/2 + blip_radius * math.sin(angle) - 6

            blip.frame = (blip_x, blip_y, 12, 12)
            blip.alpha = 0.9

            est_distance = max(1, 100 - threat * 20 - delta * 10)
            console.clear()
            print(f"Blip detected at {heading_deg:.0f}°")
            print(f"Estimated distance: {est_distance:.0f} m")
            print(f"Current threat: {threat:.1f}   Field: {strength:.1f} μT   Δ: {delta:.2f}")

            def fade_and_reset():
                blip.alpha = 0.0

            ui.delay(fade_and_reset, 3.0)

            # Blip ping sound – COMMENTED OUT
            # sound.play_effect('ui:alert', volume=0.7, pitch=1.15, pan=0.0)
            # ui.delay(lambda: sound.play_effect('ui:alert', volume=0.4, pitch=0.95, pan=0.0), 0.25)

        # L1 beeps
        if 2.95 <= self.fil_voltage <= 3.35:
            interval = max(1.6 - (threat * 0.15), 0.12)
            pitch = BASE_PITCH + threat * 200
            vol = 0.35 + threat * 0.065
            sound.play_effect('ui:alert', volume=vol, pitch=pitch/440.0)
            ui.delay(lambda: None, interval)

    def will_close(self):
        motion.stop_updates()
        location.stop_updates()


if __name__ == '__main__':
    v = TrackerView()
    v.present('fullscreen')
    console.clear()
    print("Aliens Motion Tracker – Stable, Blip Sound Off")
    print("• Blips last 3 seconds and appear along sweep line")
    print("• Heading & distance printed to console on detection")
    print("• 'Head Contact' text + center red dot on high threat")
    print("• Rotate phone freely – no crashes")
    print("• Bring metal close to test")
