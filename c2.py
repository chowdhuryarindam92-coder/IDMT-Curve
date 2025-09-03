# app.py
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

st.set_page_config(page_title="IDMT Relay Curves (IEC 60255-151)", layout="wide")

# IEC 60255-151 curve constants
CURVE_CONSTANTS = {
    "NI": {"A": 0.14, "B": 0.02},
    "VI": {"A": 13.5, "B": 1},
    "EI": {"A": 80, "B": 2},
}

def trip_time(A, B, TMS, If, Ip):
    """Compute trip time; return np.nan if invalid (ratio <= 1)."""
    ratio = If / Ip
    denom = ratio**B - 1
    return np.nan if denom <= 0 else (A * TMS) / denom

def compute_curve_points(A, B, TMS, Ip, x_currents):
    ratios = x_currents / Ip
    denom = ratios**B - 1
    y = np.where(denom > 0, (A * TMS) / denom, np.nan)
    return y

st.title("IDMT Relay Trip Time Curves – Dual Curve Comparison")
st.caption("IEC 60255-151 (NI / VI / EI). Move the sliders to see how setpoints shift the curves.")

with st.sidebar:
    st.header("Global settings")
    x_min, x_max = 0.1, 1000.0
    fault_currents = np.logspace(np.log10(x_min), np.log10(x_max), 500)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Set 1")
    curve1 = st.selectbox("Curve 1", ["NI", "VI", "EI"], index=0, key="c1")
    TMS1 = st.slider("TMS1", 0.1, 20.0, 0.1, 0.1)
    Ip1  = st.slider("Pickup Ip1 (A)", 0.1, 10.0, 1.0, 0.1)
    If1  = st.slider("Fault If1 (A)", 0.1, 10.0, 2.0, 0.1)

with col2:
    st.subheader("Set 2")
    curve2 = st.selectbox("Curve 2", ["NI", "VI", "EI"], index=1, key="c2")
    TMS2 = st.slider("TMS2", 0.1, 20.0, 0.2, 0.1)
    Ip2  = st.slider("Pickup Ip2 (A)", 0.1, 10.0, 1.5, 0.1)
    If2  = st.slider("Fault If2 (A)", 0.1, 10.0, 3.0, 0.1)

# Compute curves
A1, B1 = CURVE_CONSTANTS[curve1]["A"], CURVE_CONSTANTS[curve1]["B"]
A2, B2 = CURVE_CONSTANTS[curve2]["A"], CURVE_CONSTANTS[curve2]["B"]

y1 = compute_curve_points(A1, B1, TMS1, Ip1, fault_currents)
y2 = compute_curve_points(A2, B2, TMS2, Ip2, fault_currents)

# Compute single-point trip times
tt1 = trip_time(A1, B1, TMS1, If1, Ip1)
tt2 = trip_time(A2, B2, TMS2, If2, Ip2)

# Plot
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(fault_currents, y1, label=f"{curve1} Curve (Set 1)", linestyle="-")
ax.plot(fault_currents, y2, label=f"{curve2} Curve (Set 2)", linestyle="--")

# Vertical markers for chosen fault currents
ax.axvline(x=If1, linestyle="--", linewidth=1, label=f"If1 = {If1} A")
ax.axvline(x=If2, linestyle="--", linewidth=1, label=f"If2 = {If2} A")

ax.set_title("IDMT Relay Trip Time Curves - Dual Curve Comparison")
ax.set_xlabel("Fault Current If (A)")
ax.set_ylabel("Trip Time (s)")
ax.grid(True, which="both", linestyle="--", linewidth=0.5)
ax.set_xscale("log")
ax.set_yscale("log")

# Readable ticks
ax.set_xlim([0.1, 1000])
ax.set_ylim([0.01, 100])
ax.set_xticks([0.1, 0.5, 1, 5, 10, 50, 100, 500, 1000])
ax.get_xaxis().set_major_formatter(ScalarFormatter())
ax.set_yticks([0.01, 0.1, 0.5, 1, 5, 10, 50, 100])
ax.get_yaxis().set_major_formatter(ScalarFormatter())

ax.legend()
plt.tight_layout()
st.pyplot(fig)

# Trip time readout
st.markdown("### Trip Time @ Selected Fault Current(s)")
c1, c2 = st.columns(2)
with c1:
    if np.isnan(tt1):
        st.error(
            f"Set 1 ({curve1}): If1/Ip1 ≤ 1 → inverse-time not defined. Increase If1 or reduce Ip1."
        )
    else:
        st.success(f"Set 1 ({curve1}): **Trip Time = {tt1:.4f} s**  (If1={If1} A, Ip1={Ip1} A, TMS1={TMS1})")
with c2:
    if np.isnan(tt2):
        st.error(
            f"Set 2 ({curve2}): If2/Ip2 ≤ 1 → inverse-time not defined. Increase If2 or reduce Ip2."
        )
    else:
        st.success(f"Set 2 ({curve2}): **Trip Time = {tt2:.4f} s**  (If2={If2} A, Ip2={Ip2} A, TMS2={TMS2})")

st.caption("Note: Inverse-time formula T = A·TMS / ((If/Ip)^B − 1) is valid only when If/Ip > 1.")

# --- Developer Credit ---
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<center><small>Developed by <b>Arindam Chowdhury</b></small></center>", unsafe_allow_html=True)

