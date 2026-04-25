"""Shared matplotlib style + reusable publication plots."""
from __future__ import annotations

from typing import Iterable

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from .config import BANDS


# =============================================================================
# Style
# =============================================================================
def apply_style() -> None:
    """Apply project-wide rcParams (legend cell 2 style tuned for readability)."""
    plt.rcParams.update({
        'figure.dpi':        120,
        'savefig.dpi':       140,
        'font.size':          10,
        'axes.titlesize':     11,
        'axes.labelsize':     10,
        'axes.titleweight':   'bold',
        'axes.spines.top':    False,
        'axes.spines.right':  False,
        'axes.grid':          True,
        'grid.alpha':         0.25,
        'grid.linestyle':     '--',
        'legend.frameon':     False,
        'legend.fontsize':    9,
        'xtick.labelsize':    9,
        'ytick.labelsize':    9,
        'lines.linewidth':    1.1,
    })


# Colour scheme keyed by experiment / condition
STYLE_COLORS = {
    # Experiment 1 — E1PRE pre-sleep supine; E1A–C postural ramp
    'E1PRE': '#4C72B0',  # supine pre-sleep (validation)
    'E1A': '#5A9BD5',    # supine post-sleep
    'E1B': '#55A868',    # sitting
    'E1C': '#C44E52',    # standing
    # Experiment 2 - breath hold
    'E2A_insp_1': '#937860',
    'E2A_insp_2': '#B59D80',
    'E2B_exp_1':  '#8172B2',
    'E2B_exp_2':  '#A79BC5',
    # Experiment 3 - walking
    'E3_walk': '#CCB974',
    # Experiment 4A - paced breathing
    'E4A_3pm':  '#2E4057',
    'E4A_5pm':  '#4C72B0',
    'E4A_6pm':  '#55A868',
    'E4A_9pm':  '#DD8452',
    'E4A_12pm': '#C44E52',
    # Experiment 4B - sleep
    'E4B_sleep': '#64B5CD',
}

BAND_COLORS = {'VLF': '#cccccc', 'LF': '#f4a261', 'HF': '#2a9d8f'}

# Grayscale fills echoing common journal HRV figures (dark LF, light HF).
BAND_COLORS_JOURNAL = {
    'VLF': '#dddddd',
    'LF':  'dimgray',
    'HF':  'lightgray',
}


def _band_fill_colors(journal_grayscale: bool,
                      band_colors: dict | None) -> dict:
    base = BAND_COLORS_JOURNAL if journal_grayscale else BAND_COLORS
    if band_colors:
        return {**base, **band_colors}
    return base


def _metrics_inset_text(fd: dict, welch_note: str | None = None) -> str:
    lf = fd.get('lf_ms2', float('nan'))
    hf = fd.get('hf_ms2', float('nan'))
    tp = fd.get('total_power_ms2', float('nan'))
    lhr = fd.get('lf_hf_ratio', float('nan'))
    lfn = fd.get('lf_nu', float('nan'))
    hfn = fd.get('hf_nu', float('nan'))
    lines = [
        f"TP  = {tp:7,.0f} ms²",
        f"LF  = {lf:7,.0f} ms²   ({lfn:4.1f} n.u.)",
        f"HF  = {hf:7,.0f} ms²   ({hfn:4.1f} n.u.)",
        f"LF/HF = {lhr:6.2f}",
    ]
    if welch_note:
        lines.append(welch_note)
    return "\n".join(lines)


# =============================================================================
# Plots
# =============================================================================
def plot_rr_tachogram(rr_ms: np.ndarray, rr_times: np.ndarray,
                      ax=None, color: str = '#333333',
                      label: str | None = None,
                      title: str | None = None,
                      event_markers: Iterable[tuple[float, str]] | None = None,
                      ylim: tuple[float, float] | None = None,
                      linewidth: float = 0.7,
                      lw: float | None = None):
    """Plot an RR-interval tachogram with optional event markers.

    event_markers : iterable of (t_s, annotation) drawn as vertical dashed lines.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 3))
    w = float(lw) if lw is not None else linewidth
    if rr_ms.size > 0:
        ax.plot(rr_times, rr_ms, color=color, marker='.', markersize=3,
                linestyle='-', linewidth=w, label=label)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('RR (ms)')
    if ylim is not None:
        ax.set_ylim(*ylim)
    if title:
        ax.set_title(title)
    if event_markers:
        y0, y1 = ax.get_ylim()
        for t_ev, annot in event_markers:
            ax.axvline(t_ev, color='k', linestyle='--', linewidth=0.8, alpha=0.6)
            ax.text(t_ev, y1, f' {annot}', fontsize=8, va='top')
    if label:
        ax.legend(loc='best')
    return ax


def plot_rr_psd_pub(f: np.ndarray, p: np.ndarray,
                    ax=None, color: str = '#333333',
                    label: str | None = None,
                    title: str | None = None,
                    fill_std: np.ndarray | None = None,
                    bands: dict | None = None,
                    annotate_peaks: bool = True,
                    logy: bool = True,
                    xlim: tuple[float, float] = (0.0, 0.5)):
    """Publication-style RR PSD plot with band shading + optional error band.

    Parameters
    ----------
    f, p       : frequency axis and power spectral density.
    fill_std   : if given, shades (p - std .. p + std) around the line.
    bands      : dict of {name: (lo, hi)}; shades band regions behind the line.
                 Defaults to config.BANDS (VLF/LF/HF).
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 4))
    if bands is None:
        bands = BANDS

    ymin = max(1e-6, np.nanmin(p[p > 0])) if (p > 0).any() else 1e-6
    ymax = np.nanmax(p) * 2 if p.size else 1.0

    for bname, (blo, bhi) in bands.items():
        ax.axvspan(blo, bhi, color=BAND_COLORS.get(bname, '#cccccc'),
                   alpha=0.18, zorder=0)

    if fill_std is not None and fill_std.size == p.size:
        ax.fill_between(f, np.maximum(p - fill_std, 1e-9), p + fill_std,
                        color=color, alpha=0.2, linewidth=0)

    ax.plot(f, p, color=color, linewidth=1.3, label=label)

    if annotate_peaks:
        for bname, (blo, bhi) in bands.items():
            if bname == 'VLF':
                continue
            m = (f >= blo) & (f < bhi)
            if not m.any():
                continue
            i_pk = np.argmax(p[m])
            f_pk = f[m][i_pk]
            p_pk = p[m][i_pk]
            if p_pk > ymin:
                ax.plot(f_pk, p_pk, marker='v', color=color, markersize=6)
                ax.annotate(f'{bname} peak\n{f_pk:.3f} Hz',
                            xy=(f_pk, p_pk), xytext=(6, 8),
                            textcoords='offset points', fontsize=8)

    if logy:
        ax.set_yscale('log')
    ax.set_xlim(*xlim)
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('PSD (ms²/Hz)')
    if title:
        ax.set_title(title)
    if label:
        ax.legend(loc='upper right')
    return ax


def plot_rr_psd_stacked(items, bands: dict | None = None,
                        xlim: tuple[float, float] = (0.04, 0.5),
                        logy: bool = False,
                        style: str = 'filled',
                        mark_peak: bool = True,
                        metrics_box: bool = True,
                        peak_range: tuple[float, float] = (0.04, 0.40),
                        row_height: float = 2.1,
                        fig_width: float = 11.0,
                        suptitle: str | None = None,
                        fill_under: bool | None = None,
                        psd_ylim: None | str | tuple[float, float] = None,
                        journal_grayscale: bool = False,
                        band_colors: dict | None = None):
    """Stacked-subplots RR PSD (one panel per condition), shared X axis.

    Two visual styles:

    * ``style='filled'`` (default) — the curve itself is used as the top
      edge of a coloured LF / HF fill, so the shaded area literally equals
      the integrated band power. Best when you want to emphasise total
      variance differences between conditions (e.g. supine vs standing).

    * ``style='textbook'`` — clean line with vertical grey lines at band
      boundaries and floating ``LF`` / ``HF`` text labels, echoing the
      classical HRV schematic found in Task Force 1996 and most
      textbooks. Best when peaks are narrow and you want them to read
      at a glance (e.g. paced-breathing conditions).

    Both styles share:
        ① linear Y: per-panel autoscale (0 → max × 1.18) by default, or a
           shared limit via ``psd_ylim='global'`` / a fixed ``(0, ymax)`` tuple;
        ② a red ★ at the dominant peak within ``peak_range`` with
           frequency annotated;
        ③ a monospace metrics box (LF / HF / LF·HF⁻¹) in the top-right;
        ④ optional per-item ``target_hz`` rendered as a red dashed
           vertical line (useful for paced-breathing / resonance tests).

    Parameters
    ----------
    items : list of dict, each with
        'key'       — short id (e.g. 'E1PRE', 'E1A')
        'subtitle'  — posture/condition string
        'f', 'p'    — frequency axis and PSD (ms²/Hz)
        'color'     — line color
        'fd'        — dict from pipeline.frequency_domain_hrv
                      (total_power_ms2, vlf_ms2, lf_ms2, hf_ms2,
                       lf_nu, hf_nu, lf_hf_ratio)
        'target_hz' — optional expected peak frequency (Hz) to mark
    style       : 'filled' | 'textbook'.
    logy        : set True only if you need to compare peak heights across
                  panels of very different variances (e.g. sleep stages).
    mark_peak   : red ★ + annotation at the dominant peak inside peak_range.
    metrics_box : right-top textbox with LF / HF / LF·HF⁻¹.
    peak_range  : (lo, hi) in Hz — where to look for the dominant peak.
    fill_under  : legacy alias for style ('filled' if True, 'textbook' if
                  False). Overrides ``style`` when provided.
    psd_ylim    : ``None`` (per-panel autoscale), ``'global'`` (shared max from
                  all panels inside ``xlim``), or ``(0, ymax)`` fixed limits.
    journal_grayscale : if True, LF/HF/VLF fills use grayscale journal palette.
    band_colors : optional overrides for band fill colours (merged with base).
    """
    if bands is None:
        bands = BANDS

    if fill_under is not None:
        style = 'filled' if fill_under else 'textbook'
    if style not in ('filled', 'textbook'):
        raise ValueError(f"style must be 'filled' or 'textbook', got {style!r}")

    fills = _band_fill_colors(journal_grayscale, band_colors)

    psd_ylim_fixed: tuple[float, float] | None = None
    if not logy and psd_ylim == 'global':
        gmax = 0.0
        for it in items:
            f = np.asarray(it['f'])
            p = np.asarray(it['p'])
            m_view = (f >= xlim[0]) & (f <= xlim[1])
            if m_view.any():
                gmax = max(gmax, float(np.nanmax(p[m_view])))
        psd_ylim_fixed = (0.0, gmax * 1.05) if gmax > 0 else (0.0, 1.0)
    elif isinstance(psd_ylim, tuple):
        psd_ylim_fixed = psd_ylim

    n = len(items)
    fig, axes = plt.subplots(n, 1, figsize=(fig_width, row_height * n),
                             sharex=True)
    if n == 1:
        axes = [axes]

    band_edges = sorted({e for b in bands.values() for e in b
                         if xlim[0] <= e <= xlim[1]})
    lf_lo, lf_hi = bands['LF']
    hf_lo, hf_hi = bands['HF']
    lf_center = 0.5 * (lf_lo + lf_hi)
    hf_center = 0.5 * (hf_lo + hf_hi)

    for ax, it in zip(axes, items):
        f   = np.asarray(it['f'])
        p   = np.asarray(it['p'])
        fd  = it.get('fd', {})
        col = it.get('color', '#333333')
        tgt = it.get('target_hz', None)

        if style == 'filled':
            for bname, (blo, bhi) in bands.items():
                if bname == 'VLF' and xlim[0] >= bhi:
                    continue
                m = (f >= blo) & (f <= bhi)
                if m.sum() > 1:
                    ax.fill_between(f[m], 0.0, p[m],
                                    color=fills.get(bname, '#cccccc'),
                                    alpha=0.45, zorder=1,
                                    linewidth=0)
        else:
            for edge in band_edges:
                ax.axvline(edge, color='#888888', linewidth=0.8,
                           alpha=0.6, zorder=0)

        ax.plot(f, p, color=col, linewidth=1.6, zorder=3)

        if tgt is not None and xlim[0] <= tgt <= xlim[1]:
            ax.axvline(tgt, color='crimson', linestyle='--',
                       linewidth=1.1, alpha=0.75, zorder=2)

        if mark_peak:
            m = (f >= peak_range[0]) & (f <= peak_range[1])
            if m.any() and float(np.nanmax(p[m])) > 0:
                i_pk = int(np.argmax(p[m]))
                f_pk = float(f[m][i_pk])
                p_pk = float(p[m][i_pk])
                # In textbook mode the target line is red, so use the
                # curve colour for the peak marker to avoid confusion.
                pk_col = col if style == 'textbook' else 'red'
                ax.plot(f_pk, p_pk, marker='*', color=pk_col,
                        markersize=15, zorder=5,
                        markeredgecolor='black', markeredgewidth=0.6)
                ax.annotate(f'Peak: {f_pk:.3f} Hz',
                            xy=(f_pk, p_pk),
                            xytext=(14, 10), textcoords='offset points',
                            fontsize=9, fontweight='bold', color=pk_col,
                            arrowprops=dict(arrowstyle='->', color=pk_col,
                                            lw=1.0))

        if metrics_box:
            lf  = fd.get('lf_ms2', float('nan'))
            hf  = fd.get('hf_ms2', float('nan'))
            tp  = fd.get('total_power_ms2', float('nan'))
            lhr = fd.get('lf_hf_ratio', float('nan'))
            lfn = fd.get('lf_nu', float('nan'))
            hfn = fd.get('hf_nu', float('nan'))
            txt = _metrics_inset_text(fd)
            ax.text(0.985, 0.95, txt,
                    transform=ax.transAxes, fontsize=8.5,
                    va='top', ha='right', fontfamily='monospace',
                    bbox=dict(boxstyle='round,pad=0.4',
                              facecolor='lightyellow',
                              edgecolor='grey', alpha=0.9),
                    zorder=6)

        if logy:
            ax.set_yscale('log')
            pos = p[p > 0]
            if pos.size:
                ax.set_ylim(max(1e-3, np.nanpercentile(pos, 1) / 2.0),
                            np.nanmax(p) * 2.5)
        else:
            if psd_ylim_fixed is not None:
                ax.set_ylim(*psd_ylim_fixed)
            else:
                m_view = (f >= xlim[0]) & (f <= xlim[1])
                pk_view = float(np.nanmax(p[m_view])) if m_view.any() else 0.0
                if pk_view > 0:
                    ax.set_ylim(0, pk_view * 1.18)

        if style == 'textbook':
            ylo, yhi = ax.get_ylim()
            y_label = ylo + 0.86 * (yhi - ylo)
            for name, xc in (('LF', lf_center), ('HF', hf_center)):
                if xlim[0] <= xc <= xlim[1]:
                    ax.text(xc, y_label, name, ha='center', va='center',
                            fontsize=10, fontweight='bold',
                            color='#555555', zorder=4,
                            bbox=dict(boxstyle='round,pad=0.15',
                                      facecolor='white',
                                      edgecolor='none', alpha=0.85))

        title_line = f"{it['key']} — {it.get('subtitle', '')}"
        ax.set_title(title_line, fontsize=10, loc='left', pad=4)
        ax.set_ylabel('PSD (ms²/Hz)')

    for ax in axes[:-1]:
        ax.tick_params(labelbottom=False)
    axes[-1].set_xlabel('Frequency (Hz)')
    axes[0].set_xlim(*xlim)

    if style == 'filled':
        band_handles = []
        for bname in ('LF', 'HF'):
            blo, bhi = bands[bname]
            band_handles.append(Rectangle(
                (0, 0), 1, 1, color=fills[bname], alpha=0.5,
                label=f'{bname} ({blo:.2f}–{bhi:.2f} Hz)'))
        if xlim[0] < bands['VLF'][1]:
            blo, bhi = bands['VLF']
            band_handles.insert(0, Rectangle(
                (0, 0), 1, 1, color=fills['VLF'], alpha=0.5,
                label=f'VLF ({blo:.3f}–{bhi:.2f} Hz)'))
        axes[0].legend(handles=band_handles, loc='upper left',
                       fontsize=8, frameon=True, framealpha=0.9)

    if suptitle:
        fig.suptitle(suptitle, fontsize=12, y=1.0)
    fig.tight_layout()
    return fig, axes


# Stronger VLF/LF/HF under-curve fills for RR PSD (Task Force-style contrast).
_PSD_JOURNAL_FILLS: dict[str, tuple[str, float]] = {
    'VLF': ('#d8d8d8', 0.30),
    'LF':  ('#3a3a3a', 0.58),
    'HF':  ('#a8a8a8', 0.48),
}


def _tachogram_hrv_metrics_str(td: dict) -> str:
    hr = td.get('mean_hr_bpm', float('nan'))
    sd = td.get('sdnn_ms', float('nan'))
    rm = td.get('rmssd_ms', float('nan'))
    if not (np.isfinite(hr) and np.isfinite(sd) and np.isfinite(rm)):
        return ''
    return f'HR {hr:.0f} bpm · SDNN {sd:.1f} · RMSSD {rm:.1f} ms'


def _annotate_lf_hf_peaks(
        ax, f: np.ndarray, p: np.ndarray, bands: dict,
        lf_color: str = '0.25', hf_color: str = '0.35') -> None:
    """Label dominant LF and HF bin on the displayed PSD (same f,p as the plot)."""
    f = np.asarray(f, dtype=float)
    p = np.asarray(p, dtype=float)
    lo, hi = bands['LF']
    m = (f >= lo) & (f < hi) & np.isfinite(p) & (p > 0)
    if m.any():
        k = int(np.argmax(p[m]))
        f_pk = float(f[m][k])
        p_pk = float(p[m][k])
        ax.annotate(
            f'LF peak {f_pk:.2f} Hz',
            xy=(f_pk, p_pk), xytext=(5, 10), textcoords='offset points',
            fontsize=7.5, color=lf_color,
            arrowprops=dict(arrowstyle='->', color=lf_color, alpha=0.5, lw=0.7),
        )
    lo, hi = bands['HF']
    m = (f >= lo) & (f < hi) & np.isfinite(p) & (p > 0)  # [lo, hi) like trapz
    if m.any():
        k = int(np.argmax(p[m]))
        f_pk = float(f[m][k])
        p_pk = float(p[m][k])
        br = f_pk * 60.0
        ax.annotate(
            f'HF peak {f_pk:.2f} Hz\n(~{br:.0f} breaths/min)',
            xy=(f_pk, p_pk), xytext=(8, -18), textcoords='offset points',
            fontsize=7.5, color=hf_color, ha='left', va='top',
            arrowprops=dict(arrowstyle='->', color=hf_color, alpha=0.5, lw=0.7),
        )


def plot_rr_tachogram_psd_grid(
        items,
        bands: dict | None = None,
        xlim: tuple[float, float] = (0.0, 0.5),
        fig_width_per_col: float = 2.95,
        row_height: float = 2.45,
        suptitle: str | None = None,
        suptitle_y: float = 0.99,
        tachogram_color: str = 'black',
        psd_line_color: str | None = 'black',
        mark_peak: bool = False,
        metrics_box: bool = True,
        peak_range: tuple[float, float] = (0.04, 0.40),
        welch_note: str | None = 'PSD: Welch, Hann',
        rr_ylim_pad: tuple[float, float] = (0.98, 1.02),
        psd_ylim: None | str | tuple[float, float] = 'per_column',
        psd_yscale: str = 'log',
        band_strong: bool = True,
        band_colors: dict | None = None,
        fill_alpha: float = 0.55,
        annotate_lf_hf_peaks: bool = True):
    """2×N grid: RR tachogram (top) and RR PSD (bottom) per condition.

    Matches common journal layouts (tachogram aligned with its spectrum,
    high-contrast VLF/LF/HF under-curve fills, metrics inset on PSD panels).

    Each item dict requires:
        ``key``, ``subtitle``, ``f``, ``p``, ``fd`` (frequency_domain_hrv),
        ``rr_times``, ``rr_ms`` (same units as the pipeline NK series).
    Optional per item: ``tachogram_title`` (str, e.g. two-line short title),
    ``td`` or ``td_hrv`` (time-domain dict for HR/SDNN/RMSSD text on tachogram).

    Parameters
    ----------
    psd_ylim
        ``'per_column'`` (default) — each column autoscales to its own PSD
        in ``xlim``; ``'global'`` or ``None`` — one y-scale for all columns;
        or ``(y0, y1)`` fixed limits (same for every column, ``psd_yscale``).
    psd_yscale
        ``'log'`` (default) or ``'linear'``. Log helps small-power postures
        stay visible next to a large supine peak.
    band_strong
        If True, use high-contrast grayscale fills; if False, use
        :data:`BAND_COLORS_JOURNAL` and ``fill_alpha`` as before.
    annotate_lf_hf_peaks
        If True, annotate TF LF/HF band argmax on the plotted PSD curve
        (re breath rate for HF in min⁻¹).
    suptitle_y
        Matplotlib :func:`~matplotlib.figure.Figure.suptitle` y position.
    """
    if bands is None:
        bands = BANDS
    n = len(items)
    if n == 0:
        raise ValueError('items must be non-empty')
    if psd_yscale not in ('log', 'linear'):
        raise ValueError("psd_yscale must be 'log' or 'linear'")

    fig, axs = plt.subplots(
        2, n, figsize=(fig_width_per_col * n, row_height * 2),
        sharex='row', sharey=False, layout='constrained')
    if n == 1:
        axes = np.asarray(axs).reshape(2, 1)
    else:
        axes = axs

    weak_fills = _band_fill_colors(True, band_colors)
    if band_strong:
        fills: dict = {k: v[0] for k, v in _PSD_JOURNAL_FILLS.items()}
        fill_alphas = {k: v[1] for k, v in _PSD_JOURNAL_FILLS.items()}
    else:
        fills = dict(weak_fills)
        fill_alphas = {b: float(fill_alpha) for b in bands}

    rr_mins: list[float] = []
    rr_maxs: list[float] = []
    for it in items:
        rr = np.asarray(it['rr_ms'], dtype=float)
        if rr.size:
            rr_mins.append(float(np.nanmin(rr)))
            rr_maxs.append(float(np.nanmax(rr)))
    if rr_mins:
        p_lo, p_hi = rr_ylim_pad
        rr_ylim = (min(rr_mins) * p_lo, max(rr_maxs) * p_hi)
    else:
        rr_ylim = (0.0, 1.0)

    gmax = 0.0
    for it in items:
        f = np.asarray(it['f'])
        p = np.asarray(it['p'])
        m_view = (f >= xlim[0]) & (f <= xlim[1])
        if m_view.any():
            gmax = max(gmax, float(np.nanmax(p[m_view])))

    shared_ylim: tuple[float, float] | None = None
    if psd_ylim in (None, 'global'):
        if gmax > 0:
            if psd_yscale == 'log':
                y1 = gmax * 1.1
                y0 = max(y1 / 1e4, 1e-12)
                shared_ylim = (y0, y1)
            else:
                shared_ylim = (0.0, gmax * 1.05)
        else:
            shared_ylim = (1e-12, 1.0) if psd_yscale == 'log' else (0.0, 1.0)
    elif psd_ylim == 'per_column':
        shared_ylim = None
    elif isinstance(psd_ylim, tuple):
        y_lo, y_hi = psd_ylim
        if psd_yscale == 'log' and y_lo <= 0 and y_hi > 0:
            y_lo = max(y_hi / 1e4, 1e-12)
        shared_ylim = (y_lo, y_hi)
    else:
        raise ValueError("psd_ylim must be 'global', None, 'per_column', or (y0, y1)")

    for j, it in enumerate(items):
        ax_t = axes[0, j]
        ax_p = axes[1, j]
        rt = np.asarray(it['rr_times'], dtype=float)
        rr = np.asarray(it['rr_ms'], dtype=float)
        f = np.asarray(it['f'])
        p = np.asarray(it['p'])
        fd = it.get('fd', {})
        col = it.get('color', '#333333')
        line_col = col if psd_line_color is None else psd_line_color
        tgt = it.get('target_hz', None)

        if rt.size and rr.size:
            ax_t.plot(rt, rr, color=tachogram_color, linewidth=0.8)

        t_title = it.get('tachogram_title')
        if t_title is None:
            t_title = f"{it['key']} — {it.get('subtitle', '')}"
        ax_t.set_title(t_title, fontsize=10, loc='left', pad=6)

        td = it.get('td', it.get('td_hrv'))
        if isinstance(td, dict) and _tachogram_hrv_metrics_str(td):
            ax_t.text(0.02, 0.98, _tachogram_hrv_metrics_str(td),
                      transform=ax_t.transAxes, fontsize=7.5, va='top', ha='left',
                      color='0.2',
                      bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                                edgecolor='0.6', alpha=0.9),
                      zorder=5)

        for bname, (blo, bhi) in bands.items():
            if bname == 'VLF' and xlim[0] >= bhi:
                continue
            # Match pipeline trapezoid bands: [lo, hi) except clip display to xlim.
            m = (f >= blo) & (f < bhi) & (f >= xlim[0]) & (f <= xlim[1])
            if not m.any():
                continue
            a_fill = float(fill_alphas.get(bname, fill_alpha))
            ax_p.fill_between(
                f[m], 0.0, p[m], color=fills.get(bname, '#cccccc'),
                alpha=a_fill, zorder=1, linewidth=0)

        ax_p.plot(f, p, color=line_col, linewidth=1.0, zorder=3)

        if tgt is not None and xlim[0] <= tgt <= xlim[1]:
            ax_p.axvline(tgt, color='crimson', linestyle='--',
                         linewidth=1.1, alpha=0.75, zorder=2)

        if mark_peak:
            m_pk = (f >= peak_range[0]) & (f <= peak_range[1])
            if m_pk.any() and float(np.nanmax(p[m_pk])) > 0:
                i_pk = int(np.argmax(p[m_pk]))
                f_pk = float(f[m_pk][i_pk])
                p_pk = float(p[m_pk][i_pk])
                ax_p.plot(f_pk, p_pk, marker='*', color='red',
                          markersize=14, zorder=5,
                          markeredgecolor='black', markeredgewidth=0.5)
                ax_p.annotate(
                    f'Peak: {f_pk:.3f} Hz', xy=(f_pk, p_pk),
                    xytext=(10, 8), textcoords='offset points',
                    fontsize=8, fontweight='bold', color='red',
                    arrowprops=dict(arrowstyle='->', color='red', lw=0.8))

        if metrics_box:
            txt = _metrics_inset_text(fd, welch_note=welch_note)
            ax_p.text(
                0.985, 0.97, txt, transform=ax_p.transAxes, fontsize=8.0,
                va='top', ha='right', fontfamily='monospace',
                bbox=dict(boxstyle='round,pad=0.35', facecolor='white',
                          edgecolor='grey', alpha=0.92),
                zorder=6)

        ax_p.set_xlim(*xlim)
        m_view = (f >= xlim[0]) & (f <= xlim[1])
        p_view = p[m_view]
        p_pos = p_view[(p_view > 0) & np.isfinite(p_view)]

        if psd_ylim == 'per_column':
            if psd_yscale == 'log':
                if p_pos.size:
                    pmax = float(np.nanmax(p_pos))
                    pmin = max(pmax / (10.0 ** 4.0), 1e-12)
                else:
                    pmin, pmax = 1e-9, 1.0
                ax_p.set_yscale('log')
                ax_p.set_ylim(pmin, pmax * 1.1)
            else:
                ymax = float(np.nanmax(p_pos)) * 1.05 if p_pos.size else 1.0
                ax_p.set_yscale('linear')
                ax_p.set_ylim(0.0, ymax)
        else:
            assert shared_ylim is not None
            y0, y1 = shared_ylim
            ax_p.set_yscale(psd_yscale)
            ax_p.set_ylim(y0, y1)

        if annotate_lf_hf_peaks and p.size:
            _annotate_lf_hf_peaks(ax_p, f, p, bands)

        if j == 0:
            ax_t.set_ylabel('RR (ms)')
            ax_p.set_ylabel('PSD (ms²/Hz)')
        ax_t.set_xlabel('Time (s)')
        ax_p.set_xlabel('Frequency (Hz)')

    for j in range(n):
        axes[0, j].set_ylim(*rr_ylim)
    if n > 1:
        for j in range(1, n):
            axes[0, j].tick_params(labelleft=False)
            axes[1, j].tick_params(labelleft=False)

    # Legend colors match actual fills
    leg_fills: dict
    if band_strong:
        leg_fills = {k: _PSD_JOURNAL_FILLS[k][0] for k in _PSD_JOURNAL_FILLS}
        leg_alphas = {k: _PSD_JOURNAL_FILLS[k][1] for k in _PSD_JOURNAL_FILLS}
    else:
        leg_fills = {**weak_fills}
        leg_alphas = {b: 0.55 for b in bands}
    band_handles: list[Rectangle] = []
    if xlim[0] < bands['VLF'][1]:
        blo, bhi = bands['VLF']
        band_handles.append(Rectangle(
            (0, 0), 1, 1, color=leg_fills['VLF'], alpha=leg_alphas.get('VLF', 0.4),
            label=f'VLF ({blo:.3f}–{bhi:.2f} Hz)'))
    for bname in ('LF', 'HF'):
        blo, bhi = bands[bname]
        band_handles.append(Rectangle(
            (0, 0), 1, 1, color=leg_fills[bname], alpha=leg_alphas.get(bname, 0.5),
            label=f'{bname} ({blo:.2f}–{bhi:.2f} Hz)'))
    axes[1, 0].legend(handles=band_handles, loc='upper left', fontsize=7.5,
                      frameon=True, framealpha=0.92)

    if suptitle:
        fig.suptitle(suptitle, fontsize=12, y=suptitle_y)
    return fig, axes


def plot_ecg_psd_with_harmonics(f: np.ndarray, p: np.ndarray,
                                 mean_hr_bpm: float,
                                 respiratory_hz: float | None = None,
                                 ax=None, color: str = '#333333',
                                 label: str | None = None,
                                 title: str | None = None,
                                 xlim: tuple[float, float] = (0.05, 5.0),
                                 n_harmonics: int = 4,
                                 y_decades: float = 5.0):
    """ECG-band PSD plot annotating HR harmonics (f0, 2f0, …) and the
    respiratory peak.

    Y axis is clamped to ``y_decades`` orders of magnitude below the
    in-view peak, so the harmonic comb stays legible instead of being
    flattened into a thin strip by the default matplotlib autoscale
    (which happily extends to 10⁻²² on noise-floor data).
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4))
    ax.semilogy(f, p, color=color, linewidth=0.9, label=label)

    m_view = (f >= xlim[0]) & (f <= xlim[1])
    if m_view.any():
        p_view = p[m_view]
        p_view = p_view[p_view > 0]
        if p_view.size:
            ymax = float(np.nanmax(p_view)) * 3.0
            ymin = ymax / (10 ** y_decades)
            ax.set_ylim(ymin, ymax)

    f0 = mean_hr_bpm / 60.0 if np.isfinite(mean_hr_bpm) else None
    y_top = ax.get_ylim()[1]
    y_bot = ax.get_ylim()[0]
    if f0 is not None:
        for k in range(1, n_harmonics + 1):
            fk = k * f0
            if xlim[0] <= fk <= xlim[1]:
                ax.axvline(fk, color='tab:red', linestyle=':',
                           alpha=0.6, linewidth=0.9)
                ax.text(fk, y_top,
                        f' {k}f0' if k > 1 else f' f0={f0:.2f}Hz',
                        color='tab:red', fontsize=8,
                        va='top', ha='left')

    if respiratory_hz is not None and np.isfinite(respiratory_hz) \
            and xlim[0] <= respiratory_hz <= xlim[1]:
        ax.axvline(respiratory_hz, color='tab:blue', linestyle='-.',
                   alpha=0.6, linewidth=0.9)
        ax.text(respiratory_hz, y_bot,
                f' resp {respiratory_hz:.2f}Hz',
                color='tab:blue', fontsize=8,
                va='bottom', ha='left')

    ax.set_xlim(*xlim)
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('PSD (mV²/Hz)')
    if title:
        ax.set_title(title)
    if label:
        ax.legend(loc='upper right')
    return ax


def plot_spectrogram_rr(f: np.ndarray, t: np.ndarray, Sxx: np.ndarray,
                        ax=None, title: str | None = None,
                        event_markers: Iterable[tuple[float, str]] | None = None,
                        ymax: float = 0.5, *,
                        log_scale: str = 'db',
                        vmin: float | None = None,
                        vmax: float | None = None):
    """Plot an RR spectrogram with optional event markers.

    log_scale
        ``'db'`` (default) — 10·log10(PSD), label in dB.
        ``'log10'`` — log10(PSD) for a wider linear color dynamic range
        of weak HF power vs LF.
        ``'linear'`` — raw PSD (m²/Hz); poor contrast for mixed LF/HF.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 4))
    if Sxx.size == 0:
        ax.text(0.5, 0.5, '(spectrogram unavailable — too few RR intervals)',
                ha='center', va='center', transform=ax.transAxes)
        return ax
    m = f <= ymax
    eps = 1e-12
    if log_scale == 'db':
        Z = 10.0 * np.log10(Sxx[m] + eps)
        cblabel = '10·log10(PSD)  [dB]'
    elif log_scale == 'log10':
        Z = np.log10(Sxx[m] + eps)
        cblabel = 'log10(PSD)  (ms²/Hz)'
    elif log_scale == 'linear':
        Z = Sxx[m]
        cblabel = 'PSD (ms²/Hz)'
    else:
        raise ValueError("log_scale must be 'db', 'log10', or 'linear'")
    mesh = ax.pcolormesh(t, f[m], Z, shading='gouraud', cmap='viridis',
                         vmin=vmin, vmax=vmax)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Frequency (Hz)')
    ax.set_ylim(0, ymax)
    for bname, (blo, bhi) in BANDS.items():
        if bname == 'VLF':
            continue
        ax.axhline(blo, color='w', linestyle=':', linewidth=0.8, alpha=0.6)
        ax.axhline(bhi, color='w', linestyle=':', linewidth=0.8, alpha=0.6)
    if event_markers:
        for t_ev, annot in event_markers:
            ax.axvline(t_ev, color='white', linestyle='--',
                       linewidth=1.0, alpha=0.8)
            ax.text(t_ev, ymax * 0.95, f' {annot}',
                    color='white', fontsize=8, va='top')
    if title:
        ax.set_title(title)
    cb = plt.colorbar(mesh, ax=ax, pad=0.01)
    cb.set_label(cblabel)
    return ax


def plot_duration_sweep(df_sweep, metrics=('sdnn_ms', 'lf_ms2', 'hf_ms2'),
                        fig=None):
    """Plot Figure 1.4 — mean ± std over window length, one panel per metric,
    with CV% annotated at each point.

    df_sweep is the DataFrame returned by pipeline.duration_effect_sweep().
    """
    if fig is None:
        fig, axes = plt.subplots(1, len(metrics), figsize=(4.2 * len(metrics), 4))
    else:
        axes = fig.subplots(1, len(metrics))
    if len(metrics) == 1:
        axes = [axes]

    for ax, metric in zip(axes, metrics):
        sub = df_sweep[df_sweep['metric'] == metric].sort_values('window_s')
        if sub.empty:
            continue
        W   = sub['window_s'].to_numpy(dtype=float)
        M   = sub['mean'].to_numpy(dtype=float)
        S   = sub['std'].to_numpy(dtype=float)
        cv  = sub['cv_pct'].to_numpy(dtype=float)

        ax.errorbar(W, M, yerr=np.where(np.isfinite(S), S, 0.0),
                    marker='o', capsize=4, color='#4C72B0', ecolor='#4C72B0')
        ax.fill_between(W, M - np.where(np.isfinite(S), S, 0.0),
                        M + np.where(np.isfinite(S), S, 0.0),
                        color='#4C72B0', alpha=0.15)

        for xi, yi, ci in zip(W, M, cv):
            if np.isfinite(ci):
                ax.annotate(f'CV {ci:.1f}%',
                            xy=(xi, yi), xytext=(4, 6),
                            textcoords='offset points', fontsize=8,
                            color='#555555')

        ax.set_xlabel('Window length (s)')
        ax.set_ylabel(metric.replace('_', ' '))
        ax.set_title(f'Duration effect — {metric}')

    fig.tight_layout()
    return fig


__all__ = [
    'apply_style', 'STYLE_COLORS', 'BAND_COLORS', 'BAND_COLORS_JOURNAL',
    'plot_rr_tachogram', 'plot_rr_psd_pub', 'plot_rr_psd_stacked',
    'plot_rr_tachogram_psd_grid',
    'plot_ecg_psd_with_harmonics',
    'plot_spectrogram_rr', 'plot_duration_sweep',
]
