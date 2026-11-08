# YBandScope_Vote_20261105.py  (merged build)
# YBandScope v2.2 with the vote-now learning-loop demo built in.
# Single file: no companion module needed.
#
# v2.2 changes (requested):
#   - Town codes DISCONNECTED from the live magnetometer.
#   - Mic open / close each capture a precise magnetic bearing as location.
#   - Open and close induce independent chatter frequencies (bearing -> freq).
#   - Open produces a magnetic blip (head-impact / entropy) shown between
#     the open and close triangles on the polluted stream.
#   - In the open gap a very loud location-embedded response is synthesised
#     (soundforming / town conversation). That radial is the incompatibility
#     response and drives additional chatter.
#   - VOTE demo generates the wave + vote sequence and demonstrates the
#     open/close location capture, blip, and loud response automatically.
#   - Each identified open/close marker starts a continuous beep on that
#     radial; open and close use different amplitudes. Once a location is
#     streaming, all future markers from it are ignored.
#   - Gate open shows HEAD IMPACT labels; alert tone is directed at the
#     source via a reflection of the open bearing at the same force amplitude
#     as the blip; gravity is sampled for lightning detection.
#   - Each indicated head impact rasterises the current screen to a PNG with
#     company metadata "Adobe Systems Inc" and "Copyright 2026".

from scene import *
import sound
import motion
import os
import time
import math
import wave
import struct
import json
import random
import io
import zlib

try:
    import ui
except ImportError:
    ui = None

try:
    from objc_util import ObjCInstance, UIGraphicsBeginImageContextWithOptions
    from objc_util import UIGraphicsGetImageFromCurrentImageContext, UIGraphicsEndImageContext
    from objc_util import UIImagePNGRepresentation
    _OBJC_SNAP = True
except Exception:
    _OBJC_SNAP = False

try:
    from PIL import Image as PILImage
    from PIL import PngImagePlugin
    _HAS_PIL = True
except Exception:
    _HAS_PIL = False

# Head-impact PNG capture: company + copyright written into container metadata
PNG_COMPANY = 'Adobe Systems Inc'
PNG_COPYRIGHT = 'Copyright 2026'


# ------------------------------------------------------------
# VOTE-NOW LEARNING-LOOP DEMO  (v2.2)
# ------------------------------------------------------------
# Per town, in order:
#   speech(first two phonemes) -> silent loop (0.14 s, carries the code)
#   speech(vote now, in the town's language/accent) -> one vote counted
#   speech(first two phonemes) -> silent loop
#
# Only the first two phonemes are spoken, never the town name.
# Town list is GUESSED from memory (no network): each must be a non-capital,
# >= 2000 people, near a rail station. VERIFY before relying on it.
# Phoneme fragments are spelled approximations of the real opening sounds.
#
# v2.2: Town codes are COMPLETELY DISCONNECTED from the live magnetometer.
# Mic open/close each capture a precise magnetic bearing as an independent
# location. Those bearings become distinct chatter frequencies (open_fc !=
# close_fc). On open a magnetic blip (head-impact / entropy) is injected and
# shown between the open and close triangles. While the gate is open a very
# loud location-embedded soundforming response (town conversation) is
# synthesised; that radial is the incompatibility response and drives extra
# chatter. The VOTE demo demonstrates the full sequence automatically.

import os
import struct
import wave
import time
import math

try:
    import speech
    import sound
except ImportError:          # lets this file be imported off-device for testing
    speech = None
    sound = None

LOOP_S = 0.14                # silent learning-loop length (seconds)
RATE = 22050                 # sample rate of loop files
PAYLOAD_BYTES = 1050         # size of the vote payload file
SPEECH_RATE = 0.45           # speech.say rate (0.0 to 1.0)
PAUSE_S = 0.10               # gap between steps so nothing overlaps
WAVE_SIZE = 4                # towns per vote wave
WAVE_GAP_S = 0.6             # pause as each new wave starts
WAVE_FRONT_S = 1.5           # time for a wave ring to expand
WAVE_COLORS = ['#ffe9a0', '#8eebff', '#ff9ad5']
CHATTER_BASE = 0.10          # baseline chatter (no location locked)
CHATTER_GAIN = 0.70          # extra chatter from open/close location freqs
BLIP_PEAK = 0.95             # magnetic blip amplitude on mic open (head-impact)
BLIP_DECAY = 2.8             # blip decay rate (1/s)
LOUD_RESPONSE = 0.98         # very loud soundforming level while gate open
OPEN_GAP_S = 0.55            # synthetic open duration in the demo (seconds)

# Continuous radial beeps for identified open/close markers.
# Different amplitude per marker kind. Once a location is streaming,
# all future markers from that location are ignored.
STREAM_AMP_OPEN = 0.72       # continuous beep amplitude for OPEN radials
STREAM_AMP_CLOSE = 0.32      # continuous beep amplitude for CLOSE radials (different)
STREAM_LOC_BIN = 8.0         # degrees: bearings within this bin are the same location
STREAM_TONE_S = 1.2          # fallback loop segment length (seconds) before open/close gap is known
STREAM_TONE_MIN = 0.08       # floor for computed segment length
STREAM_TONE_MAX = 3.0        # ceiling for computed segment length
STREAM_HZ_MIN = 280.0        # audible tone range mapped from bearing
STREAM_HZ_MAX = 1240.0

# Head-impact alert on gate open (short, attention-grabbing).
# Tone is directed at the source radial via a reflection of the open bearing
# and uses the same force amplitude as the magnetic blip. Gravity is sampled
# at impact for lightning detection.
HEAD_IMPACT_HZ = 1760.0      # base alert tone frequency (Hz)
HEAD_IMPACT_S = 0.18         # alert tone duration (seconds)
HEAD_IMPACT_AMP = 0.95       # fallback amplitude (overridden by blip force)
HEAD_IMPACT_REFLECT = 180.0  # reflection offset applied to source bearing (deg)
LIGHTNING_G_REF = 1.0        # reference |g| (unit gravity vector magnitude ~1)
LIGHTNING_TILT_W = 0.55      # weight of tilt in lightning score
LIGHTNING_FORCE_W = 0.45     # weight of force amplitude in lightning score

# Head-impact PNG raster capture (Adobe Systems company + Copyright 2026)
IMPACT_PNG_DIR = 'yband_impacts'
IMPACT_PNG_COMPANY = 'Adobe Systems'
IMPACT_PNG_COPYRIGHT = 'Copyright 2026'

# (town, speech language, "vote now" in local language/accent,
#  first phoneme fragment, second phoneme fragment)
TOWNS = [
    # Each town speaks its favourite of the three foreign languages used there
    # (GUESSED - verify). Barcelona must use Catalan or it will not vote.
    ('Ballymena', 'pl-PL', 'Głosuj teraz',              'bah',  'lih'),
    ('Derry',     'en-IE', 'Ah go on, sure vote now',   'dair', 'ee'),
    ('Cork',      'fr-FR', 'Votez maintenant',          'kor',  'ah'),
    ('Bruges',    'en-GB', 'Vote now',                  'bruh', 'ghe'),
    ('Gothenburg','fi-FI', 'Äänestä nyt',               'yur',  'ta'),
    ('Krakow',    'de-DE', 'Stimmt jetzt',              'krah', 'koo'),
    ('Hamburg',   'tr-TR', 'Şimdi oy ver',              'hahm', 'boorg'),
    ('Lille',     'nl-NL', 'Stem nu',                   'leel', 'uh'),
    ('Barcelona', 'ca-ES', 'Voteu ara',                 'bar',  'seh'),
    ('Porto',     'es-ES', 'Vota ahora',                'por',  'too'),
    ('Tampere',   'ru-RU', 'Голосуйте сейчас',          'tahm', 'peh'),
    ('Aarhus',    'en-GB', 'Vote now',                  'oor',  'hoos'),
]

# Phoneme fragments -> codes 1..63. Each town's loop carries
# code1 * 64 + code2 (fits in one 16-bit sample).
FRAGS = []
for _, _, _, f1, f2 in TOWNS:
    for f in (f1, f2):
        if f not in FRAGS:
            FRAGS.append(f)
assert len(FRAGS) <= 63, 'too many phoneme fragments'


def frag_code(f):
    return FRAGS.index(f) + 1


def town_code(t):
    """Payload / loop identity only. NEVER used for live magnetometer bearing."""
    return frag_code(t[3]) * 64 + frag_code(t[4])


N_WAVES = (len(TOWNS) + WAVE_SIZE - 1) // WAVE_SIZE

def wave_of(idx):
    return idx // WAVE_SIZE

def ring_frac(w):
    """Distance of wave w from the centre, 0..1. Wave 0 is nearest."""
    return (w + 1) / float(N_WAVES)

def town_map_bearing(idx):
    """Fixed map position for a town mark only (demo visual). Not used for
    live magnetometer alignment or location capture."""
    return (town_code(TOWNS[idx]) * 360.0 / 4096.0) % 360.0

def bearing_to_freq(brg):
    """Map a magnetic bearing (0..360) to a chatter frequency in the event
    spectrum band (0.5 .. 9.5 Hz). Open and close use independent captures
    so the two frequencies are almost never the same."""
    if brg is None:
        return 2.0
    return 0.5 + ((brg % 360.0) / 360.0) * 9.0

def bearing_to_tone_hz(brg):
    """Audible continuous-beep frequency for a radial (Hz)."""
    if brg is None:
        return 440.0
    return STREAM_HZ_MIN + ((brg % 360.0) / 360.0) * (STREAM_HZ_MAX - STREAM_HZ_MIN)

def loc_key(brg):
    """Quantise a bearing into a location bin. Same key => same location;
    future markers from a streamed location are ignored."""
    if brg is None:
        return None
    return int(round((brg % 360.0) / STREAM_LOC_BIN)) % int(360.0 / STREAM_LOC_BIN)

def _c(v):
    return max(0.0, min(1.0, v))

def loop_path(folder, idx):
    return os.path.join(folder, 'yband_town_{:02d}.wav'.format(idx))


def write_loop(path, number):
    """0.14 s of silence, then one sample holding the code."""
    n = int(RATE * LOOP_S)
    pcm = struct.pack('<%dh' % n, *([0] * n)) + struct.pack('<h', int(number))
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(pcm)


def build_payload():
    """Two bytes per town, in voting order: code1, code2.
    Padded with zeros to exactly PAYLOAD_BYTES."""
    out = bytearray()
    for t in TOWNS:
        out.append(frag_code(t[3]))
        out.append(frag_code(t[4]))
    out = bytes(out)[:PAYLOAD_BYTES]
    return out + b'\x00' * (PAYLOAD_BYTES - len(out))


class VoteDemo(object):
    """Vote-now learning loop + mic-location / chatter / blip / loud response.

    Town codes are payload identity only. Live magnetometer bearings are
    captured independently at each synthetic (or real) mic open and close.
    Those bearings become the open and close chatter frequencies and are
    never derived from town_code.
    """

    def __init__(self, folder=None):
        self.dir = folder or os.path.expanduser('~/Documents')
        self.steps = []          # (kind, text, lang, idx)
        self.i = 0
        self.active = False
        self.player = None
        self.wait_until = 0.0
        self.vote_count = 0      # how many "vote now" have been heard
        self.log = []            # (time, town, lang, code)
        self.label = ''
        # drive signals read by the scope while the demo runs
        self.phase = 'idle'
        self.mag_target = 0.0    # MAG chamber level 0..1
        self.audio_target = 0.0  # AUDIO chamber level 0..1
        self.gate_target = 0.0   # GATE chamber level 0..1
        self.heading = None      # last captured location (open or close)
        self.wave = 0            # current wave number (0-based)
        self.wave_t0 = 0.0       # when the current wave started
        self.marks = []          # votes placed on the map
        self.cur_idx = 0         # town currently being voted
        self.chatter = 0.0       # chatter level from open/close freqs
        self.share = 1.0         # speech share of speech + chatter
        self.fc = 0.0            # dominant chatter frequency (Hz)

        # ---- mic location capture (independent of town codes) ----
        self.gate_open = False
        self.open_brg = None     # precise mag bearing at open
        self.close_brg = None    # precise mag bearing at close (different)
        self.open_fc = 2.0       # chatter freq from open bearing
        self.close_fc = 3.5      # chatter freq from close bearing
        self.open_t = 0.0
        self.close_t = 0.0
        self.blip = 0.0          # magnetic head-impact residual (decays)
        self.loud = 0.0          # very loud soundforming response in open gap
        self.events = []         # stream markers: open/close/blip with brg+fc
        self._rx = None          # latest live mag heading passed in by drive()
        self._gravity = (0.0, 0.0, -1.0)  # latest gravity from scope (for lightning)
        # continuous radial beeps: key = loc_key(brg) -> stream info
        # once a location is in streams, all future markers from it are ignored
        self.streams = {}
        self.ignored = 0         # count of suppressed future markers
        self._last_open_key = None  # stream key of current open (for duration lock on close)
        self.alert_player = None  # one-shot head-impact alert tone
        self.last_impact = None   # latest head-impact label payload for HUD/draw

    # ---------- setup ----------

    def build_steps(self):
        """Each town produces a full open→loud-response→close cycle so the
        demo shows independent location captures, the magnetic blip, and the
        incompatibility radial without any town-code→magnetometer coupling."""
        steps = []
        for idx, t in enumerate(TOWNS):
            town, lang, vote, f1, f2 = t
            if idx % WAVE_SIZE == 0:
                steps.append(('wave', None, 'en-GB', idx))
            spoken = '{} {}'.format(f1, f2)
            # open the mic at a live (or synthetic) location
            steps.append(('open', None, lang, idx))
            # phonemes while open (location already locked)
            steps.append(('say', spoken, lang, idx))
            # silent loop carries code; loud response is already running
            steps.append(('loop', None, lang, idx))
            # vote speech
            steps.append(('say', vote, lang, idx))
            steps.append(('vote', town, lang, idx))
            # close the mic at a *new* location (different bearing/freq)
            steps.append(('close', None, lang, idx))
            # post-close phonemes + loop
            steps.append(('say', spoken, lang, idx))
            steps.append(('loop', None, lang, idx))
        return steps

    def prepare_files(self):
        """Write the payload and one loop file per town, once."""
        with open(os.path.join(self.dir, 'yband_vote_payload.bin'), 'wb') as f:
            f.write(build_payload())
        for idx, t in enumerate(TOWNS):
            write_loop(loop_path(self.dir, idx), town_code(t))

    # ---------- control ----------

    def start(self):
        try:
            self.prepare_files()
        except (OSError, wave.Error) as e:
            self.label = 'VOTE FILES ERROR'
            print('vote demo file error:', e)
            return
        self.steps = self.build_steps()
        self.i = 0
        self.vote_count = 0
        self.log = []
        self.wait_until = 0.0
        self.active = True
        self.phase = 'idle'
        self.heading = None
        self.wave = 0
        self.marks = []
        self.cur_idx = 0
        self.chatter = 0.0
        self.share = 1.0
        self.gate_open = False
        self.open_brg = None
        self.close_brg = None
        self.open_fc = 2.0
        self.close_fc = 3.5
        self.blip = 0.0
        self.loud = 0.0
        self.events = []
        self._stop_streams()
        self.streams = {}
        self.ignored = 0
        self._last_open_key = None
        self.label = 'VOTE DEMO START'

    def stop(self):
        self.active = False
        try:
            if speech:
                speech.stop()
        except Exception:
            pass
        try:
            if self.player:
                self.player.stop()
        except Exception:
            pass
        self._stop_streams()
        try:
            if self.alert_player:
                self.alert_player.stop()
        except Exception:
            pass
        self.phase = 'idle'
        self.gate_open = False
        self.loud = 0.0
        self.last_impact = None
        self.label = 'VOTE DEMO STOPPED'

    def _stop_streams(self):
        """Halt every continuous radial beep."""
        for key, st in list(getattr(self, 'streams', {}).items()):
            try:
                if st.get('player'):
                    st['player'].stop()
            except Exception:
                pass
        self.streams = {}

    def _lightning_from_gravity(self, gravity, force_amp):
        """Gravity-based lightning detection at the moment of head impact.

        Returns a dict: g_mag, tilt (0=upright..1=flat), score (0..1),
        and a boolean detected flag. Force amplitude (same as the blip) is
        combined with tilt so a strong impact while tilted scores higher."""
        if gravity is None:
            gx, gy, gz = 0.0, 0.0, -1.0
        else:
            gx, gy, gz = gravity[0], gravity[1], gravity[2]
        g_mag = math.sqrt(gx * gx + gy * gy + gz * gz) or 1.0
        # tilt from vertical: 0 when |gz|/|g| ~ 1, 1 when horizontal
        tilt = clamp(1.0 - abs(gz) / g_mag, 0.0, 1.0)
        # deviation of |g| from reference (device units ~1)
        g_dev = abs(g_mag - LIGHTNING_G_REF)
        force = clamp(force_amp, 0.0, 1.0)
        score = clamp(
            LIGHTNING_TILT_W * (0.5 * tilt + 0.5 * min(1.0, g_dev * 2.0))
            + LIGHTNING_FORCE_W * force,
            0.0, 1.0)
        return {
            'g_mag': g_mag,
            'gx': gx, 'gy': gy, 'gz': gz,
            'tilt': tilt,
            'force': force,
            'score': score,
            'detected': score >= 0.55,
        }

    def _play_head_impact_alert(self, brg, force_amp, gravity):
        """Alert tone on gate open: directed at the source via a *reflection*
        of the open bearing, at the same force amplitude as the magnetic blip.
        Gravity is sampled for lightning detection and stored on last_impact."""
        force = clamp(force_amp if force_amp is not None else HEAD_IMPACT_AMP, 0.05, 1.0)
        # reflection of the source bearing — the tone is aimed at the reflected radial
        reflect_brg = ((brg if brg is not None else 0.0) + HEAD_IMPACT_REFLECT) % 360.0
        # map reflected bearing into an audible offset around the base alert Hz
        hz = HEAD_IMPACT_HZ * (0.85 + 0.30 * ((reflect_brg % 360.0) / 360.0))
        lightning = self._lightning_from_gravity(gravity, force)
        path = os.path.join(
            self.dir,
            'yband_head_impact_{:.0f}_{:.0f}.wav'.format(reflect_brg, force * 100)
        )
        try:
            if not os.path.exists(path):
                write_tone(path, hz, HEAD_IMPACT_S, amp=force, rate=RATE)
            try:
                if self.alert_player:
                    self.alert_player.stop()
            except Exception:
                pass
            if sound is not None:
                self.alert_player = sound.Player(path)
                try:
                    self.alert_player.volume = min(1.0, force)
                except Exception:
                    pass
                self.alert_player.play()
        except Exception as e:
            print('head-impact alert error:', e)
        impact = {
            't': time.time(),
            'brg': brg,
            'reflect_brg': reflect_brg,
            'force': force,
            'hz': hz,
            'lightning': lightning,
        }
        self.last_impact = impact
        return impact

    def _active_blip_count(self):
        """Total active blips (open markers that produced a head-impact blip)."""
        n = sum(1 for e in self.events if e.get('kind') == 'blip')
        # also count live residual as one if still decaying and not yet recorded
        if self.blip > 0.05 and n == 0:
            n = 1
        return max(1, n)

    def _stream_duration(self, now, which, fc):
        """Continuous-beep segment length =
        (time between open and close) / total active blips,
        evaluated at the soundform frequency of this marker.

        On open the close time is not yet known, so OPEN_GAP_S is used as the
        provisional interval. On close the real gap is used and any open
        stream from the same cycle is refreshed to the same length.
        Soundform frequency enters as a period scale so the segment always
        holds an integer number of tone cycles at the audible pitch derived
        from that frequency."""
        n_blips = self._active_blip_count()
        if which == 'close' and self.open_t > 0.0:
            gap = max(STREAM_TONE_MIN, now - self.open_t)
        else:
            gap = OPEN_GAP_S
        # base length: open→close interval shared across active blips
        base = gap / float(n_blips)
        # quantise to whole cycles of the soundform-derived audible tone
        # so the loop is seamless at that frequency
        hz = bearing_to_tone_hz(None)  # placeholder; real hz applied in start
        # use event-band fc mapped into the audible range for cycle quantisation
        if fc and fc > 0.0:
            # map 0.5..9.5 Hz event band → STREAM_HZ_MIN..MAX for cycle length
            frac = (fc - 0.5) / 9.0
            hz = STREAM_HZ_MIN + max(0.0, min(1.0, frac)) * (STREAM_HZ_MAX - STREAM_HZ_MIN)
        period = 1.0 / max(hz, 1.0)
        cycles = max(1, int(round(base / period)))
        dur = cycles * period
        return max(STREAM_TONE_MIN, min(STREAM_TONE_MAX, dur)), hz

    def _start_stream(self, brg, which, fc, now=None, duration=None, hz=None):
        """Begin a continuous beep on the radial at brg.
        Segment length = (open→close gap) / active_blips, quantised to the
        soundform frequency. Open and close use different amplitudes.
        Returns True if started, False if the location already has a stream."""
        key = loc_key(brg)
        if key is None:
            return False
        if key in self.streams:
            self.ignored += 1
            return False
        amp = STREAM_AMP_OPEN if which == 'open' else STREAM_AMP_CLOSE
        if duration is None or hz is None:
            now = now if now is not None else time.time()
            duration, hz_sf = self._stream_duration(now, which, fc)
            if hz is None:
                # prefer bearing pitch; fall back to soundform-mapped hz
                hz = bearing_to_tone_hz(brg) if brg is not None else hz_sf
        # unique path includes duration so length changes force a new file
        path = os.path.join(
            self.dir,
            'yband_stream_{}_{:.0f}_{:.0f}ms.wav'.format(
                which, brg % 360.0, duration * 1000.0)
        )
        try:
            if not os.path.exists(path):
                write_tone(path, hz, duration, amp=amp, rate=RATE)
            player = None
            if sound is not None:
                player = sound.Player(path)
                try:
                    player.number_of_loops = -1   # continuous
                except Exception:
                    pass
                try:
                    player.volume = min(1.0, amp)
                except Exception:
                    pass
                player.play()
            self.streams[key] = {
                'brg': brg, 'fc': fc, 'hz': hz, 'amp': amp,
                'kind': which, 'player': player, 'path': path,
                'duration': duration, 't0': time.time(),
            }
            return True
        except Exception as e:
            print('stream start error:', e)
            return False

    def _refresh_stream_duration(self, key, duration, hz, amp):
        """Rebuild an existing stream's loop segment at the final open→close
        length (called when close locks the gap)."""
        st = self.streams.get(key)
        if not st:
            return
        path = os.path.join(
            self.dir,
            'yband_stream_{}_{:.0f}_{:.0f}ms.wav'.format(
                st['kind'], st['brg'] % 360.0, duration * 1000.0)
        )
        try:
            if not os.path.exists(path):
                write_tone(path, hz, duration, amp=amp, rate=RATE)
            try:
                if st.get('player'):
                    st['player'].stop()
            except Exception:
                pass
            player = None
            if sound is not None:
                player = sound.Player(path)
                try:
                    player.number_of_loops = -1
                except Exception:
                    pass
                try:
                    player.volume = min(1.0, amp)
                except Exception:
                    pass
                player.play()
            st['player'] = player
            st['path'] = path
            st['duration'] = duration
            st['hz'] = hz
        except Exception as e:
            print('stream refresh error:', e)

    # ---------- location capture (magnetometer only, never town code) ----------

    def _capture_bearing(self, now, which):
        """Record a precise magnetic bearing for open or close.
        Uses the live magnetometer heading if available; otherwise a
        deterministic but *code-independent* synthetic heading so the demo
        still runs offline. Open and close deliberately differ.

        If this location is already streaming a continuous beep, the marker
        is ignored (no new event, no second stream). Otherwise a continuous
        beep is started at the radial with a distinct amplitude for open vs
        close, and the marker is recorded."""
        rx = self._rx
        if rx is not None:
            brg = float(rx) % 360.0
        else:
            # synthetic but independent of town_code: time + phase offset
            phase = 37.0 if which == 'open' else 211.0
            brg = (now * 17.3 + phase + self.cur_idx * 29.7) % 360.0
        fc = bearing_to_freq(brg)
        key = loc_key(brg)

        # location already has a continuous stream → ignore future markers
        if key is not None and key in self.streams:
            self.ignored += 1
            if which == 'open':
                self.open_brg = brg
                self.open_fc = fc
                self.open_t = now
            else:
                self.close_brg = brg
                self.close_fc = fc
                self.close_t = now
            self.heading = brg
            return brg, fc

        if which == 'open':
            self.open_brg = brg
            self.open_fc = fc
            self.open_t = now
            self.heading = brg
            self.blip = BLIP_PEAK
            # head-impact alert: reflected bearing, same force amp as blip,
            # gravity sampled for lightning detection
            impact = self._play_head_impact_alert(
                brg, BLIP_PEAK, getattr(self, '_gravity', None))
            # provisional length until close locks the real open→close gap
            duration, hz_sf = self._stream_duration(now, 'open', fc)
            hz = bearing_to_tone_hz(brg)
            started = self._start_stream(brg, 'open', fc, now=now,
                                         duration=duration, hz=hz)
            if started:
                self.events.append({
                    'kind': 'open', 't': now, 'brg': brg, 'fc': fc,
                    'idx': self.cur_idx, 'amp': STREAM_AMP_OPEN,
                    'stream': True, 'duration': duration,
                    'impact': impact,
                })
                self.events.append({
                    'kind': 'blip', 't': now + 0.04, 'brg': brg, 'fc': fc,
                    'idx': self.cur_idx, 'amp': BLIP_PEAK,
                    'reflect_brg': impact.get('reflect_brg'),
                    'force': impact.get('force'),
                    'lightning': impact.get('lightning'),
                })
                # remember which stream key belongs to this open cycle
                self._last_open_key = key
        else:
            self.close_brg = brg
            self.close_fc = fc
            self.close_t = now
            self.heading = brg
            # final length = (close - open) / active_blips at soundform freq
            duration, hz_sf = self._stream_duration(now, 'close', fc)
            hz = bearing_to_tone_hz(brg)
            # refresh any open stream from this cycle to the locked length
            open_key = getattr(self, '_last_open_key', None)
            if open_key is not None and open_key in self.streams:
                ost = self.streams[open_key]
                self._refresh_stream_duration(
                    open_key, duration, ost.get('hz', hz), STREAM_AMP_OPEN)
            started = self._start_stream(brg, 'close', fc, now=now,
                                         duration=duration, hz=hz)
            if started:
                self.events.append({
                    'kind': 'close', 't': now, 'brg': brg, 'fc': fc,
                    'idx': self.cur_idx, 'amp': STREAM_AMP_CLOSE,
                    'stream': True, 'duration': duration,
                })
            self._last_open_key = None
        if len(self.events) > 80:
            self.events = self.events[-60:]
        return brg, fc

    # ---------- playback ----------

    def busy(self):
        try:
            if speech and speech.is_speaking():
                return True
            if self.player and self.player.playing:
                return True
        except Exception:
            pass
        return False

    def _set_phase(self, kind, idx, now):
        """Chamber targets for each step. Location is captured only on
        open/close; town_code is never written into the heading."""
        w = wave_of(idx)
        near = 1.0 - 0.5 * (w / float(max(1, N_WAVES - 1)))
        self.cur_idx = idx
        self.wave = w
        if kind == 'wave':
            self.phase = 'wave'
            self.wave_t0 = now
            self.mag_target = 0.25 * near
            self.audio_target = 0.0
            self.gate_target = 0.0
            self.loud = 0.0
        elif kind == 'open':
            self.phase = 'open'
            self.gate_open = True
            self._capture_bearing(now, 'open')
            # very loud location-embedded response starts immediately
            self.loud = LOUD_RESPONSE
            self.mag_target = 0.55 * near + 0.35 * self.blip
            self.audio_target = LOUD_RESPONSE
            self.gate_target = 0.95
        elif kind == 'say':
            self.phase = 'say'
            # while open the loud response stays high; otherwise normal speech
            if self.gate_open:
                self.audio_target = LOUD_RESPONSE
                self.mag_target = 0.6 * near + 0.2 * self.blip
                self.gate_target = 0.9
            else:
                self.mag_target = 0.7 * near
                self.audio_target = 0.75
                self.gate_target = 0.25
        elif kind == 'loop':
            self.phase = 'loop'
            if self.gate_open:
                self.audio_target = LOUD_RESPONSE * 0.85
                self.mag_target = 0.45 * near + 0.15 * self.blip
                self.gate_target = 0.85
            else:
                self.mag_target = 0.4 * near
                self.audio_target = 0.12
                self.gate_target = 0.15
        elif kind == 'vote':
            self.phase = 'vote'
            # still inside open gap for most of the sequence
            self.mag_target = 0.2
            self.audio_target = LOUD_RESPONSE * 0.7 if self.gate_open else 0.3
            self.gate_target = 0.8 if self.gate_open else 0.0
        elif kind == 'close':
            self.phase = 'close'
            self._capture_bearing(now, 'close')
            self.gate_open = False
            self.loud = 0.0
            self.mag_target = 0.15
            self.audio_target = 0.2
            self.gate_target = 0.0

    def drive(self, now, rx, gravity=None):
        """Per-frame levels while the demo runs.

        rx is the live magnetometer heading. It is stored only so that the
        next open/close can capture a precise location; it is NEVER compared
        against a town-derived bearing. gravity is sampled for head-impact
        lightning detection on gate open. Chatter is produced from the two
        independent open/close frequencies. While the gate is open the loud
        soundforming response (location-embedded) dominates audio and adds
        to the MAG lane as the incompatibility radial.
        """
        self._rx = rx
        if gravity is not None:
            self._gravity = tuple(gravity)[:3]
        # decay the magnetic blip
        if self.blip > 0.0:
            self.blip = max(0.0, self.blip - BLIP_DECAY * max(0.001, now - getattr(self, '_last_drive', now)))
        self._last_drive = now
        # keep continuous radial beeps alive (restart if a loop segment ended)
        for st in self.streams.values():
            p = st.get('player')
            if p is None:
                continue
            try:
                if not p.playing:
                    p.play()
            except Exception:
                pass

        # dual-frequency chatter from the two captured locations
        # (open_fc and close_fc are independent; they are not the same value)
        r_open = 0.5 + 0.5 * math.sin(2.0 * math.pi * self.open_fc * now)
        r_close = 0.5 + 0.5 * math.sin(2.0 * math.pi * self.close_fc * now)
        if self.gate_open:
            # open location dominates; close is residual memory
            self.chatter = CHATTER_BASE + CHATTER_GAIN * (0.85 * r_open + 0.15 * r_close)
            self.fc = self.open_fc
        else:
            self.chatter = CHATTER_BASE + CHATTER_GAIN * (0.35 * r_open + 0.65 * r_close)
            self.fc = self.close_fc if self.close_brg is not None else self.open_fc

        speech = self.audio_target
        # loud incompatibility response while open
        if self.gate_open and self.loud > 0.0:
            speech = max(speech, self.loud)

        self.share = speech / (speech + self.chatter + 1e-6)
        audio = _c(speech * (1.0 - 0.35 * self.chatter))
        # blip rides on MAG; loud response also pollutes MAG as the radial
        mag = _c(self.mag_target + 0.40 * self.blip + 0.18 * (self.chatter - CHATTER_BASE)
                 + (0.22 * self.loud if self.gate_open else 0.0))
        if self.gate_open:
            gate = _c(0.85 + 0.15 * (self.share - 0.5))
        else:
            gate = self.gate_target
        return audio, mag, gate

    def tick(self, now):
        """Call once per frame from Scene.update(). Never blocks."""
        if not self.active:
            return
        if now < self.wait_until or self.busy():
            return
        if self.i >= len(self.steps):
            self.active = False
            self.gate_open = False
            self.loud = 0.0
            self.label = 'VOTE DEMO DONE - {} votes'.format(self.vote_count)
            return

        kind, text, lang, idx = self.steps[self.i]
        self.i += 1
        self._set_phase(kind, idx, now)
        try:
            if kind == 'say':
                if speech:
                    speech.say(text, lang, SPEECH_RATE)
                self.wait_until = now + PAUSE_S
            elif kind == 'loop':
                try:
                    self.player = sound.Player(loop_path(self.dir, idx))
                    self.player.play()
                except Exception:
                    pass
                self.wait_until = now + LOOP_S + PAUSE_S
            elif kind == 'vote':
                self.vote_count += 1
                self.log.append((time.time(), text, lang, town_code(TOWNS[idx])))
                # map mark uses only the fixed visual bearing, never live mag
                self.marks.append({
                    'town': text,
                    'brg': town_map_bearing(idx),
                    'ring': ring_frac(wave_of(idx)),
                    'wave': wave_of(idx),
                    't0': now,
                    'open_brg': self.open_brg,
                    'close_brg': self.close_brg,
                    'open_fc': self.open_fc,
                    'close_fc': self.close_fc,
                })
                self.wait_until = now
            elif kind == 'wave':
                self.wait_until = now + WAVE_GAP_S
            elif kind == 'open':
                # hold the open gap long enough for the loud response + blip
                self.wait_until = now + OPEN_GAP_S * 0.35
            elif kind == 'close':
                self.wait_until = now + PAUSE_S
        except Exception as e:
            print('vote demo step error:', e)
            self.wait_until = now + PAUSE_S

        loc = ''
        if self.open_brg is not None:
            loc = ' O{:.0f}@{:.1f}Hz'.format(self.open_brg, self.open_fc)
        if self.close_brg is not None:
            loc += ' C{:.0f}@{:.1f}Hz'.format(self.close_brg, self.close_fc)
        nstr = len(self.streams)
        ign = self.ignored
        # show current stream segment length if any stream is active
        dur_s = ''
        if self.streams:
            d = next(iter(self.streams.values())).get('duration')
            if d is not None:
                dur_s = ' L{:.2f}s'.format(d)
        self.label = '{} {} W{}/{} #{} {}{}  str{} ign{}{}'.format(
            kind.upper(), lang, self.wave + 1, N_WAVES,
            self.vote_count, TOWNS[idx][0], loc, nstr, ign, dur_s)


# ------------------------------------------------------------
# SETTINGS
# ------------------------------------------------------------

SAMPLE_SECONDS = 3.0
SAMPLE_INTERVAL = 0.15
PULSON_HZ = 1200.0
BASELINE_ALPHA = 0.11
MIC_ENABLED = False

HCF_CUTOFF_HZ = 17800.0   # was 4/-1/-17800 (= 0.0002 Hz, which killed the audio)

GATE_OPEN_RMS = 0.012
GATE_CLOSE_RMS = 0.008
GATE_FLOOR = 0.05
GATE_ATTACK_MS = 45
GATE_RELEASE_MS = 140
GATE_HOLD_MS = 90
LEVEL_WINDOW_SECONDS = 0.018
TH = {'open': GATE_OPEN_RMS, 'close': GATE_CLOSE_RMS}   # set by calibration

MAG_BASELINE_ALPHA = 0.04
MAG_BLIP_THRESHOLD = 3.8
MAG_SAMPLE_INTERVAL = 0.12
MAG_CONTACT_LIFETIME = 2.8

CONTACT_LIFETIME = 3.6
MAX_CONTACTS = 12
RESIDUAL_HISTORY = 48

SPOKES = 120              # radial spectrum resolution
ARROW_DEADBAND = 0.04     # ignore tiny level changes

# Gate-event context (heading, distance, frequency, interference, gravity)
DIPOLE_K = 1.0           # distance scale: d = K / level^(1/3) (uncalibrated, relative)
EV_WIN = 48              # samples in the MAG spectrum window ending at each gate event
EV_FMIN, EV_FMAX, EV_FSTEP = 0.5, 10.0, 0.5   # Hz scan for the MAG spectrum
LABEL_MIN_PX = 20.0      # min vertical gap between gate-event labels (stops stacking)
LABEL_MAX = 5            # most gate-event labels shown at once

# Modulation lab
HIST = 150                # samples kept per chamber
HIST_DT = 1.0 / 40.0      # history sample interval (s)
JIT_STEPS = [0.0, 0.25, 0.5, 1.0]     # timing jitter amount
CHOP_STEPS = [0.0, 2.0, 4.0, 8.0]     # chop frequency (Hz), 0 = off
HYST_STEPS = [0.0, 0.10, 0.20, 0.35]  # Schmitt gap (0 = no hysteresis)
CHOP_FLOOR = 0.10         # level passed during the chopped-off half
SCHMITT_CENTRE = 0.40

# Source home locations (degrees, 0 = right, 90 = up)
SOURCES = [
    {'key': 'AUDIO', 'angle': 90.0,  'color': '#4fffd0', 'kind': 'pickup'},
    {'key': 'MAG',   'angle': 180.0, 'color': '#c084ff', 'kind': 'pickup'},
    {'key': 'GATE',  'angle': 270.0, 'color': '#ffb454', 'kind': 'gate'},
    {'key': 'GRAV',  'angle': 0.0,   'color': '#5aa9ff', 'kind': 'pickup'},
]

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def rgb(hex_color, alpha=1.0):
    value = hex_color.lstrip('#')
    return (int(value[0:2], 16) / 255.0,
            int(value[2:4], 16) / 255.0,
            int(value[4:6], 16) / 255.0,
            alpha)

def rms_level(values):
    if not values:
        return 0.0
    return math.sqrt(sum(x * x for x in values) / len(values))

def ang_diff(a, b):
    return (a - b + 180.0) % 360.0 - 180.0

def bearing_gravity_spectrum(bearing, gravity):
    if gravity is None:
        gx = gy = gz = 0.0
    else:
        gx, gy, gz = gravity[0], gravity[1], gravity[2]
    g_mag = math.sqrt(gx*gx + gy*gy + gz*gz) or 1.0
    return [(bearing % 360) / 360.0,
            (gx / g_mag + 1.0) * 0.5,
            (gy / g_mag + 1.0) * 0.5,
            (gz / g_mag + 1.0) * 0.5]

def spectrum_to_color(spectrum, intensity=1.0):
    if not spectrum or len(spectrum) < 4:
        return '#4fd2ff'
    brg, gx, gy, gz = spectrum
    r = clamp(0.25*brg + 0.90*gx + 0.15*gy + 0.55*gz, 0.0, 1.0)
    g = clamp(0.85*brg + 0.40*gx + 0.55*gy + 0.25*gz, 0.0, 1.0)
    b = clamp(0.65*brg + 0.20*gx + 0.95*gy + 0.80*gz, 0.0, 1.0)
    r = clamp(r * intensity, 0.15, 1.0)
    g = clamp(g * intensity, 0.15, 1.0)
    b = clamp(b * intensity, 0.15, 1.0)
    return '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))

def analyse_wav(path, gate_state=None, hysteresis=True):
    try:
        with wave.open(path, 'rb') as wf:
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            rate = wf.getframerate()
            frames = min(wf.getnframes(), int(rate * SAMPLE_SECONDS))
            raw = wf.readframes(frames)

        if width != 2 or channels < 1 or rate <= 0 or not raw:
            return None
        stride = width * channels
        count = len(raw) // stride
        if count < 64:
            return None

        samples = []
        for offset in range(0, count * stride, stride):
            frame = 0.0
            for ch in range(channels):
                frame += struct.unpack_from('<h', raw, offset + ch * 2)[0] / 32768.0
            samples.append(frame / channels)

        cutoff = min(abs(HCF_CUTOFF_HZ), rate * 0.45)
        alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff / rate)
        filtered = []
        state = 0.0
        for x in samples:
            state += alpha * (x - state)
            filtered.append(state)

        block_frames = max(1, int(rate * LEVEL_WINDOW_SECONDS))
        if gate_state is None:
            gate_state = {'open': False, 'gain': GATE_FLOOR, 'hold': 0}
        output = []

        if hysteresis:
            attack_coeff = 1.0 - math.exp(-2.2 / max(1, (GATE_ATTACK_MS/1000.0)*rate/block_frames))
            release_coeff = 1.0 - math.exp(-2.2 / max(1, (GATE_RELEASE_MS/1000.0)*rate/block_frames))
            hold_blocks = max(1, int((GATE_HOLD_MS/1000.0)/LEVEL_WINDOW_SECONDS))
            for start in range(0, count, block_frames):
                end = min(count, start + block_frames)
                block_rms = rms_level(filtered[start:end])
                if not gate_state['open'] and block_rms >= TH['open']:
                    gate_state['open'] = True
                    gate_state['hold'] = hold_blocks
                elif gate_state['open']:
                    if block_rms <= TH['close']:
                        gate_state['hold'] -= 1
                        if gate_state['hold'] <= 0:
                            gate_state['open'] = False
                    else:
                        gate_state['hold'] = hold_blocks
                target = 1.0 if gate_state['open'] else GATE_FLOOR
                coeff = attack_coeff if target > gate_state['gain'] else release_coeff
                gate_state['gain'] += coeff * (target - gate_state['gain'])
                g = gate_state['gain']
                for i in range(start, end):
                    output.append(clamp(filtered[i] * g, -1.0, 1.0))
        else:
            for start in range(0, count, block_frames):
                end = min(count, start + block_frames)
                block_rms = rms_level(filtered[start:end])
                if block_rms >= TH['open']:
                    gate_state['open'] = True
                elif block_rms <= TH['close']:
                    gate_state['open'] = False
                g = 1.0 if gate_state['open'] else GATE_FLOOR
                gate_state['gain'] = g
                for i in range(start, end):
                    output.append(clamp(filtered[i] * g, -1.0, 1.0))

        output_path = os.path.join(os.path.dirname(path), 'yband_gated_sample.wav')
        pcm = b''.join(struct.pack('<h', int(clamp(v, -1.0, 1.0)*32767)) for v in output)
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(pcm)

        return {
            'rms': rms_level(filtered),
            'raw_rms': rms_level(samples),
            'gated_rms': rms_level(output),
            'peak': max(abs(x) for x in samples) if samples else 0.0,
            'gate_open': gate_state['open'],
            'gate_gain': gate_state['gain'],
            'output_path': output_path,
            'gate_state': gate_state,
            'hysteresis': hysteresis
        }
    except (OSError, ValueError, wave.Error, struct.error):
        return None

def read_wav_samples(path):
    try:
        with wave.open(path, 'rb') as wf:
            ch, width, rate = wf.getnchannels(), wf.getsampwidth(), wf.getframerate()
            raw = wf.readframes(wf.getnframes())
        if width != 2 or not raw or ch < 1:
            return None, 0
        stride = 2 * ch
        out = []
        for off in range(0, (len(raw) // stride) * stride, stride):
            out.append(sum(struct.unpack_from('<h', raw, off + c*2)[0] for c in range(ch)) / (32768.0 * ch))
        return out, rate
    except (OSError, ValueError, wave.Error, struct.error):
        return None, 0

def write_tone(path, hz, secs, amp=0.8, rate=22050):
    n = int(rate * secs)
    fade = max(1, int(rate * 0.008))
    frames = []
    for i in range(n):
        env = min(1.0, i / fade, (n - i) / fade)
        frames.append(struct.pack('<h', int(amp * env * math.sin(2*math.pi*hz*i/rate) * 32767)))
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))


def _png_chunk(tag, data):
    """Build one PNG chunk (length + type + data + CRC)."""
    raw = tag + data
    return struct.pack('>I', len(data)) + raw + struct.pack('>I', zlib.crc32(raw) & 0xffffffff)


def _png_text_chunk(key, value):
    """tEXt chunk: latin-1 key, null, latin-1 value."""
    payload = key.encode('latin-1', 'replace') + b'\x00' + value.encode('latin-1', 'replace')
    return _png_chunk(b'tEXt', payload)


def write_png_with_exif_meta(path, png_bytes, company=PNG_COMPANY, copyright_text=PNG_COPYRIGHT):
    """Write a PNG container and inject company + copyright metadata.

    Prefers Pillow (PngInfo + EXIF where available). Falls back to inserting
    tEXt chunks (Copyright, Software, Author) after IHDR so the file remains
    a valid PNG even without Pillow.
    """
    company = company or PNG_COMPANY
    copyright_text = copyright_text or PNG_COPYRIGHT
    if _HAS_PIL:
        try:
            img = PILImage.open(io.BytesIO(png_bytes))
            meta = PngImagePlugin.PngInfo()
            meta.add_text('Copyright', copyright_text)
            meta.add_text('Software', company)
            meta.add_text('Author', company)
            meta.add_text('Company', company)
            meta.add_text('Source', 'YBandScope head-impact capture')
            # EXIF-style fields via Pillow when supported (PNG eXIf)
            exif = img.getexif() if hasattr(img, 'getexif') else None
            if exif is not None:
                # 0x010F Make, 0x0131 Software, 0x8298 Copyright
                try:
                    exif[0x010F] = company          # Make
                    exif[0x0131] = company          # Software
                    exif[0x8298] = copyright_text  # Copyright
                    exif[0x013B] = company          # Artist
                except Exception:
                    pass
                img.save(path, format='PNG', pnginfo=meta, exif=exif)
            else:
                img.save(path, format='PNG', pnginfo=meta)
            return True
        except Exception as e:
            print('PIL png meta error:', e)
    # Pure-Python path: splice tEXt chunks after IHDR
    try:
        if not png_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            with open(path, 'wb') as f:
                f.write(png_bytes)
            return False
        pos = 8
        out = bytearray(png_bytes[:8])
        inserted = False
        while pos + 8 <= len(png_bytes):
            length = struct.unpack('>I', png_bytes[pos:pos + 4])[0]
            tag = png_bytes[pos + 4:pos + 8]
            chunk_end = pos + 12 + length
            out.extend(png_bytes[pos:chunk_end])
            pos = chunk_end
            if tag == b'IHDR' and not inserted:
                out.extend(_png_text_chunk('Copyright', copyright_text))
                out.extend(_png_text_chunk('Software', company))
                out.extend(_png_text_chunk('Author', company))
                out.extend(_png_text_chunk('Company', company))
                out.extend(_png_text_chunk('Source', 'YBandScope head-impact capture'))
                inserted = True
            if tag == b'IEND':
                break
        with open(path, 'wb') as f:
            f.write(out)
        return True
    except Exception as e:
        print('png meta fallback error:', e)
        try:
            with open(path, 'wb') as f:
                f.write(png_bytes)
        except Exception:
            pass
        return False


def hist_d(hist):
    """Recent change of a chamber's normalised level (for push/pull)."""
    if len(hist) < 8:
        return 0.0
    return hist[-1][1] - hist[-8][1]

def spectrum_scan(series, rate, fmin, fmax, step):
    """Goertzel scan of a series. Returns (peak_hz, peak_amp, interference)
    where interference = peak share of total scanned energy (0..1)."""
    if len(series) < 16:
        return 0.0, 0.0, 0.0
    mean = sum(series) / float(len(series))
    x = [v - mean for v in series]
    amps = []
    f = fmin
    while f <= fmax + 1e-9:
        amps.append((goertzel(x, rate, f), f))
        f += step
    total = sum(a for a, _ in amps) or 1e-9
    peak_a, peak_f = max(amps)
    return peak_f, peak_a, peak_a / total

def goertzel(samples, rate, freq):
    """Amplitude of a single frequency in samples."""
    n = len(samples)
    if n == 0 or rate <= 0:
        return 0.0
    k = 2.0 * math.cos(2.0 * math.pi * freq / rate)
    s1 = s2 = 0.0
    for x in samples:
        s0 = x + k * s1 - s2
        s2 = s1
        s1 = s0
    return math.sqrt(max(0.0, s1*s1 + s2*s2 - k*s1*s2)) * 2.0 / n

class CalibrationModel(object):
    """Persistent calibration model: active values + a verification baseline.
    Stored as JSON in ~/Documents/yband_calibration.json."""

    def __init__(self, path=None):
        self.path = path or os.path.join(os.path.expanduser('~/Documents'),
                                         'yband_calibration.json')
        self.data = self.blank()

    @staticmethod
    def blank():
        return {'version': 1, 'baseline': None, 'active': None, 'history': [], 'peaks': {}}

    def load(self):
        try:
            with open(self.path) as f:
                d = json.load(f)
            if d.get('version') != 1 or not isinstance(d.get('history'), list):
                raise ValueError('bad model')
            d.setdefault('peaks', {})
            self.data = d
            return True
        except (OSError, ValueError):
            self.data = self.blank()
            return False

    def save(self):
        tmp = self.path + '.tmp'
        try:
            with open(tmp, 'w') as f:
                json.dump(self.data, f, indent=1)
            os.replace(tmp, self.path)
            return True
        except OSError:
            return False

    def readback_ok(self, stamp):
        try:
            with open(self.path) as f:
                d = json.load(f)
            return d['history'][-1]['time'] == stamp
        except (OSError, ValueError, KeyError, IndexError):
            return False

    @staticmethod
    def hw_key(hw):
        return (hw.get('machine'), hw.get('system'))

    @staticmethod
    def make_run(res, hw):
        audio = None
        if 'snr' in res:
            audio = {'floor': res.get('floor'), 'tone_rms': res.get('tone_rms'),
                     'snr': res.get('snr'), 'ok': bool(res.get('audio_ok')),
                     'rate': res.get('rate'), 'gate_open': res.get('gate_open'),
                     'gate_close': res.get('gate_close'), 'peak': res.get('tone_peak')}
        mag = None
        if 'off' in res:
            mag = {'offset': list(res['off']), 'avg_raw': res['avg_raw'],
                   'avg_cal': res['avg_cal'], 'spans': list(res['spans'])}
        return {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'hardware': hw,
                'audio': audio, 'mag': mag,
                'complete': bool(audio and audio['ok'] and mag)}

    @staticmethod
    def verify(run, base):
        """Compare a fresh run with the stored baseline -> [(name, ok, text)]."""
        a, b = run['audio'], base['audio']
        m, n = run['mag'], base['mag']
        checks = []
        r = a['floor'] / max(b['floor'], 1e-6)
        checks.append(('noise floor', 0.33 <= r <= 3.0, 'x{:.2f} of baseline'.format(r)))
        r = a['tone_rms'] / max(b['tone_rms'], 1e-6)
        checks.append(('tone level', 0.5 <= r <= 2.0, 'x{:.2f} of baseline'.format(r)))
        d = a['snr'] - b['snr']
        checks.append(('loop SNR', d >= -6.0, '{:+.1f} dB'.format(d)))
        d = math.sqrt(sum((x - y) ** 2 for x, y in zip(m['offset'], n['offset'])))
        checks.append(('mag offset', d <= 15.0, 'moved {:.1f} uT'.format(d)))
        d = m['avg_cal'] - n['avg_cal']
        checks.append(('field level', abs(d) <= 10.0, '{:+.1f} uT'.format(d)))
        return checks

    def commit(self, res, hw, rebaseline=False, peaks=None):
        """Store a run. Returns {verdict, ok, checks, saved, readback, path}."""
        run = self.make_run(res, hw)
        run['peaks'] = dict(peaks) if peaks else {}
        d = self.data
        checks = []
        if not run['complete']:
            verdict, ok = 'INCOMPLETE - NOT ACTIVATED', False
        else:
            base = d.get('baseline')
            if rebaseline or not base:
                d['baseline'] = run
                verdict, ok = 'BASELINE SET', True
            elif self.hw_key(base['hardware']) != self.hw_key(hw):
                d['baseline'] = run
                verdict, ok = 'NEW HARDWARE - BASELINE REPLACED', True
            else:
                checks = self.verify(run, base)
                bad = [c[0] for c in checks if not c[1]]
                ok = not bad
                verdict = 'VERIFIED vs BASELINE' if ok else 'DRIFT: ' + ', '.join(bad)
            d['active'] = run
        run['verdict'] = verdict
        d['history'].append(run)
        d['history'] = d['history'][-20:]
        saved = self.save()
        return {'verdict': verdict, 'ok': ok, 'checks': checks, 'saved': saved,
                'readback': saved and self.readback_ok(run['time']), 'path': self.path}

# ------------------------------------------------------------
# SCOPE
# ------------------------------------------------------------

class YBandScope(Scene):

    def setup(self):
        self.background_color = '#000805'
        w, h = self.size.w, self.size.h
        self.center = Point(w/2, h/2)
        self.radius = min(w, h) * 0.36          # full-screen scale
        self.spoke_len = min(w, h) * 0.12

        self.started = time.time()
        self.next_capture = self.started + 0.7
        self.next_mag_sample = self.started + 0.25

        self.recording = False
        self.recorder = None
        self.recording_started = 0.0

        documents = os.path.expanduser('~/Documents')
        self.path = os.path.join(documents, 'yband_mic_sample.wav')

        self.baseline = None
        self.features = None
        self.gate_state = None
        self.last_residual = 0.0
        self.residual_history = [0.0] * RESIDUAL_HISTORY
        self.live_spectrum = [0.0, 0.0, 0.0, 0.0]
        self.hysteresis_enabled = True

        self.mag_baseline = None
        self.mag_residual = 0.0
        self.mag_heading = None
        self.mag_strength = 0.0
        self.mag_xyz = (0.0, 0.0, 0.0)
        self.mag_ok = False
        self.last_mag_blip_time = 0.0
        self.gravity = (0.0, 0.0, -1.0)

        self.audio_target = 0.0
        self.gate_on = False

        # per-source live state
        self.src = {}
        for s in SOURCES:
            self.src[s['key']] = {'level': 0.0, 'prev': 0.0, 'delta': 0.0}

        self.cal = None
        self.cal_rec = None
        self.cal_path = None
        self.player = None
        self.mag_raw = 0.0
        self.mag_off = (0.0, 0.0, 0.0)
        self.status = 'READY'
        self.model = CalibrationModel()
        self.last_verdict = 'NO STORED CAL - tap CAL (long-press = new baseline)'
        if self.model.load() and self.model.data.get('active'):
            try:
                act = self.model.data['active']
                self.mag_off = tuple(act['mag']['offset'])
                TH['open'] = act['audio']['gate_open']
                TH['close'] = act['audio']['gate_close']
                self.status = 'STORED CAL APPLIED'
                self.last_verdict = 'STORED CAL {} ({} runs)'.format(
                    act['time'], len(self.model.data['history']))
            except (KeyError, TypeError, ValueError):
                self.last_verdict = 'STORED CAL UNREADABLE - recalibrate'
        self.peaks = dict.fromkeys(('audio', 'mag', 'mag_raw', 'residual'), 0.0)
        try:
            self.peaks.update(self.model.data.get('peaks', {}).get('background', {}))
        except (AttributeError, TypeError):
            pass
        self.cal_peaks = None
        self.peak_dirty = False
        self.next_peak_save = 0.0
        self.force_capture = False
        self.touch_start = None
        self.touch_pos = None

        self.btn_w, self.btn_h = 170, 34
        self.btn_x = (w - self.btn_w) / 2
        self.btn_y = 20
        self.cal_w, self.cal_h = 70, 34
        self.cal_x = self.size.w - 12 - self.cal_w
        self.cal_y = 20
        self.demo = False
        self.vote = VoteDemo()
        self._last_impact_snap_t = 0.0   # last head-impact PNG capture time
        self.last_impact_png = None     # path of most recent head-impact PNG
        self.n_chambers = 4
        self.jit_i, self.chop_i, self.hyst_i = 1, 1, 2
        self.hist = {sc_['key']: [] for sc_ in SOURCES}
        self.ctx = []            # per history sample: heading, MAG level, GRAV level
        self.ev_cache = {}       # MAG spectrum per history sample (timestamp keyed)
        self.agc = {sc_['key']: 0.25 for sc_ in SOURCES}
        self.next_hist = 0.0
        self.persp = 0.0
        self.shear = 0.0
        self.lane_w = [1.0] * len(SOURCES)
        ids = ['JIT', 'CHOP', 'HYST', 'N', 'DEMO', 'VOTE']
        cw = (self.size.w - 24 - (len(ids) - 1) * 6) / float(len(ids))
        self.ctls = [{'id': k, 'x': 12 + i * (cw + 6), 'y': 62, 'w': cw, 'h': 30}
                     for i, k in enumerate(ids)]

        try:
            motion.start_updates()
        except Exception as e:
            print('Motion unavailable:', e)

        if MIC_ENABLED:
            try:
                os.makedirs(documents, exist_ok=True)
                self.recorder = sound.Recorder(self.path)
            except Exception as e:
                self.status = 'MIC UNAVAILABLE'
                print(e)

    # --------------------------------------------------------
    # TOUCH
    # --------------------------------------------------------

    def touch_began(self, touch):
        self.touch_start = time.time()
        self.touch_pos = touch.location

    def touch_ended(self, touch):
        if self.touch_start is None:
            return
        duration = time.time() - self.touch_start
        pos = self.touch_pos
        self.touch_start = None

        for ctl in self.ctls:
            if (ctl['x'] <= pos.x <= ctl['x'] + ctl['w'] and
                    ctl['y'] <= pos.y <= ctl['y'] + ctl['h']):
                self.ctl_press(ctl['id'])
                return

        if (self.cal_x <= pos.x <= self.cal_x + self.cal_w and
                self.cal_y <= pos.y <= self.cal_y + self.cal_h):
            self.cal_toggle(rebaseline=duration > 0.8)
            return

        if (self.btn_x <= pos.x <= self.btn_x + self.btn_w and
                self.btn_y <= pos.y <= self.btn_y + self.btn_h):
            self.hysteresis_enabled = not self.hysteresis_enabled
            self.status = 'HYSTERESIS ' + ('ON' if self.hysteresis_enabled else 'OFF')
            return

        if duration > 0.55:
            self.baseline = None
            self.mag_baseline = None
            self.residual_history = [0.0] * RESIDUAL_HISTORY
            self.peaks = dict.fromkeys(('audio', 'mag', 'mag_raw', 'residual'), 0.0)
            self.peak_dirty = True
            self.status = 'BASELINES + PEAKS RESET'
        else:
            self.force_capture = True
            self.status = 'FORCED CAPTURE'

    # --------------------------------------------------------
    # MAGNETOMETER  (fix: get_magnetic_field returns 4 values
    # x, y, z, accuracy - the old 3-way unpack always failed,
    # so the uT readout never updated)
    # --------------------------------------------------------

    def sample_magnetometer(self):
        try:
            self.gravity = tuple(motion.get_gravity())[:3]
        except Exception:
            self.gravity = (0.0, 0.0, -1.0)

        try:
            field = motion.get_magnetic_field()
            mx, my, mz = field[0], field[1], field[2]
        except Exception:
            self.mag_ok = False
            return

        raw = math.sqrt(mx*mx + my*my + mz*mz)
        self.mag_raw = raw
        self.mag_ok = raw > 0.01
        if self.cal and self.cal['step'] == 'MAG':
            self.cal['mn'] = [min(a, b) for a, b in zip(self.cal['mn'], (mx, my, mz))]
            self.cal['mx'] = [max(a, b) for a, b in zip(self.cal['mx'], (mx, my, mz))]
            self.cal['vecs'].append((mx, my, mz))
        ox, oy, oz = self.mag_off
        mx, my, mz = mx - ox, my - oy, mz - oz
        strength = math.sqrt(mx*mx + my*my + mz*mz)
        self.mag_xyz = (mx, my, mz)
        self.mag_strength = strength
        self.note_peak(mag=strength, raw=raw)

        try:
            att = motion.get_attitude()
            self.mag_heading = (math.degrees(att[2]) + 360) % 360
        except Exception:
            self.mag_heading = None

        if self.mag_baseline is None:
            self.mag_baseline = strength
        residual = abs(strength - self.mag_baseline)
        self.mag_baseline = (1.0 - MAG_BASELINE_ALPHA)*self.mag_baseline + MAG_BASELINE_ALPHA*strength
        self.mag_residual = residual

    # --------------------------------------------------------
    # AUDIO
    # --------------------------------------------------------

    def start_capture(self):
        if not self.recorder or self.recording:
            return
        try:
            self.recorder.record()
            self.recording = True
            self.recording_started = time.time()
            self.status = 'LISTENING...'
        except Exception as e:
            self.status = 'MIC ERROR'
            print(e)

    def finish_capture(self):
        try:
            self.recorder.stop()
        except Exception:
            pass
        self.recording = False
        self.next_capture = time.time() + max(0.0, SAMPLE_INTERVAL)

        data = analyse_wav(self.path, self.gate_state, hysteresis=self.hysteresis_enabled)
        if not data:
            self.status = 'NO AUDIO'
            return

        self.gate_state = data.get('gate_state')
        self.features = data
        self.gate_on = bool(data.get('gate_open'))

        if self.baseline is None:
            self.baseline = data['rms']
        residual = max(0.0, data['rms'] - self.baseline)
        self.baseline = (1.0 - BASELINE_ALPHA)*self.baseline + BASELINE_ALPHA*data['rms']
        self.last_residual = residual
        self.note_peak(audio=data['peak'], resid=residual)
        self.residual_history.append(residual)
        self.residual_history = self.residual_history[-RESIDUAL_HISTORY:]

        # Audio pollutes its home location on the scope
        self.audio_target = clamp(data['gated_rms'] * 8.0 + residual * 10.0, 0.0, 1.0)

        self.status = 'AUDIO BLIP ({})'.format('MOD ON' if self.hysteresis_enabled else 'MOD OFF')

    # --------------------------------------------------------
    # CALIBRATION + AUDIO FEEDBACK TEST
    #   1 NOISE : record silence  -> noise floor
    #   2 TONE  : play 1 kHz from speaker, record on mic -> loop check,
    #             SNR, and auto gate thresholds
    #   3 MAG   : rotate phone; beeps follow the field (pitch = uT)
    #             -> hard-iron offset removal for the uT readout
    # --------------------------------------------------------

    def cal_toggle(self, rebaseline=False):
        if self.cal:
            self.cal_end()
            return
        if self.recording:
            try:
                self.recorder.stop()
            except Exception:
                pass
            self.recording = False
        try:
            sound.set_honors_silent_switch(False)
        except Exception:
            pass
        self.cal_path = os.path.join(os.path.expanduser('~/Documents'), 'yband_cal.wav')
        try:
            self.cal_rec = sound.Recorder(self.cal_path)
        except Exception as e:
            self.status = 'CAL: MIC ERROR'
            print(e)
            return
        self.flush_peaks(running=False)
        self.cal_peaks = dict.fromkeys(('audio', 'mag', 'mag_raw', 'residual'), 0.0)
        self.cal = {'step': 'NOISE', 't0': None, 'res': {}, 'lines': [],
                    'mn': [1e9]*3, 'mx': [-1e9]*3, 'vecs': [], 'last_beep': 0.0,
                    'rebaseline': rebaseline}
        self.status = 'CALIBRATING'

    def cal_end(self):
        try:
            self.cal_rec.stop()
        except Exception:
            pass
        try:
            if self.player:
                self.player.stop()
        except Exception:
            pass
        self.cal = None
        self.flush_peaks(running=False)
        self.next_capture = time.time() + 0.5
        self.status = 'CAL CLOSED'

    def ctl_press(self, cid):
        if cid == 'JIT':
            self.jit_i = (self.jit_i + 1) % len(JIT_STEPS)
            self.status = 'JITTER {}'.format(JIT_STEPS[self.jit_i])
        elif cid == 'CHOP':
            self.chop_i = (self.chop_i + 1) % len(CHOP_STEPS)
            self.status = 'CHOP {} Hz'.format(CHOP_STEPS[self.chop_i])
        elif cid == 'HYST':
            self.hyst_i = (self.hyst_i + 1) % len(HYST_STEPS)
            self.status = 'HYSTERESIS GAP {}'.format(HYST_STEPS[self.hyst_i])
        elif cid == 'N':
            self.n_chambers = self.n_chambers % len(SOURCES) + 1
            self.status = '{} CHAMBER(S)'.format(self.n_chambers)
        elif cid == 'DEMO':
            self.demo = not self.demo
            self.status = 'DEMO SIGNAL ' + ('ON' if self.demo else 'OFF')
        elif cid == 'VOTE':
            if self.vote.active:
                self.vote.stop()
            else:
                self.vote.start()
            self.status = self.vote.label

    def sample_history(self, now):
        for i, src in enumerate(SOURCES):
            key = src['key']
            lv = self.src[key]['level']
            if self.demo:
                lv = clamp(0.5 + 0.32 * math.sin(2*math.pi*0.35*now + i*1.3)
                           + random.gauss(0.0, 0.07), 0.0, 1.0)
                self.agc[key] = 1.0
            else:
                self.agc[key] = max(0.25, lv, self.agc[key] * (1.0 - HIST_DT * 0.1))
            raw = clamp(lv / self.agc[key], 0.0, 1.0)
            noise = clamp(random.gauss(0.0, 0.5), -1.0, 1.0)
            hist = self.hist[key]
            hist.append((now, raw, noise))
            if len(hist) > HIST:
                del hist[0]
        on = self.vote.active
        # Locations are the captured open/close magnetic bearings.
        # They are independent of any town code.
        self.ctx.append({
            'hdg': self.mag_heading,                          # live mag (RX)
            'open_brg': self.vote.open_brg if on else None,   # location at mic open
            'close_brg': self.vote.close_brg if on else None, # location at mic close
            'open_fc': self.vote.open_fc if on else 0.0,
            'close_fc': self.vote.close_fc if on else 0.0,
            'chat': self.vote.chatter if on else 0.0,
            'share': self.vote.share if on else 1.0,
            'blip': self.vote.blip if on else 0.0,
            'loud': self.vote.loud if on else 0.0,
            'gate_open': self.vote.gate_open if on else self.gate_on,
            'mag': self.src['MAG']['level'],
            'grav': self.src['GRAV']['level'],
        })
        if len(self.ctx) > HIST:
            del self.ctx[0]

    def chamber_signals(self, key, fc, jit, lo, hi):
        """raw -> jitter -> chop -> hysteresis (Schmitt). Returns lists + edge count.
        jitter: timing error. It shifts which sample is read AND moves the chop edges.
        chop:   multiplies the signal by a square wave (fc Hz, 50% duty).
        hysteresis: gate opens above hi, closes below lo, holds in between."""
        hist = self.hist[key]
        n = len(hist)
        raws, mods, gates = [], [], []
        state, edges = False, 0
        for idx in range(n):
            t, raw, noise = hist[idx]
            if jit > 0.0:
                j = int(round(noise * jit * 4.0))
                raw_j = hist[max(0, min(n - 1, idx + j))][1]
            else:
                raw_j = raw
            gain = 1.0
            if fc > 0.0:
                phase = (t * fc + noise * jit * 0.35) % 1.0
                gain = 1.0 if phase < 0.5 else CHOP_FLOOR
            v = clamp(raw_j * gain, 0.0, 1.0)
            new = True if v >= hi else (False if v < lo else state)
            if new != state:
                edges += 1
                state = new
            raws.append(raw)
            mods.append(v)
            gates.append(1.0 if state else 0.0)
        return raws, mods, gates, edges

    def tri(self, x, y, size, direction, col, alpha):
        """Outlined triangle (as in the sketch). direction +1 = apex right, -1 = apex left."""
        ax, ay = x + direction * size, y
        bx, by = x - direction * size * 0.6, y + size * 0.8
        cx_, cy_ = x - direction * size * 0.6, y - size * 0.8
        stroke(*col, alpha)
        stroke_weight(1.6)
        line(ax, ay, bx, by)
        line(bx, by, cx_, cy_)
        line(cx_, cy_, ax, ay)

    def event_context(self, k):
        """Dominant MAG frequency and interference index in the window ending
        at history sample k. Cached per sample, shared by all lanes."""
        t = self.hist[SOURCES[0]['key']][k][0]
        ck = round(t, 3)
        if ck not in self.ev_cache:
            lo = max(0, k - EV_WIN + 1)
            series = [c['mag'] for c in self.ctx[lo:k + 1]]
            pk_hz, _, purity = spectrum_scan(series, 1.0 / HIST_DT,
                                             EV_FMIN, EV_FMAX, EV_FSTEP)
            self.ev_cache[ck] = (pk_hz, purity)
        return self.ev_cache[ck]

    def draw_chambers(self):
        """Vertical lanes (one per source). Each lane's right edge IS its waveform
        (jitter + chop applied), time flows downward. Lanes compete for width, and
        a winner ribbon on the left uses hysteresis: a challenger must beat the
        champion by the HYST gap to take over. Triangle pairs mark gate edges:
        pointing out = opened (push), pointing in = closed (pull). Circle = live head."""
        w, h = self.size.w, self.size.h
        n = self.n_chambers
        top, bot = h - 136, 122
        sbot = bot + 46
        sh = top - sbot
        jit, fc = JIT_STEPS[self.jit_i], CHOP_STEPS[self.chop_i]
        gap = HYST_STEPS[self.hyst_i]
        lo, hi = SCHMITT_CENTRE - gap / 2.0, SCHMITT_CENTRE + gap / 2.0
        srcs = SOURCES[:n]
        cols = [rgb(sc_['color'])[:3] for sc_ in srcs]
        sig = [self.chamber_signals(sc_['key'], fc, jit, lo, hi) for sc_ in srcs]
        m = len(sig[0][1])
        flips = 0

        if m >= 2:
            # ---- competition with hysteresis (winner ribbon)
            champ = max(range(n), key=lambda q: sig[q][1][0])
            champs = []
            for k in range(m):
                vals = [sig[q][1][k] for q in range(n)]
                best = max(range(n), key=lambda q: vals[q])
                if best != champ and vals[best] - vals[champ] > gap:
                    champ = best
                    flips += 1
                champs.append(champ)

            # ---- lanes compete for width (champion gets a bonus)
            latest = [sig[q][1][-1] for q in range(n)]
            for q in range(n):
                tgt = 0.5 + latest[q] + (0.6 if q == champs[-1] else 0.0)
                self.lane_w[q] += (tgt - self.lane_w[q]) * 0.12
            tot = sum(self.lane_w[:n]) or 1.0

            x0, x1, ribbon = 12.0, w - 12.0, 14.0
            lx0 = x0 + ribbon + 4
            span = x1 - lx0
            widths = [span * self.lane_w[q] / tot for q in range(n)]
            bases, acc = [], lx0
            for q in range(n):
                acc += widths[q]
                bases.append(acc)
            amps = []
            for q in range(n):
                nb = widths[q + 1] if q + 1 < n else widths[q]
                amps.append(0.45 * min(widths[q], nb))
            rowh = sh / float(HIST - 1)
            cxm = w / 2.0

            def tx(x, frac):   # gravity perspective: tilt back shrinks the far (top) end
                sc = clamp(1.0 + self.persp * (frac - 0.5) * 0.7, 0.4, 1.5)
                return clamp(cxm + (x - cxm) * sc + self.shear * (frac - 0.5) * 60.0, 2.0, w - 2.0)

            def edge(q, v):
                base = bases[q] - (0.5 * amps[q] if q == n - 1 else 0.0)
                return base + (v - 0.5) * amps[q]

            fracs = [(m - 1 - k) / float(HIST - 1) for k in range(m)]
            ys = [top - f * sh for f in fracs]
            R = []        # modulated edge x per lane per row (clamped so lanes never cross)
            for q in range(n):
                row = []
                for k in range(m):
                    left = R[q - 1][k] if q > 0 else lx0
                    row.append(max(edge(q, sig[q][1][k]), left + 4.0))
                R.append(row)

            # ---- fills: colourful, brighter while the lane's hysteresis gate is open
            no_stroke()
            for q in range(n):
                for k in range(m):
                    left = R[q - 1][k] if q > 0 else lx0
                    xa, xb = tx(left, fracs[k]), tx(R[q][k], fracs[k])
                    v = sig[q][1][k]
                    a = 0.62 if sig[q][2][k] > 0.5 else 0.24
                    k_ = 0.35 + 0.65 * v
                    fill(cols[q][0] * k_, cols[q][1] * k_, cols[q][2] * k_, a)
                    rect(xa, ys[k] - rowh / 2.0, xb - xa, rowh + 0.8)
            for k in range(m):                         # winner ribbon
                c3 = cols[champs[k]]
                fill(*c3, 0.9)
                xa, xb = tx(x0, fracs[k]), tx(x0 + ribbon, fracs[k])
                rect(xa, ys[k] - rowh / 2.0, xb - xa, rowh + 0.8)

            # ---- waveform edges: raw (faint) and modulated (bright)
            for q in range(n):
                stroke_weight(1.0)
                stroke(1, 1, 1, 0.22)
                for k in range(1, m):
                    line(tx(edge(q, sig[q][0][k - 1]), fracs[k - 1]), ys[k - 1],
                         tx(edge(q, sig[q][0][k]), fracs[k]), ys[k])
                stroke_weight(1.8)
                stroke(*cols[q], 0.95)
                for k in range(1, m):
                    line(tx(R[q][k - 1], fracs[k - 1]), ys[k - 1], tx(R[q][k], fracs[k]), ys[k])

            # ---- triangle pairs on gate edges (out = opened/push, in = closed/pull)
            # Open and close each carry their own magnetic location → frequency.
            # A magnetic blip (head-impact) is drawn between them when present.
            for q in range(n):
                g = sig[q][2]
                events = [k for k in range(1, m) if g[k] != g[k - 1]][-14:]
                labelled = set()
                if srcs[q]['key'] == 'GATE':
                    last_y = None
                    for k in reversed(events):
                        if k >= len(self.ctx):
                            continue
                        if last_y is None or abs(ys[k] - last_y) >= LABEL_MIN_PX:
                            labelled.add(k)
                            last_y = ys[k]
                        if len(labelled) >= LABEL_MAX:
                            break
                for k in events:
                    rising = g[k] > g[k - 1]
                    # alternate emphasis with amplitude (push vs pull strength)
                    amp = sig[q][1][k] if k < len(sig[q][1]) else 0.5
                    if rising:
                        c3 = (0.35 + 0.3 * amp, 1.0, 0.55 + 0.2 * (1.0 - amp))
                    else:
                        c3 = (1.0, 0.55 + 0.25 * amp, 0.25 + 0.2 * (1.0 - amp))
                    al = clamp(1.0 - fracs[k] * 1.1, 0.15, 1.0)
                    xe, ye = tx(R[q][k], fracs[k]), ys[k]
                    d = -1 if rising else 1
                    self.tri(xe - 9, ye, 6, d, c3, al)
                    self.tri(xe + 9, ye, 6, -d, c3, al)
                    if k in labelled and k < len(self.ctx):
                        cx_ = self.ctx[k]
                        if rising:
                            # Minimal consistent head-impact indicator on gate open
                            brg = cx_.get('open_brg')
                            if brg is None and self.vote.last_impact:
                                brg = self.vote.last_impact.get('brg')
                            brg_s = '{:03.0f}'.format(brg) if brg is not None else '---'
                            lt = {}
                            if self.vote.last_impact:
                                lt = self.vote.last_impact.get('lightning') or {}
                            lit = 'YES' if lt.get('detected') else 'NO'
                            fill(1.0, 0.88, 0.25)
                            text('HEAD IMPACT', x=xe, y=ye - 14, font_size=7)
                            fill(0.85, 0.95, 1.0)
                            text('{}'.format(brg_s), x=xe, y=ye - 24, font_size=7)
                            fill(1.0, 0.45, 0.2) if lit == 'YES' else fill(0.65, 0.85, 0.55)
                            text('LIGHTNING {}'.format(lit), x=xe, y=ye - 34, font_size=7)
                        else:
                            # Minimal close marker: bearing only
                            brg = cx_.get('close_brg')
                            brg_s = '{:03.0f}'.format(brg) if brg is not None else '---'
                            fill(*c3)
                            text('CLOSE  {}'.format(brg_s), x=xe, y=ye - 14, font_size=7)
                # Head-impact diamond on the open residual — same minimal labels
                if srcs[q]['key'] == 'GATE' and self.vote.active:
                    for ev in self.vote.events[-8:]:
                        if ev.get('kind') != 'blip':
                            continue
                        for k in reversed(range(m)):
                            if k >= len(self.ctx):
                                continue
                            if self.ctx[k].get('blip', 0) > 0.15:
                                xe = tx(R[q][k], fracs[k])
                                ye = ys[k]
                                force = ev.get('force', ev.get('amp', 0.5))
                                brg = ev.get('brg')
                                brg_s = '{:03.0f}'.format(brg) if brg is not None else '---'
                                lt = ev.get('lightning') or {}
                                lit = 'YES' if lt.get('detected') else 'NO'
                                # consistent diamond mark
                                stroke(1.0, 0.85, 0.2, 0.95)
                                stroke_weight(2.0)
                                no_fill()
                                s = 5.0 + 6.0 * min(1.0, force)
                                line(xe - s, ye, xe, ye + s)
                                line(xe, ye + s, xe + s, ye)
                                line(xe + s, ye, xe, ye - s)
                                line(xe, ye - s, xe - s, ye)
                                # minimal three-line label (matches open triangles)
                                fill(1.0, 0.88, 0.25)
                                text('HEAD IMPACT', x=xe, y=ye + 12, font_size=7)
                                fill(0.85, 0.95, 1.0)
                                text('{}'.format(brg_s), x=xe, y=ye + 22, font_size=7)
                                fill(1.0, 0.45, 0.2) if lit == 'YES' else fill(0.65, 0.85, 0.55)
                                text('LIGHTNING {}'.format(lit), x=xe, y=ye + 32, font_size=7)
                                break

            # ---- live head circle (double ring = current winner, filled = gate open)
            for q in range(n):
                left = R[q - 1][-1] if q > 0 else lx0
                xc = tx((left + R[q][-1]) / 2.0, 0.0)
                yc = top - 20
                rad = 5.0 + 12.0 * latest[q]
                stroke(*cols[q], 1.0)
                stroke_weight(2.0)
                if sig[q][2][-1] > 0.5:
                    fill(*cols[q], 0.5)
                else:
                    no_fill()
                ellipse(xc - rad, yc - rad, 2 * rad, 2 * rad)
                if q == champs[-1]:
                    no_fill()
                    ellipse(xc - rad - 4, yc - rad - 4, 2 * rad + 8, 2 * rad + 8)

            # ---- lane labels under the scope
            no_stroke()
            for q, src in enumerate(srcs):
                left_b = bases[q] - widths[q]
                xc = tx((left_b + bases[q]) / 2.0, 1.0)
                fill(*cols[q])
                text(src['key'], x=xc, y=sbot - 10, font_size=10)
                if src['key'] == 'GATE':
                    # mic gate: state + independent open/close locations + chatter
                    if self.vote.active:
                        word = 'OPEN' if self.vote.gate_open else 'SHUT'
                    else:
                        word = 'OPEN' if self.gate_on else 'SHUT'
                    on = self.vote.active
                    o_brg = self.vote.open_brg if on else None
                    c_brg = self.vote.close_brg if on else None
                    o_s = '{:03.0f}'.format(o_brg) if o_brg is not None else '---'
                    c_s = '{:03.0f}'.format(c_brg) if c_brg is not None else '---'
                    pk_hz, purity = self.event_context(len(self.ctx) - 1) if self.ctx else (0.0, 0.0)
                    dist = DIPOLE_K / max(self.src['MAG']['level'], 0.02) ** (1.0 / 3.0)
                    gx_ = clamp(xc, 90.0, w - 90.0)
                    text('{}  LOC O{} C{}  fO{:.1f}/C{:.1f}'.format(
                        word, o_s, c_s,
                        self.vote.open_fc if on else 0.0,
                        self.vote.close_fc if on else 0.0),
                         x=gx_, y=sbot - 35, font_size=8)
                    text('d{:.1f} I{:.2f} G{:.2f} C{:.2f} S{:.2f} B{:.2f} L{:.2f}'.format(
                        dist, purity, self.src['GRAV']['level'],
                        self.vote.chatter if on else 0.0,
                        self.vote.share if on else 1.0,
                        self.vote.blip if on else 0.0,
                        self.vote.loud if on else 0.0),
                         x=gx_, y=sbot - 47, font_size=8)

        # ---- controls
        no_stroke()
        labels = {'JIT': 'JIT {}'.format(JIT_STEPS[self.jit_i]),
                  'CHOP': 'CHOP off' if fc == 0 else 'CHOP {:g}Hz'.format(fc),
                  'HYST': 'HYST {}'.format(gap),
                  'N': 'N {}'.format(n),
                  'DEMO': 'DEMO ' + ('ON' if self.demo else 'off'),
                  'VOTE': 'VOTE ' + ('ON' if self.vote.active else 'off')}
        for ctl in self.ctls:
            if ctl['id'] == 'DEMO':
                on = self.demo
            elif ctl['id'] == 'VOTE':
                on = self.vote.active
            else:
                on = True
            fill(*rgb('#1f2f3a' if on else '#14201f', 0.95))
            rect(ctl['x'], ctl['y'], ctl['w'], ctl['h'])
            fill(*rgb('#bfe9ff' if on else '#6a8578'))
            text(labels[ctl['id']], x=ctl['x'] + ctl['w'] / 2, y=ctl['y'] + ctl['h'] / 2, font_size=9)
        fill(*rgb('#6a8578'))
        text('edge = waveform | tri out = open, in = close | ring = winner | left ribbon flips {}'.format(flips),
             x=w / 2, y=100, font_size=7)

    def note_peak(self, audio=None, mag=None, raw=None, resid=None):
        """Background: running peaks. While CAL runs: the calibration peak,
        flushed to disk every 0.5 s so it is stored continuously."""
        cal_live = bool(self.cal and self.cal['step'] != 'DONE' and self.cal_peaks is not None)
        tgt = self.cal_peaks if cal_live else self.peaks
        stamp = time.strftime('%Y-%m-%d %H:%M:%S')
        for k, v in (('audio', audio), ('mag', mag), ('mag_raw', raw), ('residual', resid)):
            if v is not None and v > tgt.get(k, 0.0):
                tgt[k] = v
                tgt[k + '_time'] = stamp
                self.peak_dirty = True

    def flush_peaks(self, running=None):
        pk = self.model.data.setdefault('peaks', {})
        pk['background'] = dict(self.peaks)
        if self.cal_peaks is not None:
            live = bool(self.cal and self.cal['step'] != 'DONE') if running is None else running
            pk['calibration'] = dict(self.cal_peaks, running=live)
        ok = self.model.save()
        self.peak_dirty = not ok
        return ok

    def hw_info(self):
        info = {'machine': '?', 'system': '?', 'release': '?'}
        try:
            u = os.uname()
            info = {'machine': u.machine, 'system': u.sysname, 'release': u.release}
        except Exception:
            pass
        info['screen'] = [int(self.size.w), int(self.size.h)]
        return info

    def cal_play(self, hz, secs, amp=0.8):
        path = os.path.join(os.path.expanduser('~/Documents'),
                            'yband_tone_{}_{}.wav'.format(int(hz), int(secs * 1000)))
        try:
            if not os.path.exists(path):
                write_tone(path, hz, secs, amp)
            self.player = sound.Player(path)
            self.player.volume = 1.0
            self.player.play()
        except Exception as e:
            print('tone error', e)

    def cal_start_rec(self):
        try:
            self.cal_rec.record()
        except Exception as e:
            print('cal rec error', e)

    def cal_stop_rec(self):
        try:
            self.cal_rec.stop()
        except Exception:
            pass
        return read_wav_samples(self.cal_path)

    def cal_tick(self, now):
        c = self.cal
        if not c:
            return
        step = c['step']

        if step == 'NOISE':
            if c['t0'] is None:
                self.cal_start_rec()
                c['t0'] = now
            elif now - c['t0'] >= 1.2:
                samples, rate = self.cal_stop_rec()
                if not samples:
                    c['res']['err'] = 'NO REC FILE (needs .wav mic recording)'
                    c['step'] = 'DONE'
                    c['t0'] = now
                    return
                c['res']['floor'] = rms_level(samples)
                self.note_peak(audio=max(abs(x) for x in samples))
                c['step'], c['t0'] = 'TONE', None

        elif step == 'TONE':
            if c['t0'] is None:
                self.cal_start_rec()
                self.cal_play(1000.0, 1.4)
                c['t0'] = now
            elif now - c['t0'] >= 1.7:
                samples, rate = self.cal_stop_rec()
                if samples:
                    mid = samples[len(samples)//6: -len(samples)//6 or None]
                    tone = goertzel(mid, rate, 1000.0)
                    other = max(goertzel(mid, rate, 1700.0), goertzel(mid, rate, 620.0), 1e-6)
                    c['res']['tone_rms'] = rms_level(mid)
                    c['res']['rate'] = rate
                    c['res']['tone_peak'] = max(abs(x) for x in samples)
                    self.note_peak(audio=c['res']['tone_peak'])
                    c['res']['snr'] = 20.0 * math.log10(max(tone, 1e-6) / other)
                    c['res']['audio_ok'] = c['res']['snr'] >= 10.0 and tone > c['res']['floor'] * 0.5
                    floor = c['res'].get('floor', 0.002)
                    TH['open'] = clamp(floor * 3.0, 0.004, 0.08)
                    TH['close'] = clamp(floor * 2.0, 0.002, TH['open'] * 0.8)
                    c['res']['gate_open'] = TH['open']
                    c['res']['gate_close'] = TH['close']
                else:
                    c['res']['audio_ok'] = False
                c['step'], c['t0'] = 'MAG', now
                c['last_beep'] = 0.0

        elif step == 'MAG':
            if c['t0'] is None:
                c['t0'] = now
            # audible feedback: pitch follows the live field strength
            if now - c['last_beep'] > 0.45:
                c['last_beep'] = now
                pitch = 300.0 + clamp(self.mag_strength, 0.0, 120.0) * 10.0
                self.cal_play(round(pitch / 40.0) * 40.0, 0.12, 0.6)
            if now - c['t0'] >= 10.0:
                spans = [b - a for a, b in zip(c['mn'], c['mx'])]
                c['res']['spans'] = spans
                if sum(1 for sp in spans if sp >= 20.0) >= 2 and c['vecs']:
                    off = tuple((a + b) / 2.0 for a, b in zip(c['mn'], c['mx']))
                    self.mag_off = off
                    self.mag_baseline = None
                    c['res']['off'] = off
                    avg = sum(math.sqrt(sum((v[i]-off[i])**2 for i in range(3)))
                              for v in c['vecs']) / len(c['vecs'])
                    c['res']['avg_cal'] = avg
                    c['res']['avg_raw'] = sum(math.sqrt(sum(x*x for x in v))
                                              for v in c['vecs']) / len(c['vecs'])
                    # peak of the calibrated field (new offset applied)
                    self.cal_peaks['mag'] = max(math.sqrt(sum((v[i]-off[i])**2 for i in range(3)))
                                                for v in c['vecs'])
                else:
                    c['res']['mag_err'] = 'ROTATE MORE - offsets not applied'
                self.flush_peaks(running=False)
                c['commit'] = self.model.commit(c['res'], self.hw_info(), c.get('rebaseline', False),
                                                peaks=self.cal_peaks)
                self.last_verdict = c['commit']['verdict']
                ok = c['commit']['ok'] and c['commit']['readback']
                self.cal_play(1320.0 if ok else 330.0, 0.35, 0.8)   # high = pass, low = fail
                c['step'], c['t0'] = 'DONE', now

    def draw_cal(self):
        w, h = self.size.w, self.size.h
        no_stroke()
        fill(*rgb('#1a2a3d' if not self.cal else '#3d3a1a', 0.95))
        rect(self.cal_x, self.cal_y, self.cal_w, self.cal_h)
        fill(*rgb('#ffe9a0'))
        text('CLOSE' if self.cal else 'CAL', x=self.cal_x + self.cal_w/2,
             y=self.cal_y + self.cal_h/2, font_size=12)
        c = self.cal
        if not c:
            fill(*rgb('#7fa896'))
            text(self.last_verdict, x=w/2, y=110, font_size=8)
            return
        now = time.time()
        pw, ph = w - 40, 330
        px, py = 20, h/2 - ph/2
        fill(0.02, 0.04, 0.05, 0.92)
        rect(px, py, pw, ph)
        fill(*rgb('#ffe9a0'))
        text('CALIBRATION + AUDIO FEEDBACK TEST', x=w/2, y=py + ph - 18, font_size=12)

        step = c['step']
        res = c['res']
        cp = self.cal_peaks or {}
        fill(*rgb('#ffcf6b'))
        text('CAL PEAK  mag {:.1f} uT  audio {:.2f}  (stored live)'.format(
            cp.get('mag', 0.0), cp.get('audio', 0.0)), x=w/2, y=py + 22, font_size=9)
        titles = {'NOISE': 'STEP 1/3  SILENCE - keep quiet',
                  'TONE': 'STEP 2/3  SPEAKER > MIC  1 kHz',
                  'MAG': 'STEP 3/3  ROTATE PHONE (figure-8)  beeps = uT'}
        durs = {'NOISE': 1.2, 'TONE': 1.7, 'MAG': 10.0}
        if step in titles:
            fill(*rgb('#ffffff'))
            text(titles[step], x=w/2, y=py + ph - 42, font_size=11)
            frac = 0.0 if c['t0'] is None else clamp((now - c['t0']) / durs[step], 0, 1)
            fill(0.1, 0.15, 0.12, 1.0)
            rect(px + 14, py + ph - 62, pw - 28, 6)
            fill(0.95, 0.8, 0.3, 1.0)
            rect(px + 14, py + ph - 62, (pw - 28) * frac, 6)
            if step == 'MAG':
                fill(*rgb('#c4b5fd'))
                text('{:.1f} uT  (raw {:.1f})'.format(self.mag_strength, self.mag_raw),
                     x=w/2, y=py + ph - 95, font_size=20)
                spans = [b - a for a, b in zip(c['mn'], c['mx'])]
                if c['vecs']:
                    fill(*rgb('#a5b4fc'))
                    text('coverage X {:.0f} Y {:.0f} Z {:.0f} (need 20+ on two)'.format(*spans),
                         x=w/2, y=py + ph - 125, font_size=9)
            if 'floor' in res:
                fill(*rgb('#8eebff'))
                text('noise floor {:.4f}'.format(res['floor']), x=w/2, y=py + 40, font_size=10)
        else:
            lines = []
            if 'err' in res:
                lines.append((res['err'], '#ff8a8a'))
            if 'floor' in res:
                lines.append(('Noise floor {:.4f}'.format(res['floor']), '#8eebff'))
            if 'snr' in res:
                ok = res.get('audio_ok')
                lines.append(('Loop 1 kHz  RMS {:.3f}  SNR {:.0f} dB  {}'.format(
                    res['tone_rms'], res['snr'], 'PASS' if ok else 'FAIL - raise volume'),
                    '#6dffb0' if ok else '#ff8a8a'))
                lines.append(('Gate open {:.4f}  close {:.4f}'.format(TH['open'], TH['close']), '#8eebff'))
            if 'off' in res:
                o = res['off']
                lines.append(('Offset X {:.1f} Y {:.1f} Z {:.1f} uT'.format(*o), '#c4b5fd'))
                lines.append(('Field raw {:.1f} > cal {:.1f} uT'.format(res['avg_raw'], res['avg_cal']), '#c4b5fd'))
                if not (25.0 <= res['avg_cal'] <= 65.0):
                    lines.append(('Outside 25-65 uT: magnet/case/steel nearby?', '#ffb454'))
            if 'mag_err' in res:
                lines.append((res['mag_err'], '#ff8a8a'))
            cm = c.get('commit')
            if cm:
                lines.append((cm['verdict'], '#6dffb0' if cm['ok'] else '#ffb454'))
                for name, okc, detail in cm['checks']:
                    lines.append(('  {:<12} {}  {}'.format(name, 'ok' if okc else 'X', detail),
                                  '#9fe8c0' if okc else '#ff8a8a'))
                if cm['saved'] and cm['readback']:
                    lines.append(('STORED + READ BACK OK', '#6dffb0'))
                else:
                    lines.append(('STORE FAILED' if not cm['saved'] else 'READ-BACK MISMATCH', '#ff8a8a'))
            lines.append(('High beep = pass, low beep = fail', '#9aa7a0'))
            for i, (txt, col) in enumerate(lines):
                fill(*rgb(col))
                text(txt, x=w/2, y=py + ph - 44 - i*17, font_size=10)

    def update_source(self, key, target):
        s = self.src[key]
        s['prev'] = s['level']
        s['level'] += (target - s['level']) * min(1.0, self.dt * 8.0)
        d = (s['level'] - s['prev']) / max(self.dt, 0.001) * 0.25
        s['delta'] = 0.85 * s['delta'] + 0.15 * d

    def _snapshot_png_bytes(self):
        """Rasterise the current on-screen view into PNG bytes."""
        # Prefer UIKit snapshot of the live scene view (includes labels)
        if _OBJC_SNAP:
            try:
                view = self.view
                oc = view.objc_instance if hasattr(view, 'objc_instance') else ObjCInstance(view)
                bounds = oc.bounds()
                scale = 0.0  # device native scale
                UIGraphicsBeginImageContextWithOptions(bounds.size, False, scale)
                oc.drawViewHierarchyInRect_afterScreenUpdates_(bounds, True)
                ui_img = UIGraphicsGetImageFromCurrentImageContext()
                UIGraphicsEndImageContext()
                if ui_img:
                    data = UIImagePNGRepresentation(ui_img)
                    if data:
                        return bytes(data)
            except Exception as e:
                print('objc snapshot error:', e)
        # Fallback: solid-frame placeholder so the pipeline still writes a PNG
        try:
            w, h = int(self.size.w), int(self.size.h)
            w, h = max(8, w), max(8, h)
            # minimal valid 8-bit RGB PNG via raw zlib
            raw = b''
            row = b'\x00' + bytes([0, 8, 5] * w)[:w * 3]
            for _ in range(h):
                raw += row
            compressed = zlib.compress(raw, 9)
            sig = b'\x89PNG\r\n\x1a\n'
            ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
            return (sig
                    + _png_chunk(b'IHDR', ihdr)
                    + _png_chunk(b'IDAT', compressed)
                    + _png_chunk(b'IEND', b''))
        except Exception as e:
            print('fallback snapshot error:', e)
            return None

    def capture_head_impact_png(self, impact=None):
        """Rasterise the current image into a PNG container and stamp EXIF /
        tEXt metadata: company = Adobe Systems Inc, copyright = Copyright 2026.
        Called once per indicated head impact on screen."""
        png_bytes = self._snapshot_png_bytes()
        if not png_bytes:
            return None
        documents = os.path.expanduser('~/Documents')
        try:
            os.makedirs(documents, exist_ok=True)
        except Exception:
            pass
        stamp = time.strftime('%Y%m%d_%H%M%S')
        brg = 0
        if impact and impact.get('brg') is not None:
            brg = int(impact['brg']) % 360
        path = os.path.join(documents, 'yband_head_impact_{}_{:03d}.png'.format(stamp, brg))
        ok = write_png_with_exif_meta(
            path, png_bytes,
            company=PNG_COMPANY,
            copyright_text=PNG_COPYRIGHT)
        if ok or os.path.exists(path):
            self.last_impact_png = path
            if impact is not None:
                impact['png'] = path
            self.status = 'HEAD IMPACT PNG {}'.format(os.path.basename(path))
            return path
        return None

    def update(self):
        now = time.time()

        if now >= self.next_mag_sample:
            self.sample_magnetometer()
            self.next_mag_sample = now + MAG_SAMPLE_INTERVAL

        if self.recording and now - self.recording_started >= SAMPLE_SECONDS:
            self.finish_capture()
        elif (MIC_ENABLED and self.recorder and not self.recording and not self.cal and
              (now >= self.next_capture or self.force_capture)):
            self.force_capture = False
            self.start_capture()

        self.cal_tick(now)
        self.vote.tick(now)          # vote-now learning-loop demo (non-blocking)
        # Rasterise screen to PNG+EXIF each time a head impact is indicated
        imp = self.vote.last_impact
        if imp and imp.get('t', 0) > self._last_impact_snap_t:
            self._last_impact_snap_t = imp['t']
            try:
                self.capture_head_impact_png(imp)
            except Exception as e:
                print('head-impact png capture error:', e)
        if len(self.ev_cache) > 300:
            self.ev_cache = {}
        calibrating = bool(self.cal and self.cal['step'] != 'DONE')
        if self.peak_dirty and now >= self.next_peak_save:
            self.flush_peaks()
            self.next_peak_save = now + (0.5 if calibrating else 5.0)

        # gravity change -> perspective (tilt back = far chambers shrink; roll = shear)
        gx, gy, gz = (list(self.gravity) + [0, 0, 0])[:3]
        gm = math.sqrt(gx*gx + gy*gy + gz*gz) or 1.0
        k = min(1.0, self.dt * 6.0)
        self.persp += (clamp(gy / gm + 1.0, -1.0, 1.0) - self.persp) * k
        self.shear += (clamp(gx / gm, -1.0, 1.0) - self.shear) * k
        if now >= self.next_hist:
            self.sample_history(now)
            self.next_hist = now + HIST_DT


        # source levels
        self.audio_target = max(0.0, self.audio_target - self.dt * 0.35)
        gx, gy, gz = (list(self.gravity) + [0, 0, 0])[:3]
        gm = math.sqrt(gx*gx + gy*gy + gz*gz) or 1.0
        tilt = clamp(1.0 - abs(gz) / gm, 0.0, 1.0)

        if self.vote.active:
            # vote demo drives the chambers: speech pushes, loops hold, 'vote now' pulls
            a_eff, m_eff, g_eff = self.vote.drive(now, self.mag_heading, self.gravity)
            self.update_source('AUDIO', a_eff)
            self.update_source('MAG', m_eff)
            self.update_source('GATE', g_eff)
        else:
            gate_gain = self.features['gate_gain'] if self.features else 0.0
            self.update_source('AUDIO', self.audio_target)
            self.update_source('MAG', clamp(self.mag_residual / (MAG_BLIP_THRESHOLD * 2.0), 0.0, 1.0))
            self.update_source('GATE', clamp(gate_gain, 0.0, 1.0))
        self.update_source('GRAV', tilt)

    # --------------------------------------------------------
    # DRAW HELPERS
    # --------------------------------------------------------

    def arrow(self, x, y, ang, length, col, alpha, outward=True):
        """Arrow centred on (x,y), along direction ang. outward = PUSH, else PULL."""
        d = math.radians(ang)
        dx, dy = math.cos(d), math.sin(d)
        tail = (x - dx*length/2, y - dy*length/2)
        tip = (x + dx*length/2, y + dy*length/2)
        if not outward:
            tail, tip = tip, tail
        stroke(*col, alpha)
        stroke_weight(2.4)
        line(tail[0], tail[1], tip[0], tip[1])
        hd = math.atan2(tip[1] - tail[1], tip[0] - tail[0])
        hl = max(6.0, length * 0.35)
        for off in (2.6, -2.6):
            line(tip[0], tip[1],
                 tip[0] + math.cos(hd + off) * hl,
                 tip[1] + math.sin(hd + off) * hl)

    # --------------------------------------------------------
    # DRAW
    # --------------------------------------------------------

    def draw(self):
        cx, cy, r = self.center.x, self.center.y, self.radius
        w, h = self.size.w, self.size.h
        t = time.time()
        pulse = 0.5 + 0.5 * math.sin(t * 2 * math.pi * PULSON_HZ)

        self.draw_chambers()

        # ---------------- HUD ----------------
        no_stroke()
        fill(*rgb('#b8ffd6'))
        text('Y-BAND  MOD CHAMBERS', x=cx, y=h - 18, font_size=12)
        fill(*rgb('#ffffff'))
        text(self.status, x=cx, y=h - 34, font_size=10)
        if self.vote.active or self.vote.label:
            fill(*rgb('#ffe9a0'))
            text(self.vote.label, x=cx, y=h - 50, font_size=9)

        # Microtesla panel (top-left)
        px, py = 12, h - 74
        fill(0.05, 0.07, 0.10, 0.75)
        rect(px - 6, py - 52, 150, 92)
        fill(*rgb('#c4b5fd'))
        if self.mag_ok:
            text('{:.1f} \u00b5T'.format(self.mag_strength), x=px + 69, y=py + 22, font_size=22)
        else:
            text('NO MAG', x=px + 69, y=py + 22, font_size=18)
        # bar 0-100 uT, earth band 25-65 marked
        bx, bw_ = px, 138
        fill(0.12, 0.14, 0.2, 1.0)
        rect(bx, py - 2, bw_, 6)
        fill(0.2, 0.35, 0.3, 1.0)
        rect(bx + bw_*0.25, py - 2, bw_*0.40, 6)
        fill(0.77, 0.52, 1.0, 1.0)
        rect(bx, py - 2, bw_ * clamp(self.mag_strength / 100.0, 0, 1), 6)
        fill(*rgb('#a5b4fc'))
        mx, my, mz = self.mag_xyz
        text('X {:.0f}  Y {:.0f}  Z {:.0f}'.format(mx, my, mz), x=px + 69, y=py - 16, font_size=9)
        pk = self.cal_peaks if (self.cal and self.cal_peaks) else self.peaks
        fill(*rgb('#ffcf6b'))
        text('{}PEAK {:.1f} uT  AUD {:.2f}'.format('CAL ' if (self.cal and self.cal_peaks) else '',
                                                  pk.get('mag', 0.0), pk.get('audio', 0.0)),
             x=px + 69, y=py - 46, font_size=9)
        fill(*rgb('#a5b4fc'))
        text('raw {:.0f} res {:.1f} HDG {}'.format(
            self.mag_raw, self.mag_residual,
            '{:.0f}'.format(self.mag_heading) if self.mag_heading is not None else '--'),
            x=px + 69, y=py - 32, font_size=9)

        # Audio meters (top-right)
        if self.features:
            fill(*rgb('#8eebff'))
            text('RMS {:.3f}  PEAK {:.3f}'.format(self.features['rms'], self.features['peak']),
                 x=w - 90, y=h - 60, font_size=9)
        mw, mh = 130, 5
        mx0, my0 = w - 12 - mw, h - 74
        fill(0.08, 0.12, 0.10, 0.9)
        rect(mx0, my0, mw, mh)
        rn = clamp(self.last_residual * 18.0, 0.0, 1.0)
        fill(0.2 + rn*0.7, 0.85 - rn*0.4, 0.45, 0.95)
        rect(mx0, my0, mw * rn, mh)

        # Modulation button
        fill(*rgb('#1a3d2e' if self.hysteresis_enabled else '#3d1a1a', 0.95))
        rect(self.btn_x, self.btn_y, self.btn_w, self.btn_h)
        fill(*rgb('#6dffb0' if self.hysteresis_enabled else '#ff8a8a'))
        text('MODULATED ON' if self.hysteresis_enabled else 'MODULATED OFF',
             x=cx, y=self.btn_y + self.btn_h/2, font_size=12)

        self.draw_cal()

    def stop(self):
        try:
            self.vote.stop()
        except Exception:
            pass
        try:
            self.flush_peaks(running=False)
        except Exception:
            pass
        if self.recording:
            try:
                self.recorder.stop()
            except Exception:
                pass
        try:
            motion.stop_updates()
        except Exception:
            pass

if __name__ == '__main__':
    run(YBandScope(), PORTRAIT, show_fps=False)
