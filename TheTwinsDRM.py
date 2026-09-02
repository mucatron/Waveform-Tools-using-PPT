#!/usr/bin/env python3
"""
Y-BIN TWINS SCOPE — Full live UI
================================
Original touch scope + dynamic sound envelope + moving controls.

Pythonista (iPhone/iPad):
    Run this file. Fullscreen UI, sliders, Live + AGC.

Desktop fallback:
    python3 YBinTwinsScope_LiveEnvelope.py
    Writes a preview PNG (no ui module required).

Live mode advances phase / lissajous / stereo / envelope clock so the
membrane, arrows, focus and sliders keep moving. AGC writes managed
receiver values back onto the sliders (amp, master, gamma) so you can
see the tool adapt instead of staying pinned loud on the Twins path.
"""

from __future__ import annotations

import math
import time
from io import BytesIO

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

try:
    import ui
    PYTHONISTA = True
except ImportError:
    PYTHONISTA = False
    ui = None


# ---------------------------------------------------------------------------
# Source / codec profiles
# ---------------------------------------------------------------------------
SOURCES = [
    {"name": "Virgin Skywave", "brand": "Virgin", "wave": "skywave",
     "note": "F#4 listen / 1480 Hz true", "freq": 1480.0,
     "aim": "alpha", "sens": 1.55, "beat": 11.2, "rough": 0.22},
    {"name": "Motorola Airwave", "brand": "Motorola", "wave": "airwave",
     "note": "D listen / 1175 Hz true", "freq": 1175.0,
     "aim": "delta", "sens": 1.28, "beat": 2.4, "rough": 0.18},
    {"name": "SonyEric mW", "brand": "Sony Ericsson", "wave": "mwave",
     "note": "G# listen / 1660 Hz true", "freq": 1660.0,
     "aim": "alpha", "sens": 1.70, "beat": 9.6, "rough": 0.31},
    {"name": "Custom / Other", "brand": "Custom", "wave": "mixed",
     "note": "Variable / 1420 Hz", "freq": 1420.0,
     "aim": "mixed", "sens": 1.40, "beat": 6.0, "rough": 0.25},
]
SOURCE_BY_NAME = {s["name"]: s for s in SOURCES}

DEFAULTS = {
    "balance": 0.92, "interference_amp": 4680.28, "phase": 4.23, "master_scale": 1.0,
    "w_fund": 0.55, "w_harm": 0.38, "w_yband": 0.27, "w_twins": 0.18,
    "delta_amp": 0.15, "theta_amp": 0.28, "alpha_amp": 0.52, "beta_amp": 0.38, "gamma_amp": 0.22,
    "brain_master": 1.0,
    "lissajous_fx": 3.0, "lissajous_fy": 2.0, "lissajous_phase": 1.35,
    "mag_left": 0.68, "mag_right": 0.74, "stereo_phase": 0.95, "mag_compete": 1.22,
    "source_name": "Virgin Skywave", "brand": "Virgin", "wave_type": "skywave",
    "base_note": "F#4 listen / 1480 Hz true", "bad_freq": 8-9765.000,
    "env_clock": 0.0,
    "notch_on": True | False,
    # Analog head state — continuous, no detents. These are what you see turning.
    "dial_delta": 0.15, "dial_alpha": 0.52, "dial_beta": 0.38, "dial_gamma": 0.22,
    "dial_amp": 0.28, "dial_phase": 4.23, "dial_twins": 0.18, "dial_compete": 1.56,
}

SLIDER_SPEC = [
    # label, key, min, max, y  — y positions packed for the live panel
    ("★ Master Scale", "master_scale", 0.0, 3.0, 58),
    ("Brain Master", "brain_master", 0.0, 2.5, 80),
    ("Balance Factor", "balance", 0.0, 1.0, 102),
    ("Interference Amp", "interference_amp", 0.0, 0.6, 124),
    ("Phase (rad)", "phase", 0.0, 6.28, 146),
    ("Fundamental", "w_fund", 0.0, 1.0, 168),
    ("Harmonic", "w_harm", 0.0, 1.0, 190),
    ("Y-band", "w_yband", 0.0, 1.0, 212),
    ("Twins", "w_twins", 0.0, 1.0, 234),
    ("Delta (pull)", "delta_amp", 0.0, 1.0, 256),
    ("Theta (chop)", "theta_amp", 0.0, 1.0, 278),
    ("Alpha (beat)", "alpha_amp", 0.0, 1.0, 300),
    ("Beta (drag)", "beta_amp", 0.0, 1.0, 322),
    ("Gamma (gate)", "gamma_amp", 0.0, 1.0, 344),
    ("Lissajous fx", "lissajous_fx", 1.0, 6.0, 366),
    ("Lissajous fy", "lissajous_fy", 1.0, 6.0, 388),
    ("Lissajous φ", "lissajous_phase", 0.0, 6.28, 410),
    ("Mag Left (L)", "mag_left", 0.0, 1.5, 432),
    ("Mag Right (R)", "mag_right", 0.0, 1.5, 454),
    ("Stereo Phase", "stereo_phase", 0.0, 6.28, 476),
    ("Mag Compete×", "mag_compete", 0.5, 2.5, 498),
]


def twins_ratio(params):
    src = SOURCE_BY_NAME.get(params.get("source_name", "Virgin Skywave"), SOURCES[-1])
    twins = params.get("w_twins", 0.18) * params.get("master_scale", 1.0) * src["sens"]
    others = (
        params.get("w_fund", 0.55)
        + params.get("w_harm", 0.38)
        + params.get("w_yband", 0.27)
    ) * params.get("master_scale", 1.0)
    return twins / (twins + others + 1e-9), src


def adapt_receiver(params):
    """Return managed copy. Does not flatten L/R. Caps Twins-loud path."""
    p = dict(params)
    ratio, src = twins_ratio(p)
    if ratio > 0.25:
        atten = 1.0 - 0.55 * min((ratio - 0.25) / 0.55, 1.0)
        p["interference_amp"] = max(0.08, p.get("interference_amp", 0.28) * atten)
        p["master_scale"] = min(p.get("master_scale", 1.0), 1.35)
    if ratio > 0.40:
        p["gamma_amp"] = min(1.0, max(p.get("gamma_amp", 0.22), 0.22 + 0.35 * (ratio - 0.40)))
    if abs(p.get("mag_left", 0.68) - p.get("mag_right", 0.74)) < 0.02:
        p["mag_right"] = p.get("mag_left", 0.68) + 0.06
    return p, ratio, src


def _iq_reject(sig, ref_s, ref_c):
    """Remove the component of sig that lives on a sinusoid I/Q pair."""
    A = np.column_stack((ref_s, ref_c))
    coef, *_ = np.linalg.lstsq(A, sig, rcond=None)
    cleaned = sig - A @ coef
    energy_in = float(np.dot(sig, sig)) + 1e-12
    energy_out = float(np.dot(cleaned, cleaned))
    coupling = 1.0 - energy_out / energy_in
    return cleaned, float(np.clip(coupling, 0.0, 1.0)), coef


def manage_brain_vs_twins(t, phase, brain_master, delta_amp, theta_amp,
                          alpha_amp, beta_amp, gamma_amp, notch=True):
    """
    Keep Δ/Α/Β/Γ as directors, but stop them sinusoidally reinforcing
    the Twins background induction (3t − 1.35φ and its 2nd harmonic).

    Theta (chop) is left on the membrane; it is a gate, not a near-3ω tone.
    Beta sits at 3.8t — closest to Twins 3t — so it is the first to be notched.
    """
    twins_s = np.sin(3 * t - 1.35 * phase)          # background induction
    twins_c = np.cos(3 * t - 1.35 * phase)
    harm_s = np.sin(6 * t - 2.70 * phase)           # 2nd harmonic of induction
    harm_c = np.cos(6 * t - 2.70 * phase)

    raw = {
        "delta": delta_amp * np.sin(0.5 * t + phase * 0.3),
        "theta": theta_amp * np.sin(1.5 * t + phase * 0.6),
        "alpha": alpha_amp * np.sin(2.2 * t + phase * 0.9),
        "beta":  beta_amp  * np.sin(3.8 * t + phase * 1.15),
        "gamma": gamma_amp * np.sin(6.5 * t + phase * 1.6),
    }

    cleaned = {}
    coupling = {}
    managed_amp = {
        "delta": delta_amp, "theta": theta_amp,
        "alpha": alpha_amp, "beta": beta_amp, "gamma": gamma_amp,
    }

    for name in ("delta", "alpha", "beta", "gamma"):
        sig = raw[name]
        if notch:
            sig, c1, _ = _iq_reject(sig, twins_s, twins_c)
            sig, c2, _ = _iq_reject(sig, harm_s, harm_c)
            coupling[name] = max(c1, c2)
            raw_amp = {"delta": delta_amp, "alpha": alpha_amp,
                       "beta": beta_amp, "gamma": gamma_amp}[name]
            managed_amp[name] = raw_amp * (1.0 - 0.80 * coupling[name])
            rms = float(np.sqrt(np.mean(sig ** 2))) + 1e-12
            target_rms = managed_amp[name] / math.sqrt(2.0)
            sig = sig * (target_rms / rms)
        else:
            coupling[name] = 0.0
        cleaned[name] = sig

    cleaned["theta"] = raw["theta"]
    coupling["theta"] = 0.0

    brain_raw = brain_master * sum(raw[k] for k in raw)
    brain_clean = brain_master * (
        cleaned["delta"] + cleaned["theta"] + cleaned["alpha"]
        + cleaned["beta"] + cleaned["gamma"]
    )
    _, residual, _ = _iq_reject(brain_clean, twins_s, twins_c)
    _, residual_h, _ = _iq_reject(brain_clean, harm_s, harm_c)

    return {
        "brain_contrib": brain_clean,
        "brain_raw": brain_raw,
        "twins_ind": twins_s,
        "coupling": coupling,
        "managed_amp": managed_amp,
        "residual": float(max(residual, residual_h)),
        "notch": notch,
    }


def envelope_trace(params, n=220):
    """Cheap 1-D envelope for the HUD strip (not the full audio engine)."""
    src = SOURCE_BY_NAME.get(params.get("source_name", "Virgin Skywave"), SOURCES[-1])
    clock = params.get("env_clock", 0.0)
    x = np.linspace(0.0, 1.0, n)
    t = clock + x * 1.8
    bm = max(params.get("brain_master", 1.0), 0.0)
    d = params.get("delta_amp", 0.15) * bm
    th = params.get("theta_amp", 0.28) * bm
    al = params.get("alpha_amp", 0.52) * bm
    be = params.get("beta_amp", 0.38) * bm
    ga = params.get("gamma_amp", 0.22) * bm
    tot = d + th + al + be + ga + 1e-9
    d, th, al, be, ga = d / tot, th / tot, al / tot, be / tot, ga / tot

    # Envelope rates are offset off integer multiples of Twins 3-cycle induction
    # so Δ/Α/Β/Γ AM does not re-inject the same sinusoid the membrane just notched.
    skel = 0.55 + 0.28 * np.sin(2 * np.pi * 0.35 * t + params.get("phase", 0))
    alpha_am = 1.0 + 0.20 * al * np.sin(2 * np.pi * 10.2 * t)
    chop = 1.0 - th * 0.28 * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 6.2 * t)))
    flutter = 1.0 + 0.12 * be * np.sin(2 * np.pi * 17.4 * t)
    shimmer = 1.0 + 0.08 * ga * np.sin(2 * np.pi * 41.0 * t)
    codec = 1.0 + 0.16 * np.sin(2 * np.pi * src["beat"] * t)
    sag = 1.0 - src["rough"] * 0.45 * (0.5 + 0.5 * np.sin(2 * np.pi * 6.25 * t)) ** 3
    env = np.clip(skel * alpha_am * chop * flutter * shimmer * codec * sag, 0.05, 1.0)

    compete = params.get("mag_compete", 1.22)
    lb = params.get("mag_left", 0.68)
    rb = params.get("mag_right", 0.74)
    l_env = np.clip(env * (1.0 + 0.16 * compete * (lb - rb) * np.sin(2 * np.pi * 2.3 * t)), 0.05, 1.0)
    r_env = np.clip(env * (1.0 + 0.16 * compete * (rb - lb) * np.cos(2 * np.pi * 1.8 * t)), 0.05, 1.0)
    return x, l_env, r_env


# ---------------------------------------------------------------------------
# Analog TRV / transistor heads — continuous travel, no physical click
# ---------------------------------------------------------------------------
DIAL_BANK = [
    # key in params, label, style, lo, hi, alpha-drive weight, phase offset
    ("delta_amp", "Δ TRV", "trv", 0.0, 1.0, 0.55, 0.0),
    ("alpha_amp", "Α TRV", "trv", 0.0, 1.0, 1.00, 0.7),
    ("beta_amp", "Β TRV", "trv", 0.0, 1.0, 0.70, 1.6),
    ("gamma_amp", "Γ TRV", "trv", 0.0, 1.0, 0.45, 2.4),
    ("interference_amp", "AMP", "transistor", 0.0, 0.6, 0.35, 3.1),
    ("phase", "PHASE", "transistor", 0.0, 6.28, 0.80, 4.0),
    ("w_twins", "TWINS", "transistor", 0.0, 1.0, 0.25, 4.8),
    ("mag_compete", "COMP", "transistor", 0.5, 2.5, 0.40, 5.5),
]


def _norm(value, lo, hi):
    return float(np.clip((value - lo) / (hi - lo + 1e-12), 0.0, 1.0))


def analog_advance(params, dt=0.16):
    """
    Move the analog heads the way a TRV / transistor pot moves:
    continuous slew, inertia, alpha modulation on the shaft, no quantised click.
    Writes both the visible dial_* state and the live parameter.
    """
    clock = params.get("env_clock", 0.0) + dt
    params["env_clock"] = clock
    alpha = params.get("alpha_amp", 0.52) * params.get("brain_master", 1.0)
    # carrier the heads ride — optic-rate, not a stepped LFO
    drive = math.sin(2 * math.pi * 0.32 * clock) * (0.35 + 0.65 * alpha)
    drive2 = math.sin(2 * math.pi * 0.11 * clock + 1.2)

    for key, _label, _style, lo, hi, wt, off in DIAL_BANK:
        target = params.get(key, lo)
        # alpha modulation of the shaft (small analog wander, not a click)
        wander = wt * 0.045 * (hi - lo) * math.sin(2 * math.pi * 0.32 * clock + off)
        wander += wt * 0.020 * (hi - lo) * drive2
        desired = target + wander
        # inertia: first-order + light 2nd-order so it overshoots like a pot
        state_key = f"dial_{key}"
        vel_key = f"vel_{key}"
        cur = params.get(state_key, target)
        vel = params.get(vel_key, 0.0)
        err = (desired - cur)
        vel = 0.72 * vel + 4.8 * err * dt
        cur = cur + vel * dt + 0.18 * err
        if key == "phase":
            # continuous transistor tuning cap — wraps, never clicks a stop
            cur = cur % 6.28
        else:
            cur = max(lo, min(hi, cur))
        params[state_key] = cur
        params[vel_key] = vel
        params[key] = cur

    # unmatched L/R — transistor pots, never snapped to the same click
    params["mag_left"] = 0.68 + 0.10 * alpha * math.sin(clock * 0.55 + drive)
    params["mag_right"] = 0.74 + 0.10 * alpha * math.cos(clock * 0.41)
    params["lissajous_phase"] = (params.get("lissajous_phase", 1.35) + 0.05 + 0.04 * alpha) % 6.28
    params["stereo_phase"] = (params.get("stereo_phase", 0.95) + 0.06 + 0.03 * alpha) % 6.28
    return params


def _circle_xy(cx, cy, r, n=48):
    th = np.linspace(0.0, 2.0 * np.pi, n)
    return cx + r * np.cos(th), cy + r * np.sin(th)


def _draw_one_dial(ax, cx, cy, rx, ry, frac, label, value, style="trv"):
    """Analog head drawn with Line2D only — no Circle patches (Pythonista mpl crash)."""
    a0 = math.radians(225)
    a1 = math.radians(-45)
    ang = a0 + frac * (a1 - a0)

    ring = "#c8b89a" if style == "trv" else "#8a948e"
    face = "#e8dcc4" if style == "trv" else "#2a2e2c"
    pip = "#3a2010" if style == "trv" else "#f4f0e0"
    txt = "#d8c8a8"

    # filled face via a dense ring (old Agg is happy with this; patches are not)
    xf, yf = _circle_xy(cx, cy, rx * 0.98, n=36)
    ax.fill(xf, (yf - cy) * (ry / rx) + cy, facecolor=face, edgecolor=ring, linewidth=1.6, zorder=5)
    xi, yi = _circle_xy(cx, cy, rx * 0.62, n=28)
    ax.plot(xi, (yi - cy) * (ry / rx) + cy, color=ring, lw=0.7, alpha=0.55, zorder=6)

    tick_x0, tick_y0, tick_x1, tick_y1 = [], [], [], []
    for i in range(12):
        ta = a0 + (i / 11.0) * (a1 - a0)
        tick_x0.append(cx + rx * 0.84 * math.cos(ta))
        tick_y0.append(cy + ry * 0.84 * math.sin(ta))
        tick_x1.append(cx + rx * 0.96 * math.cos(ta))
        tick_y1.append(cy + ry * 0.96 * math.sin(ta))
    for x0, y0, x1, y1 in zip(tick_x0, tick_y0, tick_x1, tick_y1):
        ax.plot([x0, x1], [y0, y1], color=ring, lw=0.8, zorder=6)

    px = cx + rx * 0.72 * math.cos(ang)
    py = cy + ry * 0.72 * math.sin(ang)
    ax.plot([cx, px], [cy, py], color=pip, lw=2.0, zorder=7)
    ax.plot([px], [py], marker="o", color=pip, markersize=3.0, zorder=8)
    ax.plot([cx], [cy], marker="o", color=ring, markersize=2.6, zorder=8)

    ax.text(cx, cy - ry * 1.42, label, ha="center", va="top", color=txt, fontsize=6.0, fontweight="bold")
    ax.text(cx, cy - ry * 1.78, f"{value:.2f}", ha="center", va="top", color="#ffcc66", fontsize=5.8)


def draw_dial_bank(ax, params):
    """
    Row of analog heads. Axes box is ~4:1; data window is also 4:1 so a
    circle in data coords stays round. Do NOT call set_aspect('equal') —
    that path leaves Bbox without _points on Pythonista matplotlib.
    """
    n = len(DIAL_BANK)
    ax.set_xlim(0.0, 8.0)
    ax.set_ylim(0.0, 2.0)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_facecolor("#080b14")
    ax.text(0.08, 1.88, "ANALOG HEADS  ·  TRV + transistor pots  ·  no click  ·  shaft driven by α",
            color="#88a8cc", fontsize=6.5, va="top")
    rx = ry = 0.30
    for i, (key, label, style, lo, hi, _wt, _off) in enumerate(DIAL_BANK):
        state = params.get(f"dial_{key}", params.get(key, lo))
        frac = _norm(state, lo, hi)
        _draw_one_dial(ax, i + 0.50, 1.05, rx, ry, frac, label, state, style)


def create_twins_scope_image(params, figsize=None, dpi=None):
    if figsize is None:
        figsize = (7.2, 9.0) if PYTHONISTA else (10.0, 12.4)
    if dpi is None:
        dpi = 72 if PYTHONISTA else 112
    """Full scope + envelope strip. Returns (png_bytes, net_balance, twins_ratio)."""
    p, ratio, src = adapt_receiver(params)

    balance = p["balance"]
    interference_amp = p["interference_amp"]
    phase = p["phase"]
    w_fund, w_harm, w_yband, w_twins = p["w_fund"], p["w_harm"], p["w_yband"], p["w_twins"]
    master_scale = p["master_scale"]
    delta_amp, theta_amp = p["delta_amp"], p["theta_amp"]
    alpha_amp, beta_amp, gamma_amp = p["alpha_amp"], p["beta_amp"], p["gamma_amp"]
    brain_master = p["brain_master"]
    lissajous_fx, lissajous_fy = p["lissajous_fx"], p["lissajous_fy"]
    lissajous_phase = p["lissajous_phase"]
    mag_left, mag_right = p["mag_left"], p["mag_right"]
    stereo_phase, mag_compete = p["stereo_phase"], p["mag_compete"]
    source_name = p["source_name"]
    brand, wave_type = p["brand"], p["wave_type"]
    base_note, bad_freq = p["base_note"], p["bad_freq"]

    R = 1.0
    num_points = 421
    t = np.linspace(0, 2 * np.pi, num_points, endpoint=False)

    notch_on = p.get("notch_on", True)
    managed = manage_brain_vs_twins(
        t, phase, brain_master, delta_amp, theta_amp,
        alpha_amp, beta_amp, gamma_amp, notch=notch_on,
    )
    brain_contrib = managed["brain_contrib"]
    twins_ind = managed["twins_ind"]
    coupling = managed["coupling"]
    mamp = managed["managed_amp"]
    residual = managed["residual"]

    # Twins induction stays native. Directors no longer add in-phase sinusoid.
    disp_raw = interference_amp * master_scale * (
        w_fund * np.sin(2 * t + phase)
        + w_harm * np.sin(4 * t + 2.15 * phase)
        + w_yband * np.sin(6 * t + 0.65 * phase)
        + w_twins * twins_ind
        + 0.65 * brain_contrib
    )
    balanced_disp = disp_raw - np.mean(disp_raw) * balance
    mag_stereo = (
        mag_left * np.sin(2.3 * t + stereo_phase)
        - mag_right * np.cos(1.8 * t + stereo_phase * 0.7)
    ) * 0.18 * mag_compete
    balanced_disp = balanced_disp + mag_stereo * 0.6

    r_base = R + 0.09 * np.sin(2 * t) + 0.06 * np.cos(3 * t) + 0.04 * np.sin(5 * t)
    lx = np.sin(lissajous_fx * t + phase * 0.4)
    ly = np.sin(lissajous_fy * t + lissajous_phase)
    x_curve = (r_base + balanced_disp * 0.85) * (0.92 * lx + 0.08 * np.cos(t))
    y_curve = (r_base + balanced_disp * 0.85) * (0.92 * ly + 0.08 * np.sin(t))

    push_mask = balanced_disp > 0
    pull_mask = balanced_disp < 0
    push_energy = np.sum(balanced_disp[push_mask] ** 2) if np.any(push_mask) else 0.0
    pull_energy = np.sum(balanced_disp[pull_mask] ** 2) if np.any(pull_mask) else 0.0
    net_balance = (push_energy - pull_energy) / (push_energy + pull_energy + 1e-9)

    fig = plt.figure(figsize=figsize, dpi=dpi, facecolor="#05060f")
    ax = fig.add_axes([0.04, 0.40, 0.92, 0.57])
    ax.set_facecolor("#05060f")
    ax.set_aspect("equal")
    ax.set_xlim(-2.05, 2.05)
    ax.set_ylim(-1.72, 2.02)
    ax.axis("off")

    ax.text(0, 1.92, "Y-BIN TWINS SCOPE — Live Envelope + ΔΑΒΓ vs Twins notch",
            fontsize=12.5, ha="center", va="bottom", color="#a8c8ff", fontweight="bold")
    ax.text(0, 1.78, "Δ/Α/Β/Γ orthogonalized to Twins induction (3ω + 6ω)  ·  LIVE moves controls",
            fontsize=7.2, ha="center", color="#88a8cc", style="italic")

    ax.plot(lx * 1.35, ly * 1.35, color="#00ddff", linewidth=1.1, alpha=0.35, linestyle="--", zorder=1)
    ax.plot(lx * 0.95, ly * 0.95, color="#ff66aa", linewidth=0.9, alpha=0.28, linestyle=":", zorder=1)

    points = np.array([x_curve, y_curve]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    max_abs = np.max(np.abs(balanced_disp)) + 1e-9
    color_idx = (balanced_disp / max_abs + 1.0) / 2.0
    lc = LineCollection(segments, colors=plt.cm.RdBu_r(color_idx), linewidths=3.8, alpha=0.94, zorder=4)
    ax.add_collection(lc)
    ax.fill(x_curve, y_curve, color="#0f1a2e", alpha=0.35, zorder=2)

    ref_x = r_base * (0.92 * lx + 0.08 * np.cos(t))
    ref_y = r_base * (0.92 * ly + 0.08 * np.sin(t))
    ax.plot(ref_x, ref_y, color="#3a5068", linewidth=1.3, linestyle="--", alpha=0.6, zorder=2)

    focus_x = 0.12 * np.sin(phase)
    focus_y = 0.09 * np.cos(phase * 0.7)
    ax.plot(focus_x, focus_y, "o", color="#ffcc66", markersize=11, zorder=7,
            markeredgecolor="#ffaa22", markeredgewidth=1.2)
    ax.text(focus_x + 0.18, focus_y + 0.06, "FOCUS\n(pull/push\nresonance)", fontsize=6.5,
            color="#ffdd99", ha="left", fontweight="bold", zorder=8)

    arrow_step = 7
    x_a, y_a = x_curve[::arrow_step], y_curve[::arrow_step]
    disp_a = balanced_disp[::arrow_step]
    u = disp_a * np.cos(t[::arrow_step] + 0.3 * mag_stereo[::arrow_step])
    v = disp_a * np.sin(t[::arrow_step] + 0.3 * mag_stereo[::arrow_step])
    pos_idx, neg_idx = disp_a > 0.012, disp_a < -0.012
    if np.any(pos_idx):
        ax.quiver(x_a[pos_idx], y_a[pos_idx], u[pos_idx] * 0.72, v[pos_idx] * 0.72,
                  color="#ff5533", alpha=0.82, width=0.010, scale=1.0,
                  scale_units="xy", angles="xy", zorder=6)
    if np.any(neg_idx):
        ax.quiver(x_a[neg_idx], y_a[neg_idx], u[neg_idx] * 0.72, v[neg_idx] * 0.72,
                  color="#3388ff", alpha=0.82, width=0.010, scale=1.0,
                  scale_units="xy", angles="xy", zorder=6)

    cannula_angles = np.linspace(0, 2 * np.pi, 7)[:-1]
    for i, ca in enumerate(cannula_angles):
        r_end = R * 0.82
        ax.plot([0, r_end * np.cos(ca)], [0, r_end * np.sin(ca)],
                color="#ffaa44", linestyle=":", linewidth=1.1, alpha=0.5, zorder=3)
        ax.plot(r_end * np.cos(ca), r_end * np.sin(ca), marker="s", color="#ffaa44",
                markersize=4.2, alpha=0.7, zorder=5, markeredgecolor="#cc8800", markeredgewidth=0.4)

    ax.text(-1.95, 1.50, f"L-MAG: {mag_left:.2f}", fontsize=8, color="#66ffcc",
            fontweight="bold", ha="left",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#0a1528", edgecolor="#00aa88", alpha=0.85))
    ax.text(1.95, 1.50, f"R-MAG: {mag_right:.2f}", fontsize=8, color="#ff99aa",
            fontweight="bold", ha="right",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#0a1528", edgecolor="#aa3366", alpha=0.85))
    ax.text(0, 1.50, f"COMPETE×{mag_compete:.2f}", fontsize=7.5, color="#ffcc66",
            fontweight="bold", ha="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#112233", edgecolor="#ffaa00", alpha=0.9))

    gauge_y, gauge_width = -1.42, 2.35
    ax.plot([-gauge_width / 2, gauge_width / 2], [gauge_y, gauge_y],
            color="#3a4a60", linewidth=5.5, solid_capstyle="round", zorder=1)
    ax.plot([-gauge_width / 2, 0], [gauge_y, gauge_y],
            color="#3388ff", linewidth=5.5, solid_capstyle="round", zorder=2)
    ax.plot([0, gauge_width / 2], [gauge_y, gauge_y],
            color="#ff5533", linewidth=5.5, solid_capstyle="round", zorder=2)
    ax.plot([0, 0], [gauge_y - 0.06, gauge_y + 0.06], color="#a8c8ff", linewidth=2.2, zorder=3)
    marker_x = net_balance * (gauge_width / 2 - 0.05)
    ax.plot(marker_x, gauge_y, marker="^", markersize=14, color="white",
            markeredgecolor="#111111", markeredgewidth=1.2, zorder=8)
    ax.text(marker_x, gauge_y + 0.16, f"{net_balance * 100:+.1f}%",
            fontsize=9.5, ha="center", color="white", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.14", facecolor="#112233", edgecolor="none", alpha=0.92))
    ax.text(-gauge_width / 2 - 0.05, gauge_y - 0.12, "PULL\n(media/long)", fontsize=6.5,
            ha="left", color="#66aaff", fontweight="bold")
    ax.text(gauge_width / 2 + 0.05, gauge_y - 0.12, "PUSH\n(shortwave)", fontsize=6.5,
            ha="right", color="#ff7755", fontweight="bold")

    brain_str = (
        f"Δ{delta_amp:.2f}→{mamp['delta']:.2f} "
        f"Θ{theta_amp:.2f} "
        f"Α{alpha_amp:.2f}→{mamp['alpha']:.2f} "
        f"Β{beta_amp:.2f}→{mamp['beta']:.2f} "
        f"Γ{gamma_amp:.2f}→{mamp['gamma']:.2f}"
    )
    couple_str = (
        f"couple Δ{coupling['delta']:.2f} Α{coupling['alpha']:.2f} "
        f"Β{coupling['beta']:.2f} Γ{coupling['gamma']:.2f}  residual={residual:.3f}"
    )
    notch_tag = "NOTCH ON" if notch_on else "NOTCH OFF"
    info = (
        f"Amp={interference_amp:.2f}  Bal={balance:.2f}  Net={net_balance * 100:+.1f}%  Phase={phase:.2f}  {notch_tag}\n"
        f"Modes: Fund={w_fund:.2f} Harm={w_harm:.2f} Y={w_yband:.2f} Twins={w_twins:.2f}\n"
        f"Brain raw→managed: {brain_str}  ×{brain_master:.2f}\n"
        f"{couple_str}   twins_ratio={ratio:.2f}\n"
        f"SOURCE: {source_name}  |  {brand} {wave_type}  |  aim={src['aim']} @{src['beat']:.1f}Hz"
    )
    ax.text(0, 1.62, info, fontsize=6.0, ha="center", va="top", color="#b8d0ee", family="monospace",
            bbox=dict(boxstyle="round,pad=0.34", facecolor="#0a1528", edgecolor="#3a5068", alpha=0.94))

    # Analog TRV / transistor heads
    axk = fig.add_axes([0.02, 0.155, 0.96, 0.24])
    draw_dial_bank(axk, p)

    # Envelope strip
    ax2 = fig.add_axes([0.07, 0.025, 0.86, 0.14])
    ax2.set_facecolor("#080b14")
    ex, le, re = envelope_trace(p)
    ax2.fill_between(ex, le, color="#66ffcc", alpha=0.28)
    ax2.fill_between(ex, re, color="#ff99aa", alpha=0.22)
    ax2.plot(ex, 0.5 * (le + re), color="#ffcc66", lw=1.3)
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1.05)
    ax2.set_xticks([])
    ax2.tick_params(colors="#708090", labelsize=7)
    for spine in ax2.spines.values():
        spine.set_color("#2a3a55")
    ax2.set_ylabel("env", color="#88a8cc", fontsize=8)
    ax2.set_title(
        f"Envelope  ·  {notch_tag} residual={residual:.3f}  ·  twins_ratio={ratio:.2f}  ·  "
        f"codec→{src['aim']}  ·  L/R not matched",
        color="#88a8cc", fontsize=8, loc="left",
    )
    ax2.text(0.99, 0.08,
             "ΔΑΒΓ notched off Twins induction  ·  self-protection (optic+infra+ultra)",
             ha="right", color="#ffaa88", fontsize=6.5, style="italic", transform=ax2.transAxes)

    buf = BytesIO()
    # Pythonista's Agg Bbox breaks on bbox_inches='tight' + patches/equal-aspect.
    save_kw = dict(format="png", facecolor="#05060f", dpi=dpi)
    if not PYTHONISTA:
        save_kw["bbox_inches"] = "tight"
        save_kw["pad_inches"] = 0.08
    fig.savefig(buf, **save_kw)
    plt.close(fig)
    try:
        plt.close("all")
    except Exception:
        pass
    buf.seek(0)
    report = {
        "net_balance": float(net_balance),
        "twins_ratio": float(ratio),
        "residual": residual,
        "coupling": {k: float(v) for k, v in coupling.items()},
        "managed_amp": {k: float(v) for k, v in mamp.items()},
        "notch_on": notch_on,
    }
    return buf.read(), report


# ===========================================================================
# Pythonista UI — sliders move in LIVE, AGC writes managed values back
# ===========================================================================
if PYTHONISTA:

    class YBinTwinsScopeUI(ui.View):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.name = "Y-BIN TWINS SCOPE — Live Envelope"
            self.background_color = "#0a0f1a"
            self.flex = "WH"
            self.params = dict(DEFAULTS)
            self.base_ratios = {k: DEFAULTS[k] for k in ("w_fund", "w_harm", "w_yband", "w_twins")}
            self.brain_base = {k: DEFAULTS[k] for k in ("delta_amp", "theta_amp", "alpha_amp", "beta_amp", "gamma_amp")}
            self.live = False
            self.agc_on = True
            self._busy = False
            self._build_ui()
            self.layout()
            self._update_plot()

        def _build_ui(self):
            self.title_label = ui.Label()
            self.title_label.text = "Y-BIN TWINS SCOPE — Magnetic Lissajous + Envelope + Moving Controls"
            self.title_label.font = ("<system-bold>", 13)
            self.title_label.text_color = "#a8c8ff"
            self.title_label.alignment = ui.ALIGN_CENTER
            self.add_subview(self.title_label)

            self.status_label = ui.Label()
            self.status_label.text = "NOTCH takes Δ/Α/Β/Γ off Twins 3ω induction  ·  LIVE moves controls  ·  AGC manages receiver"
            self.status_label.font = ("<system>", 8)
            self.status_label.text_color = "#88a8cc"
            self.status_label.alignment = ui.ALIGN_CENTER
            self.add_subview(self.status_label)

            self.control_panel = ui.View()
            self.control_panel.background_color = "#111822"
            self.add_subview(self.control_panel)

            self.source_control = ui.SegmentedControl()
            self.source_control.segments = ["Virgin Sky", "Motorola Air", "SonyEric mW", "Custom"]
            self.source_control.selected_index = 0
            self.source_control.action = self._source_changed
            self.control_panel.add_subview(self.source_control)

            self.source_label = ui.Label()
            self.source_label.text = "Source: Virgin Skywave | skywave | F#4 listen / 1480 Hz true | aim=alpha @11.2Hz"
            self.source_label.font = ("<system-bold>", 8)
            self.source_label.text_color = "#ffcc88"
            self.source_label.alignment = ui.ALIGN_CENTER
            self.control_panel.add_subview(self.source_label)

            self.badfeeling_label = ui.Label()
            self.badfeeling_label.text = "ENV/AGC waiting  ·  Twins self-protection armed"
            self.badfeeling_label.font = ("<system>", 7)
            self.badfeeling_label.text_color = "#ff8866"
            self.badfeeling_label.alignment = ui.ALIGN_CENTER
            self.control_panel.add_subview(self.badfeeling_label)

            for label, key, lo, hi, y in SLIDER_SPEC:
                self._create_slider(self.control_panel, label, key, lo, hi, DEFAULTS[key], y)

            self.live_btn = ui.Button()
            self.live_btn.title = "LIVE ▶"
            self.live_btn.font = ("<system-bold>", 9)
            self.live_btn.background_color = "#1a4a38"
            self.live_btn.tint_color = "#66ffcc"
            self.live_btn.action = self._toggle_live
            self.control_panel.add_subview(self.live_btn)

            self.agc_btn = ui.Button()
            self.agc_btn.title = "AGC ON"
            self.agc_btn.font = ("<system-bold>", 9)
            self.agc_btn.background_color = "#3a2a10"
            self.agc_btn.tint_color = "#ffcc66"
            self.agc_btn.action = self._toggle_agc
            self.control_panel.add_subview(self.agc_btn)

            self.notch_btn = ui.Button()
            self.notch_btn.title = "NOTCH ON"
            self.notch_btn.font = ("<system-bold>", 9)
            self.notch_btn.background_color = "#102a3a"
            self.notch_btn.tint_color = "#66c2ff"
            self.notch_btn.action = self._toggle_notch
            self.control_panel.add_subview(self.notch_btn)

            self.reset_btn = ui.Button()
            self.reset_btn.title = "Reset"
            self.reset_btn.font = ("<system-bold>", 9)
            self.reset_btn.background_color = "#2a3a55"
            self.reset_btn.tint_color = "#ffffff"
            self.reset_btn.action = self._reset_all
            self.control_panel.add_subview(self.reset_btn)

            self.net_label = ui.Label()
            self.net_label.text = "Net: +0.0%   twins_ratio=0.19"
            self.net_label.font = ("<system-bold>", 9)
            self.net_label.text_color = "#ffcc66"
            self.net_label.alignment = ui.ALIGN_LEFT
            self.control_panel.add_subview(self.net_label)

            self.image_view = ui.ImageView()
            self.image_view.content_mode = ui.CONTENT_SCALE_ASPECT_FIT
            self.image_view.background_color = "#05060f"
            self.image_view.border_color = "#2a3a55"
            self.image_view.border_width = 1
            self.add_subview(self.image_view)

        def layout(self):
            w, h = self.width, self.height
            if w == 0 or h == 0:
                return
            self.title_label.frame = (0, 2, w, 22)
            self.status_label.frame = (0, 22, w, 14)
            control_height = 548
            self.control_panel.frame = (0, 38, w, control_height)
            self.source_control.frame = (8, 6, w - 16, 24)
            self.source_label.frame = (8, 32, w - 16, 15)
            self.badfeeling_label.frame = (8, 46, w - 16, 14)

            slider_left, slider_right_margin, slider_height, value_label_width = 102, 62, 16, 52
            for sv in self.control_panel.subviews:
                if isinstance(sv, ui.Slider):
                    new_width = max(135, w - slider_left - slider_right_margin)
                    sv.frame = (slider_left, sv.frame[1], new_width, slider_height)
                elif isinstance(sv, ui.Label) and (getattr(sv, "name") or "").startswith("val_"):
                    sv.frame = (w - value_label_width - 8, sv.frame[1], value_label_width, 16)

            self.live_btn.frame = (w - 314, control_height - 26, 72, 20)
            self.notch_btn.frame = (w - 236, control_height - 26, 72, 20)
            self.agc_btn.frame = (w - 158, control_height - 26, 72, 20)
            self.reset_btn.frame = (w - 78, control_height - 26, 70, 20)
            self.net_label.frame = (10, control_height - 26, 200, 18)

            image_top = 38 + control_height + 3
            self.image_view.frame = (3, image_top, w - 6, h - image_top - 3)

        def _create_slider(self, parent_view, label_text, param_name, min_val, max_val, init_val, y_pos):
            lbl = ui.Label()
            lbl.text = label_text
            lbl.font = ("<system>", 8)
            lbl.text_color = "#a8c8ff"
            lbl.frame = (6, y_pos, 94, 16)
            parent_view.add_subview(lbl)

            val_lbl = ui.Label()
            val_lbl.name = f"val_{param_name}"
            val_lbl.text = f"{init_val:.2f}"
            val_lbl.font = ("<system-bold>", 8)
            val_lbl.text_color = "#ffcc66"
            val_lbl.alignment = ui.ALIGN_RIGHT
            val_lbl.frame = (280, y_pos, 52, 16)
            parent_view.add_subview(val_lbl)

            slider = ui.Slider()
            slider.name = param_name
            slider.value = (init_val - min_val) / (max_val - min_val)
            slider.frame = (100, y_pos + 1, 160, 14)
            slider.continuous = True
            slider.action = self._slider_changed
            slider._min = min_val
            slider._max = max_val
            parent_view.add_subview(slider)

        def _write_slider(self, param, value):
            """Move a slider + its readout to a new value (used by LIVE / AGC)."""
            spec = next((s for s in SLIDER_SPEC if s[1] == param), None)
            if spec is None:
                return
            _, _, lo, hi, _ = spec
            value = max(lo, min(hi, value))
            self.params[param] = value
            for sv in self.control_panel.subviews:
                if isinstance(sv, ui.Slider) and sv.name == param:
                    sv.value = (value - lo) / (hi - lo)
                if isinstance(sv, ui.Label) and getattr(sv, "name", "") == f"val_{param}":
                    sv.text = f"{value:.2f}"

        def _source_changed(self, sender):
            s = SOURCES[sender.selected_index]
            self.params["source_name"] = s["name"]
            self.params["brand"] = s["brand"]
            self.params["wave_type"] = s["wave"]
            self.params["base_note"] = s["note"]
            self.params["bad_freq"] = s["freq"]
            self.source_label.text = (
                f"Source: {s['name']} | {s['wave']} | {s['note']} | aim={s['aim']} @{s['beat']:.1f}Hz"
            )
            self._update_plot()

        def _slider_changed(self, sender):
            param = sender.name
            raw_value = sender._min + sender.value * (sender._max - sender._min)
            self.params[param] = raw_value
            for v in self.control_panel.subviews:
                if getattr(v, "name", None) == f"val_{param}":
                    v.text = f"{raw_value:.2f}"
                    break
            if param == "master_scale":
                for mode in ("w_fund", "w_harm", "w_yband", "w_twins"):
                    new_val = max(0.0, min(1.0, self.base_ratios[mode] * raw_value))
                    self._write_slider(mode, new_val)
            if param == "brain_master":
                for bmode in ("delta_amp", "theta_amp", "alpha_amp", "beta_amp", "gamma_amp"):
                    new_val = max(0.0, min(1.0, self.brain_base[bmode] * raw_value))
                    self._write_slider(bmode, new_val)
            self._update_plot()

        def _toggle_live(self, sender):
            self.live = not self.live
            if self.live:
                self.live_btn.title = "LIVE ■"
                self.live_btn.background_color = "#3a1a1a"
                self.live_btn.tint_color = "#ff8866"
                self._tick()
            else:
                self.live_btn.title = "LIVE ▶"
                self.live_btn.background_color = "#1a4a38"
                self.live_btn.tint_color = "#66ffcc"

        def _toggle_agc(self, sender):
            self.agc_on = not self.agc_on
            self.agc_btn.title = "AGC ON" if self.agc_on else "AGC OFF"
            self.agc_btn.tint_color = "#ffcc66" if self.agc_on else "#8899aa"
            self._update_plot()

        def _toggle_notch(self, sender):
            self.params["notch_on"] = not self.params.get("notch_on", True)
            on = self.params["notch_on"]
            self.notch_btn.title = "NOTCH ON" if on else "NOTCH OFF"
            self.notch_btn.tint_color = "#66c2ff" if on else "#8899aa"
            self._update_plot()

        def _tick(self):
            if not self.live:
                return
            # Analog heads turn continuously (alpha-modulated TRV / transistor pots).
            analog_advance(self.params, dt=0.16)
            for key, _label, _style, lo, hi, _wt, _off in DIAL_BANK:
                self._write_slider(key, self.params[key])
            self._write_slider("mag_left", self.params["mag_left"])
            self._write_slider("mag_right", self.params["mag_right"])
            self._write_slider("lissajous_phase", self.params["lissajous_phase"])
            self._write_slider("stereo_phase", self.params["stereo_phase"])
            try:
                self._update_plot()
            except Exception as exc:
                self.live = False
                self.live_btn.title = "LIVE ▶"
                self.live_btn.background_color = "#1a4a38"
                self.live_btn.tint_color = "#66ffcc"
                self.badfeeling_label.text = "LIVE stopped: " + str(exc)
                return
            ui.delay(self._tick, 0.28)

        def _update_plot(self):
            if self._busy:
                return
            self._busy = True
            try:
                draw_params = dict(self.params)
                if self.agc_on:
                    managed, ratio, src = adapt_receiver(draw_params)
                    # Sliders that AGC is allowed to move (receiver side only)
                    for key in ("interference_amp", "master_scale", "gamma_amp"):
                        if abs(managed[key] - self.params[key]) > 0.008:
                            # ease the control toward managed so you see it travel
                            eased = self.params[key] + 0.35 * (managed[key] - self.params[key])
                            self._write_slider(key, eased)
                    draw_params = dict(self.params)
                    hud = (
                        f"AGC ON  twins_ratio={ratio:.2f}  aim={src['aim']}@{src['beat']:.1f}Hz  "
                        f"amp→{self.params['interference_amp']:.2f}  γ={self.params['gamma_amp']:.2f}"
                    )
                else:
                    ratio, src = twins_ratio(draw_params)
                    hud = (
                        f"AGC OFF  twins_ratio={ratio:.2f}  raw amp={self.params['interference_amp']:.2f}"
                    )
                png, report = create_twins_scope_image(draw_params)
                self.image_view.image = ui.Image.from_data(png)
                c = report["coupling"]
                self.net_label.text = (
                    f"Net: {report['net_balance']*100:+.1f}%  twins={report['twins_ratio']:.2f}  "
                    f"res={report['residual']:.3f}"
                )
                self.badfeeling_label.text = (
                    f"{hud}  ·  NOTCH {'ON' if report['notch_on'] else 'OFF'}  "
                    f"couple Δ{c['delta']:.2f} Α{c['alpha']:.2f} Β{c['beta']:.2f} Γ{c['gamma']:.2f}"
                )
            except Exception as exc:
                self.badfeeling_label.text = "plot error: " + str(exc)[:160]
            finally:
                self._busy = False

        def _reset_all(self, sender):
            self.live = False
            self.live_btn.title = "LIVE ▶"
            self.live_btn.background_color = "#1a4a38"
            self.live_btn.tint_color = "#66ffcc"
            self.params.update(DEFAULTS)
            self.notch_btn.title = "NOTCH ON"
            self.notch_btn.tint_color = "#66c2ff"
            self.source_control.selected_index = 0
            self.source_label.text = "Source: Virgin Skywave | skywave | F#4 listen / 1480 Hz true | aim=alpha @11.2Hz"
            for label, key, lo, hi, y in SLIDER_SPEC:
                self._write_slider(key, DEFAULTS[key])
            self._update_plot()

        def will_close(self):
            self.live = False


# ===========================================================================
# Launch
# ===========================================================================
def _desktop_preview(path="/home/workdir/artifacts/YBinTwinsScope_LiveEnvelope_preview.png"):
    p = dict(DEFAULTS)
    for _ in range(8):
        analog_advance(p, dt=0.16)
    png, report = create_twins_scope_image(p)
    with open(path, "wb") as f:
        f.write(png)
    print("preview", path)
    print("net", report["net_balance"], "twins_ratio", report["twins_ratio"])
    print("residual", report["residual"], "coupling", report["coupling"])
    print("managed_amp", report["managed_amp"])
    return path


def render_analog_motion(n_frames=28, out_dir="/home/workdir/artifacts/dial_frames"):
    """Write a sequence of frames with the analog heads actually travelling."""
    import os
    os.makedirs(out_dir, exist_ok=True)
    p = dict(DEFAULTS)
    paths = []
    for i in range(n_frames):
        analog_advance(p, dt=0.18)
        png, _rep = create_twins_scope_image(p, figsize=(10.0, 12.4), dpi=90)
        fp = f"{out_dir}/frame_{i:03d}.png"
        with open(fp, "wb") as f:
            f.write(png)
        paths.append(fp)
        print("frame", i, "alpha", f"{p['alpha_amp']:.3f}", "phase", f"{p['phase']:.3f}")
    return paths


if __name__ == "__main__":
    if PYTHONISTA:
        view = YBinTwinsScopeUI()
        view.present("fullscreen", hide_title_bar=False)
    else:
        import sys
        _desktop_preview()
        if "--animate" in sys.argv or True:
            render_analog_motion()
