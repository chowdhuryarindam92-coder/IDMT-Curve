# app.py
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import io, csv
import pandas as pd  # for nice, index-free table display

st.set_page_config(
    page_title="Relay Coordination Time-Current Characteristic Curve – Multi-Relay Comparison",
    layout="wide"
)

# --- Curve constants (IEC 60255-151) ---
CURVE_CONSTANTS = {
    "NI": {"A": 0.14, "B": 0.02},
    "VI": {"A": 13.5, "B": 1},
    "EI": {"A": 80, "B": 2},
}

# --- Helpers ---
def trip_time_idmt(A, B, TMS, If, Ip):
    ratio = If / Ip
    denom = ratio**B - 1
    return np.nan if denom <= 0 else (A * TMS) / denom

def compute_curve_points_idmt(A, B, TMS, Ip, x_currents):
    ratios = x_currents / Ip
    denom = ratios**B - 1
    return np.where(denom > 0, (A * TMS) / denom, np.nan)

def compute_dt_curve(I, Ip, Td):
    # DT: constant Td for I > Ip, otherwise no operation (nan)
    return np.where(I > Ip, Td, np.nan)

# --- Page content ---
st.title("Relay Coordination Time-Current Characteristic Curve – Multi-Relay Comparison")
st.caption("Relays 1 & 2: IEC 60255-151 IDMT (NI/VI/EI). Relay 3: Definite-Time (DT).")

with st.sidebar:
    st.header("Global settings")
    x_min, x_max = 0.1, 1000.0
    fault_currents = np.logspace(np.log10(x_min), np.log10(x_max), 500)

col1, col2, col3 = st.columns(3)

# --- Relay 1 (IDMT) ---
with col1:
    st.subheader("Relay 1")
    curve1 = st.selectbox("Curve type", ["NI", "VI", "EI"], index=0, key="r1")
    TMS1 = st.slider("TMS", 0.1, 20.0, 0.1, 0.1, key="tms1")
    # Pickup range fixed to 0.1–20 A
    Ip1  = st.slider("Pickup Ip (A)", 0.1, 20.0, 1.0, 0.1, key="ip1")

# --- Relay 2 (IDMT) ---
with col2:
    st.subheader("Relay 2")
    curve2 = st.selectbox("Curve type", ["NI", "VI", "EI"], index=1, key="r2")
    TMS2 = st.slider("TMS", 0.1, 20.0, 0.2, 0.1, key="tms2")
    Ip2  = st.slider("Pickup Ip (A)", 0.1, 20.0, 1.5, 0.1, key="ip2")

# --- Relay 3 (DT) ---
with col3:
    st.subheader("Relay 3")
    curve3 = st.selectbox("Curve type", ["DT"], index=0, key="r3")  # dropdown with only DT
    Ip3  = st.slider("Pickup Ip (A)", 0.1, 20.0, 2.0, 0.1, key="ip3")
    Td3  = st.slider("Definite Time Td (s)", 0.05, 5.0, 0.35, 0.05, key="td3")

st.markdown("---")

# --- Common current + force-all-operate control ---
left, right = st.columns([2,1])
with left:
    # Rename to "Current (A)" per request; still the shared If for all relays
    IF_SHARED = st.slider("Common Current (A) for ALL relays", 0.1, 1000.0, 2.0, 0.1)
with right:
    force_all_operate = st.checkbox("Force ALL to operate (auto choose If > max(Ip))", value=False)

# If forcing operation, use a current just above the largest pickup
IF = IF_SHARED  # display & computation label now simply "If"
max_ip = max(Ip1, Ip2, Ip3)
if force_all_operate:
    IF = float(np.nextafter(max_ip, np.inf)) * 1.001

# --- Compute curves and time(s) ---
A1, B1 = CURVE_CONSTANTS[curve1]["A"], CURVE_CONSTANTS[curve1]["B"]
A2, B2 = CURVE_CONSTANTS[curve2]["A"], CURVE_CONSTANTS[curve2]["B"]

y1 = compute_curve_points_idmt(A1, B1, TMS1, Ip1, fault_currents)
y2 = compute_curve_points_idmt(A2, B2, TMS2, Ip2, fault_currents)
y3 = compute_dt_curve(fault_currents, Ip3, Td3)

tt1 = trip_time_idmt(A1, B1, TMS1, IF, Ip1)
tt2 = trip_time_idmt(A2, B2, TMS2, IF, Ip2)
tt3 = Td3 if IF > Ip3 else np.nan

# --- Plot (grid ETAP green, relays colored individually) ---
fig, ax = plt.subplots(figsize=(10, 6))

# Different colors for each relay
ax.plot(fault_currents, y1, label=f"Relay 1 ({curve1})", linestyle="-",  color="blue")
ax.plot(fault_currents, y2, label=f"Relay 2 ({curve2})", linestyle="--", color="red")
ax.plot(fault_currents, y3, label="Relay 3 (DT)",         linestyle="-.", color="black")

# Common current marker (If) also ETAP green but a bit thicker for visibility
ax.axvline(x=IF, linestyle=":", linewidth=1.2, color="#00A651", label=f"If = {IF:.4g} A")

ax.set_title("Time-Current Characteristic Curves – Multi-Relay Comparison")
ax.set_xlabel("Current (A)")
ax.set_ylabel("Time(s)")

# Thinner ETAP green grid lines
ax.grid(True, which="both", linestyle="--", linewidth=0.4, color="#00A651")

ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlim([0.1, 1000])
ax.set_ylim([0.01, 100])

ax.set_xticks([0.1, 0.5, 1, 5, 10, 20, 50, 100, 500, 1000])
ax.get_xaxis().set_major_formatter(ScalarFormatter())
ax.set_yticks([0.01, 0.1, 0.5, 1, 5, 10, 50, 100])
ax.get_yaxis().set_major_formatter(ScalarFormatter())

ax.legend()
plt.tight_layout()
st.pyplot(fig)


# --- Trip time summary ranked (fastest -> slowest), no index column before Rank ---
st.markdown("### Trip time summary (ranked)")

# Build rows with raw numeric time for sorting
rows = []
def make_row(relay, curve, Ip, tms_value, td_value, tt, If):
    ratio = If / Ip
    operates = not np.isnan(tt)
    rows.append({
        "Relay": relay,
        "Curve": curve,
        "If (A)": If,             # numeric for formatting later
        "Ip (A)": Ip,
        "TMS": tms_value,
        "Td (s)": td_value,
        "If/Ip": ratio,
        "time_value": (np.inf if not operates else float(tt)),  # for sorting
        "Operates?": "Yes" if operates else "No",
    })

make_row("Relay 1", curve1, Ip1, TMS1, None, tt1, IF)
make_row("Relay 2", curve2, Ip2, TMS2, None, tt2, IF)
make_row("Relay 3", "DT",   Ip3, None, Td3, tt3, IF)

# Sort by time_value (ascending), operating first
rows_sorted = sorted(rows, key=lambda r: (r["time_value"] == np.inf, r["time_value"]))

# Add Rank for operating relays only
rank = 1
for r in rows_sorted:
    if r["time_value"] == np.inf:
        r["Rank"] = "-"
    else:
        r["Rank"] = rank
        rank += 1

# Format for display/CSV with requested column names
display_rows = []
for r in rows_sorted:
    display_rows.append({
        "Rank": r["Rank"],
        "Relay": r["Relay"],
        "Curve": r["Curve"],
        "If (A)": f"{r['If (A)']:.6g}",
        "Ip (A)": f"{r['Ip (A)']:.6g}",
        "TMS": "" if r["TMS"] is None else f"{r['TMS']:.6g}",
        "Td (s)": "" if r["Td (s)"] is None else f"{r['Td (s)']:.6g}",
        "If/Ip": f"{r['If/Ip']:.6g}",
        "Time(s)": "-" if r["time_value"] == np.inf else f"{r['time_value']:.6g}",
        "Operates?": r["Operates?"],
    })

# Show as a dataframe with no extra index (“column before Rank not required”)
df = pd.DataFrame(display_rows)
st.dataframe(df, use_container_width=True, hide_index=True)

# CSV download with stable fieldnames
fieldnames = ["Rank","Relay","Curve","If (A)","Ip (A)","TMS","Td (s)","If/Ip","Time(s)","Operates?"]
csv_buf = io.StringIO()
writer = csv.DictWriter(csv_buf, fieldnames=fieldnames)
writer.writeheader()
for r in display_rows:
    writer.writerow(r)

st.download_button(
    "Download Trip Time Summary (CSV)",
    data=csv_buf.getvalue(),
    file_name="trip_time_summary_ranked.csv",
    mime="text/csv"
)

# --- Guidance on operation condition ---
if not force_all_operate:
    notes = []
    if IF <= Ip1: notes.append("Relay 1")
    if IF <= Ip2: notes.append("Relay 2")
    if IF <= Ip3: notes.append("Relay 3")
    if notes:
        st.warning(
            "At the selected current, **no operation** for: " + ", ".join(notes) +
            ". Increase the common current or tick ‘Force ALL to operate’."
        )

st.caption("IDMT: T = A·TMS / ((If/Ip)^B − 1), valid only for If/Ip > 1. DT: trips at constant Td for If > Ip.")
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<center><small>Developed by <b>Arindam Chowdhury</b>, Electrical Engineer</small></center>",
    unsafe_allow_html=True,
)

