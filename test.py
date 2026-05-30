import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import welch
from src import pipeline as P
from src.config import FS

# load + filter
# Use a session with clearly visible 60 Hz contamination in raw ECG.
session_key = 'E4A_12pm'
t, raw = P.load_ecg(session_key, ch=1)
filt = P.filter_ecg(raw, fs=FS)

# 1) 時域 before/after（取 4 秒）
t0, t1 = 30, 34
i0, i1 = int(t0*FS), int(t1*FS)

plt.figure(figsize=(11,4))
plt.plot(t[i0:i1], raw[i0:i1], label='Raw ECG', alpha=0.8, lw=1)
plt.plot(t[i0:i1], filt[i0:i1], label='Filtered ECG', alpha=0.9, lw=1)
plt.title(f'ECG Before vs After Filter (Time Domain) - {session_key}')
plt.xlabel('Time (s)')
plt.ylabel('Amplitude')
plt.legend()
plt.grid(alpha=0.3)
plt.show()

# 2) 頻域：看 50-70 Hz（60Hz notch 效果）
f_raw, p_raw = welch(raw - raw.mean(), fs=FS, nperseg=4096)
f_flt, p_flt = welch(filt - filt.mean(), fs=FS, nperseg=4096)

m = (f_raw >= 50) & (f_raw <= 70)
raw_db = 10*np.log10(p_raw[m] + 1e-30)
flt_db = 10*np.log10(p_flt[m] + 1e-30)
f_band = f_raw[m]
idx_peak = np.argmax(raw_db)
f_peak = f_band[idx_peak]
y_peak = raw_db[idx_peak]

plt.figure(figsize=(11,4))
plt.plot(f_band, raw_db, label='Raw PSD (dB)', lw=1.8)
plt.plot(f_band, flt_db, label='Filtered PSD (dB)', lw=1.8)
plt.axvline(60, color='r', ls='--', lw=1, label='60 Hz')
plt.scatter([f_peak], [y_peak], color='k', s=28, zorder=3, label=f'Raw local peak: {f_peak:.2f} Hz')
plt.xlim(55, 65)
plt.title(f'PSD Around 60 Hz (Before vs After) - {session_key}')
plt.xlabel('Frequency (Hz)')
plt.ylabel('PSD (dB)')
plt.legend()
plt.grid(alpha=0.3, which='both')
plt.show()

idx60 = np.argmin(np.abs(f_raw - 60))
supp_db = 10*np.log10((p_raw[idx60]+1e-30)/(p_flt[idx60]+1e-30))
print(f"PSD@60Hz raw      = {p_raw[idx60]:.6e}")
print(f"PSD@60Hz filtered = {p_flt[idx60]:.6e}")
print(f"Suppression       = {supp_db:.2f} dB")