# app.py
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import io, csv

st.set_page_config(page_title="Overcurrent Relay Curves", layout="wide")

CURVE_CONSTANTS = {
    "NI": {"A": 0.14, "B": 0.02},
    "VI": {"A": 13.5, "B": 1},
    "EI": {"A": 80, "B": 2},
}

def trip_time_idmt(A, B, TMS, If, Ip):
    ratio = If / Ip
    denom = ratio**B - 1
    return np.nan if denom <= 0 else (A * TMS) / denom

def compute_curve_points_idmt(A, B, TMS, Ip, x_currents):
    ratios = x_currents / Ip
    denom = ratios**B - 1
    return np.where(denom > 0, (A * TMS) / denom, np.nan)

def compute_dt_curve(I, Ip, Td):
    return np.where(I > Ip, Td, np.nan)

st.title("Overcurrent Relay Trip Time Curves – Multi Relay Comparison")
st.caption("Relays 1 & 2: IEC 60255-151 IDMT (NI/VI/EI). Relay 3: Definite-Time (DT).")

with st.sidebar:
    st.header("Global settings")
    x_min, x_max = 0.1, 1000.0
    fault_currents = np.logspace(np.log10(x_min), np.log10(x_max), 500)

col1, col2, col3 = st.columns(3)

# --- Relay 1 (IDMT) ---
with col1:
    st.subheader("Relay 1")
    curve1 = st.selectbox("Curve type - IDMT", ["NI", "VI", "EI"], index=0, key="r1")
    TMS1 = st.slider("TMS", 0.1, 20.0, 0.1, 0.1, key="tms1")
    # UPDATED range: 0.1 – 20 A
    Ip1  = st.slider("Pickup Ip (A)", 0.1, 20.0, 1.0, 0.1, key="ip1")

# --- Relay 2 (IDMT) ---
with col2:
    st.subheader("Relay 2")
    curve2 = st.selectbox("Curve type - IDMT", ["NI", "VI", "EI"], index=1, key="r2")
    TMS2 = st.slider("TMS", 0.1, 20.0, 0.2, 0.1, key="tms2")
    # UPDATED range: 0.1 – 20 A
    Ip2  = st.slider("Pickup Ip (A)", 0.1, 20.0, 1.5, 0.1, key="ip2")

# --- Relay 3 (DT) ---
with col3:
    st.subheader("Relay 3")
    curve3 = st.selectbox("Curve type - DT", ["DT"], index=0, key="r3")  # dropdown with only DT
    # UPDATED range: 0.1 – 20 A (was 10–1000)
    Ip3  = st.slider("Pickup Ip (A)", 0.1, 20.0, 2.0, 0.1, key="ip3")
    Td3  = st.slider("Definite Time Td (s)", 0.05, 5.0, 0.35, 0.05, key="td3")

st.markdown("---")

# Common fault current + force operate
left, right = st.columns([2,1])
with left:
    IF_SHARED = st.slider("Common Fault Current If (A) for ALL relays",
                          0.1, 100.0, 2.0, 0.1)
with right:
    force_all_operate = st.checkbox("Force ALL to operate (auto choose If > max(Ip))", value=False)

IF_USED = IF_SHARED
max_ip = max(Ip1, Ip2, Ip3)
if force_all_operate:
    IF_USED = float(np.nextafter(max_ip, np.inf)) * 1.001

# Compute curves & trips
A1, B1 = CURVE_CONSTANTS[curve1]["A"], CURVE_CONSTANTS[curve1]["B"]
A2, B2 = CURVE_CONSTANTS[curve2]["A"], CURVE_CONSTANTS[curve2]["B"]

y1 = compute_curve_points_idmt(A1, B1, TMS1, Ip1, fault_currents)
y2 = compute_curve_points_idmt(A2, B2, TMS2, Ip2, fault_currents)
y3 = compute_dt_curve(fault_currents, Ip3, Td3)

tt1 = trip_time_idmt(A1, B1, TMS1, IF_USED, Ip1)
tt2 = trip_time_idmt(A2, B2, TMS2, IF_USED, Ip2)
tt3 = Td3 if IF_USED > Ip3 else np.nan

# Plot
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(fault_currents, y1, label=f"Relay 1 ({curve1})", linestyle="-")
ax.plot(fault_currents, y2, label=f"Relay 2 ({curve2})", linestyle="--")
ax.plot(fault_currents, y3, label="Relay 3 (DT)", linestyle="-.")

ax.axvline(x=IF_USED, linestyle=":", linewidth=1, label=f"If used = {IF_USED:.4g} A")

ax.set_title("Relay Trip Time Curves - IDMT and Definite Time")
ax.set_xlabel("Fault Current If (A)")
ax.set_ylabel("Trip Time (s)")
ax.grid(True, which="both", linestyle="--", linewidth=0.5)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlim([0.1, 1000])   # keeps full view of fault currents
ax.set_ylim([0.01, 100])

ax.set_xticks([0.1, 0.5, 1, 5, 10, 20, 50, 100, 500, 1000])  # ADDED 20 to reflect new Ip max
ax.get_xaxis().set_major_formatter(ScalarFormatter())
ax.set_yticks([0.01, 0.1, 0.5, 1, 5, 10, 50, 100])
ax.get_yaxis().set_major_formatter(ScalarFormatter())

ax.legend()
plt.tight_layout()
st.pyplot(fig)

# --- Trip time summary (ranked) ---
st.markdown("### Trip Time Summary (ranked, at common fault current)")

# Build rows with raw numeric tt for sorting
rows = []
def make_row(relay, curve, Ip, tms_value, td_value, tt, If):
    ratio = If / Ip
    operates = not np.isnan(tt)
    rows.append({
        "Relay": relay,
        "Curve": curve,
        "If (A)": If,
        "Ip (A)": Ip,
        "TMS": tms_value,
        "Td (s)": td_value,
        "If/Ip": ratio,
        "tt_value": (np.inf if not operates else float(tt)),  # for sorting
        "Operates?": "YES" if operates else "NO",
    })

make_row("Relay 1", curve1, Ip1, TMS1, None, tt1, IF_USED)
make_row("Relay 2", curve2, Ip2, TMS2, None, tt2, IF_USED)
make_row("Relay 3", "DT",   Ip3, None, Td3, tt3, IF_USED)

# Sort: operating relays first (by ascending trip time), then non-operating
rows_sorted = sorted(
    rows,
    key=lambda r: (r["tt_value"] == np.inf, r["tt_value"])
)

# Assign ranks to operating relays only
rank = 1
for r in rows_sorted:
    if r["tt_value"] == np.inf:
        r["Rank"] = "-"
    else:
        r["Rank"] = rank
        rank += 1

# Pretty-print table values
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
        "Trip Time (s)": "-" if r["tt_value"] == np.inf else f"{r['tt_value']:.6g}",
        "Operates?": r["Operates?"],
    })

st.table(display_rows)

# Headline: who operates first?
first_operating = next((r for r in rows_sorted if r["tt_value"] != np.inf), None)
if first_operating:
    st.success(
        f"**First to operate:** {first_operating['Relay']} ({first_operating['Curve']}) "
        f"→ {first_operating['tt_value']:.6g} s at If = {first_operating['If (A)']:.6g} A"
    )
else:
    st.warning("At the selected common fault current, no relay operates.")

# CSV download with stable fieldnames (includes Rank)
import io, csv
fieldnames = ["Rank","Relay","Curve","If (A)","Ip (A)","TMS","Td (s)","If/Ip","Trip Time (s)","Operates?"]
csv_buf = io.StringIO()
writer = csv.DictWriter(csv_buf, fieldnames=fieldnames)
writer.writeheader()
for r in display_rows:
    writer.writerow(r)

st.download_button(
    "Download Ranked Trip Time Summary (CSV)",
    data=csv_buf.getvalue(),
    file_name="trip_time_summary_ranked.csv",
    mime="text/csv"
)

