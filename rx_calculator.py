
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="RX Calculator — Cool Roof", layout="wide")

# --- HEADER / BRANDING ---
c1, c2, c3 = st.columns([1, 6, 1])
with c1:
    st.image("soltherm.png", caption="SOLTHERM", use_container_width=True)
with c2:
    st.title("RX Calculator — Kalkulator Chłodnego Dachu")
    st.caption("Pełna logika: szczegóły konfiguracji, 20-letnie oszczędności, opcjonalny czas zwrotu. \
Usunięto krzywą CO₂ na wykresie kumulacyjnym. Skalowanie (diapazon) dla wszystkich wykresów.")
with c3:
    st.image("bolix.png", caption="BOLIX", use_container_width=True)

# ---------- PARAMS (powłoka / stałe) ----------
TSR = 0.88            # Total Solar Reflectance
EMISSIVITY = 0.904
SRI = 111
st.caption(f"Parametry powłoki: TSR={TSR*100:.0f}%, emisyjność={EMISSIVITY:.3f}, SRI={SRI}")

# ---------- SIDEBAR: SZCZEGÓŁY KONFIGURACJI ----------
st.sidebar.header("Szczegóły konfiguracji")
default_price = 0.85   # PLN/kWh
default_ef = 0.77      # kg CO2/kWh

area_m2 = st.sidebar.number_input("Powierzchnia dachu (m²)", min_value=10.0, value=1000.0, step=10.0)
roof_type = st.sidebar.selectbox("Rodzaj dachu", ["Blacha (metal)", "Beton", "Papa/bitum"], index=0)

st.sidebar.subheader("Izolacja")
roof_ins_choice = st.sidebar.selectbox("Izolacja dachu",
                                       ["Brak", "XPS-50", "XPS-80", "XPS-100", "XPS-150",
                                        "PU-50", "PU-80", "PU-100"], index=0)
wall_ins_choice = st.sidebar.selectbox("Izolacja ścian",
                                       ["Brak", "XPS-50", "PU-80"], index=0)

ac_band = st.sidebar.selectbox("Efektywność klimatyzacji (przedział)",
                               ["Stary", "Standard", "Wysoka sprawność"], index=1)
custom_eer_on = st.sidebar.checkbox("Podaj własny EER", value=False)
if custom_eer_on:
    eer = st.sidebar.number_input("EER (Energy Efficiency Ratio)", min_value=5.0, value=11.0, step=0.5)
else:
    eer = 9.0 if ac_band == "Stary" else (11.0 if ac_band == "Standard" else 13.0)

price_pln = st.sidebar.number_input("Cena energii (zł/kWh)", min_value=0.0, value=default_price, step=0.05)
ef_kg_per_kwh = st.sidebar.number_input("Współczynnik emisji CO₂ (kg/kWh)", min_value=0.0, value=default_ef, step=0.01)

st.sidebar.markdown("---")
st.sidebar.subheader("Ustawienia wykresów (diapazon)")
auto_scale = st.sidebar.checkbox("Auto-dopasowanie zakresów", value=True)
cum_max_override = st.sidebar.number_input("Maks. oś Y (kumulacja 20 lat)", min_value=0.0, value=150000.0, step=5000.0)
trees_max_override = st.sidebar.number_input("Maks. drzewa (szt./rok)", min_value=0.0, value=300.0, step=10.0)
km_max_override = st.sidebar.number_input("Maks. km (km/rok)", min_value=0.0, value=40000.0, step=1000.0)
house_max_override = st.sidebar.number_input("Maks. gospodarstwa (szt./rok)", min_value=0.0, value=200.0, step=10.0)
bulb_max_override = st.sidebar.number_input("Maks. żarówki (szt./rok)", min_value=0.0, value=50000.0, step=5000.0)

# ---------- MODEL ----------
roof_multipliers = {"Blacha (metal)": 1.00, "Beton": 0.95, "Papa/bitum": 1.05}
roof_mult = roof_multipliers[roof_type]

# Thermal conductivities
XPS_LAMBDA = 0.034  # W/mK
PU_LAMBDA = 0.025   # W/mK

def thickness_from_choice(choice: str):
    if choice.startswith("XPS-"):
        mm = float(choice.split("-")[1])
        return mm / 1000.0, XPS_LAMBDA
    elif choice.startswith("PU-"):
        mm = float(choice.split("-")[1])
        return mm / 1000.0, PU_LAMBDA
    else:
        return 0.0, None

t_roof, lambda_roof = thickness_from_choice(roof_ins_choice)
t_wall, lambda_wall = thickness_from_choice(wall_ins_choice)

R_roof_xps = (t_roof / lambda_roof) if t_roof > 0 else 0.0
R_wall_xps = (t_wall / lambda_wall) if t_wall > 0 else 0.0

R_base_roof = {"Blacha (metal)": 0.17, "Beton": 0.50, "Papa/bitum": 0.25}[roof_type]
R_si, R_se = 0.10, 0.04

R_total_roof = R_si + R_base_roof + R_roof_xps + R_se
R_base_wall = 0.45
R_total_wall = R_si + R_base_wall + R_wall_xps + R_se

# Izolacja wpływa na zysk chłodu (im większa, tym efekt mniejszy)
beta = 0.12
insul_factor = 1.0 / (1.0 + beta * (R_roof_xps))
wall_factor = 0.98 if R_wall_xps > 0 else 1.00

FT2_PER_M2 = 10.7639
BTU_TO_J = 1055.06

area_ft2 = area_m2 * FT2_PER_M2
reduction_btu_per_ft2_base = 5833.0

reduction_btu_per_ft2 = reduction_btu_per_ft2_base * roof_mult * insul_factor * wall_factor
total_reduction_btu = area_ft2 * reduction_btu_per_ft2

kwh_saved = total_reduction_btu / (eer * 1000.0)
pln_saved = kwh_saved * price_pln
kg_co2_saved = kwh_saved * ef_kg_per_kwh
t_co2_saved = kg_co2_saved / 1000.0
gj_saved = (total_reduction_btu * BTU_TO_J) / 1e9

# Ekwiwalenty
KG_PER_TREE_PER_YEAR = 22.0
KG_PER_CAR_KM = 0.2
trees_eq = kg_co2_saved / KG_PER_TREE_PER_YEAR if KG_PER_TREE_PER_YEAR > 0 else 0
km_eq = kg_co2_saved / KG_PER_CAR_KM if KG_PER_CAR_KM > 0 else 0
households_eq = kwh_saved / 2000.0
bulbs_eq = kwh_saved / 10.0

# Serie 20-letnie
years = np.arange(1, 21)
kwh_yearly = np.full_like(years, kwh_saved, dtype=float)
pln_yearly = np.full_like(years, pln_saved, dtype=float)
kwh_cum = np.cumsum(kwh_yearly)
pln_cum = np.cumsum(pln_yearly)

# ---------- TABLES UNDER HEADER ----------
st.markdown("### Szczegóły konfiguracji")
col1, col2 = st.columns(2)

with col1:
    df_building = pd.DataFrame({
        "Parametr": [
            "Rodzaj dachu",
            "Izolacja dachu",
            "Izolacja ścian",
            "U-value dachu (W/m²K)",
            "U-value ścian (W/m²K)",
            "EER (efektywność)"
        ],
        "Wartość": [
            roof_type,
            roof_ins_choice,
            wall_ins_choice,
            f"{1/R_total_roof:.2f}",
            f"{1/R_total_wall:.2f}",
            f"{eer:.1f}"
        ]
    })
    st.table(df_building)

with col2:
    df_energy = pd.DataFrame({
        "Wskaźnik": [
            "Redukcja chłodu (Btu/ft²/rok)",
            "Redukcja chłodu (GJ/rok)",
            "Oszczędność energii (kWh/rok)",
            "Oszczędność kosztów (zł/rok)",
            "Redukcja CO₂ (kg/rok)",
            "Redukcja CO₂ (t/rok)"
        ],
        "Wartość": [
            f"{reduction_btu_per_ft2:.0f}",
            f"{gj_saved:.2f}",
            f"{kwh_saved:.0f}",
            f"{pln_saved:.0f}",
            f"{kg_co2_saved:.0f}",
            f"{t_co2_saved:.2f}"
        ]
    })
    st.table(df_energy)

# ---------- KPI BOXES ----------
m1, m2, m3, m4 = st.columns(4)
m1.metric("Roczna oszczędność energii", f"{kwh_saved:.0f} kWh")
m2.metric("Roczna oszczędność kosztów", f"{pln_saved:.0f} zł")
m3.metric("Roczna redukcja CO₂", f"{kg_co2_saved:.0f} kg")
m4.metric("Redukcja chłodu", f"{gj_saved:.2f} GJ/rok")

# ---------- Nice ceiling helper ----------
def nice_ceiling(x):
    if x <= 0:
        return 0
    import math
    exp = int(math.floor(math.log10(x)))
    base = x / (10 ** exp)
    if base <= 1:
        nice = 1
    elif base <= 2:
        nice = 2
    elif base <= 5:
        nice = 5
    else:
        nice = 10
    return nice * (10 ** exp)

# ---------- WYKRES 20-LETNIEJ KUMULACJI (BEZ CO2) ----------
st.markdown("### 20-letnie oszczędności — kumulacja (energia i koszty)")
df_cum = pd.DataFrame({
    "Rok": years,
    "Energia (kWh)": kwh_cum,
    "Koszty (zł)": pln_cum,
})
fig1 = px.line(df_cum, x="Rok", y=["Energia (kWh)", "Koszty (zł)"],
               markers=True, title="Kumulatywne oszczędności w czasie")
max_cum = float(np.nanmax([kwh_cum.max(), pln_cum.max()]))
target_max = nice_ceiling(max_cum * 1.25)
if not auto_scale:
    target_max = cum_max_override
fig1.update_yaxes(range=[0, target_max])
st.plotly_chart(fig1, use_container_width=True)

# ---------- ROCZNE EKWIWALENTY (4 KAFLE BAR) ----------
st.markdown("### Roczne ekwiwalenty (powiększona skala)")
eq1, eq2 = st.columns(2)
with eq1:
    df_trees = pd.DataFrame({"Ekwiwalent": ["Posadzone drzewa (szt./rok)"], "Wartość": [trees_eq]})
    bar1 = px.bar(df_trees, x="Ekwiwalent", y="Wartość", text="Wartość", title="🌳 Posadzone drzewa")
    ymax = nice_ceiling(max(trees_eq * 1.5, trees_max_override if not auto_scale else trees_eq * 1.5))
    bar1.update_yaxes(range=[0, ymax])
    bar1.update_traces(texttemplate="%{text:.0f}", textposition="outside")
    st.plotly_chart(bar1, use_container_width=True)

with eq2:
    df_km = pd.DataFrame({"Ekwiwalent": ["Uniknięte km samochodem (km/rok)"], "Wartość": [km_eq]})
    bar2 = px.bar(df_km, x="Ekwiwalent", y="Wartość", text="Wartość", title="🚗 Uniknięte kilometry")
    ymax2 = nice_ceiling(max(km_eq * 1.5, km_max_override if not auto_scale else km_eq * 1.5))
    bar2.update_yaxes(range=[0, ymax2])
    bar2.update_traces(texttemplate="%{text:.0f}", textposition="outside")
    st.plotly_chart(bar2, use_container_width=True)

eq3, eq4 = st.columns(2)
with eq3:
    df_house = pd.DataFrame({"Ekwiwalent": ["Gospodarstwa domowe (szt./rok)"], "Wartość": [households_eq]})
    bar3 = px.bar(df_house, x="Ekwiwalent", y="Wartość", text="Wartość", title="🏠 Domowe zużycie energii (gosp.)")
    ymax3 = nice_ceiling(max(households_eq * 1.5, house_max_override if not auto_scale else households_eq * 1.5))
    bar3.update_yaxes(range=[0, ymax3])
    bar3.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    st.plotly_chart(bar3, use_container_width=True)

with eq4:
    df_bulb = pd.DataFrame({"Ekwiwalent": ["Żarówki LED świecące rok (szt./rok)"], "Wartość": [bulbs_eq]})
    bar4 = px.bar(df_bulb, x="Ekwiwalent", y="Wartość", text="Wartość", title="💡 Żarówki LED przez rok")
    ymax4 = nice_ceiling(max(bulbs_eq * 1.5, bulb_max_override if not auto_scale else bulbs_eq * 1.5))
    bar4.update_yaxes(range=[0, ymax4])
    bar4.update_traces(texttemplate="%{text:.0f}", textposition="outside")
    st.plotly_chart(bar4, use_container_width=True)

# ---------- PAYBACK (opcjonalny) ----------
st.markdown("### Opcjonalnie: czas zwrotu (payback)")
cost_on = st.checkbox("Włącz obliczanie czasu zwrotu (podaj koszt powłoki)")
if cost_on:
    unit_cost = st.number_input("Koszt powłoki (zł/m²)", min_value=0.0, value=50.0, step=5.0)
    capex = unit_cost * area_m2
    if pln_saved > 0:
        payback_years = capex / pln_saved
        st.info(f"Szacowany prosty czas zwrotu: {payback_years:.1f} lat (CAPEX {capex:.0f} zł / {pln_saved:.0f} zł/rok)")
    else:
        st.warning("Brak oszczędności kosztowych — nie można policzyć zwrotu.")

# ---------- CSV DOWNLOAD ----------
st.markdown("---")
st.subheader("Pobierz wyniki")
summary = pd.DataFrame([{
    "Powierzchnia_m2": area_m2,
    "Rodzaj_dachu": roof_type,
    "Izolacja_dachu": roof_ins_choice,
    "Izolacja_scian": wall_ins_choice,
    "EER": eer,
    "Cena_energii_PLN_kWh": price_pln,
    "EF_kgCO2_kWh": ef_kg_per_kwh,
    "kWh_rok": kwh_saved,
    "PLN_rok": pln_saved,
    "kWh_20lat": kwh_cum[-1],
    "PLN_20lat": pln_cum[-1],
    "tCO2_rok": t_co2_saved,
}])
st.download_button("Pobierz podsumowanie (CSV)", summary.to_csv(index=False).encode("utf-8"),
                   "rx_calculator_podsumowanie.csv", "text/csv")
