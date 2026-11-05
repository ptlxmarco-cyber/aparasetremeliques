import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# CONFIGURAÇÃO DA PÁGINA WEB
# ==========================================
st.set_page_config(page_title="CNC Millalyzer Web", layout="wide")
st.title("Simulador Dinâmico CNC (Makera Z1)")

# Aumentar fontes do Matplotlib para o ecrã do telemóvel
plt.style.use('dark_background')
plt.rcParams.update({'font.size': 12, 'lines.linewidth': 2, 'figure.dpi': 120})

# ==========================================
# BASE DE DADOS E MOTOR MATEMÁTICO
# ==========================================
MATERIAIS = {
    "Alumínio 6061-T6": (750.0, 250.0),
    "Alumínio 5000 (ex: 5083)": (700.0, 220.0),
    "POM (Delrin / Acetal)": (200.0, 50.0),
    "Aço CK55 (Médio Carbono)": (2200.0, 800.0)
}

def simular_forcas(D, flutes, helix_deg, doc, woc, feedrate, rpm, ktc, krc):
    feed_per_tooth = feedrate / (rpm * flutes)
    N_z = 100
    dz = doc / N_z
    z_array = np.linspace(0, doc, N_z)
    phi_exit = np.pi 
    phi_entry = np.pi - np.arccos(1 - (2 * woc / D))
    helix_rad = np.radians(helix_deg)
    lag_angle_z = z_array * (2 * np.tan(helix_rad) / D)
    
    theta_array = np.linspace(0, 2*np.pi, 360)
    Fx_total, Fy_total, Torque_total = np.zeros(360), np.zeros(360), np.zeros(360)
    
    for t_idx, theta in enumerate(theta_array):
        Fx_inst, Fy_inst, T_inst = 0, 0, 0
        for flute in range(int(flutes)):
            pitch_angle = flute * (2 * np.pi / flutes)
            for z_idx, z in enumerate(z_array):
                phi = (theta + pitch_angle - lag_angle_z[z_idx]) % (2 * np.pi)
                if phi_entry <= phi <= phi_exit:
                    h = feed_per_tooth * np.sin(phi)
                    dFt = ktc * h * dz
                    dFr = krc * h * dz
                    Fx_inst += -dFt * np.cos(phi) - dFr * np.sin(phi)
                    Fy_inst += dFt * np.sin(phi) - dFr * np.cos(phi)
                    T_inst += dFt * (D / 2000)
                    
        Fx_total[t_idx] = Fx_inst
        Fy_total[t_idx] = Fy_inst
        Torque_total[t_idx] = T_inst
        
    return theta_array, Fx_total, Fy_total, Torque_total, feed_per_tooth

def simular_lobulos(fn, zeta, k_stiffness, flutes, ktc_n_mm2, woc, D):
    wn = 2 * np.pi * fn
    m = k_stiffness / (wn**2)
    c = 2 * zeta * np.sqrt(k_stiffness * m)
    mu = woc / D
    
    wc = np.linspace(fn, fn * 1.5, 2000) * 2 * np.pi
    FRF = 1 / (-m * wc**2 + 1j * c * wc + k_stiffness)
    Re_G = np.real(FRF)
    Im_G = np.imag(FRF)
    
    valid = Re_G < 0
    wc = wc[valid]
    Re_G = Re_G[valid]
    Im_G = Im_G[valid]
    
    Kt_n_m2 = ktc_n_mm2 * 1e6 
    a_lim = -1 / (flutes * Kt_n_m2 * mu * Re_G)
    
    rpm_list, alim_list = [], []
    for k_lobe in range(4):
        epsilon = np.pi - 2 * np.arctan2(Im_G, Re_G)
        tau = (epsilon + 2 * np.pi * k_lobe) / wc
        rpm = 60 / (flutes * tau)
        valid_rpm = (rpm > 2000) & (rpm < 20000)
        rpm_list.append(rpm[valid_rpm])
        alim_list.append(a_lim[valid_rpm] * 1000)
        
    return rpm_list, alim_list, np.min(a_lim)*1000

# ==========================================
# INTERFACE WEB (SIDEBAR INPUTS)
# ==========================================
st.sidebar.header("Parâmetros de Corte")
material = st.sidebar.selectbox("Material", list(MATERIAIS.keys()))

col_fresa1, col_fresa2 = st.sidebar.columns(2)
D = col_fresa1.number_input("Fresa (mm)", value=4.0, step=1.0)
flutes = col_fresa2.number_input("Cortes", value=3, step=1)
hel = st.sidebar.number_input("Hélice (º)", value=45.0)

st.sidebar.markdown("---")
doc = st.sidebar.number_input("DOC (Profundidade) mm", value=1.0, step=0.1)
woc = st.sidebar.number_input("WOC (Largura) mm", value=0.6, step=0.1)
rpm = st.sidebar.number_input("RPM", value=13000, step=100)
feed = st.sidebar.number_input("Avanço (mm/min)", value=1170, step=50)

st.sidebar.markdown("---")
with st.sidebar.expander("Dinâmica da Máquina (Z1)"):
    fn = st.number_input("Frequência Natural (Hz)", value=450.0)
    k = st.number_input("Rigidez (N/m)", value=5e6, format="%e")
    zeta = st.number_input("Amortecimento", value=0.02)

# ==========================================
# CÁLCULOS
# ==========================================
ktc_mat, krc_mat = MATERIAIS[material]
ang, Fx, Fy, Tq, chip = simular_forcas(D, flutes, hel, doc, woc, feed, rpm, ktc_mat, krc_mat)
rpm_l, alim_l, min_est = simular_lobulos(fn, zeta, k, flutes, ktc_mat, woc, D)
pot = np.max(Tq) * (rpm * 2 * np.pi / 60)

# ==========================================
# INTERFACE WEB (RESULTADOS)
# ==========================================
col1, col2, col3, col4 = st.columns(4)
col1.metric("Chipload", f"{chip:.3f} mm")
col2.metric("Força Y Pico", f"{np.max(Fy):.1f} N")
col3.metric("Potência Pico", f"{pot:.1f} W", delta="Alerta! >150W" if pot > 150 else "Seguro", delta_color="inverse")
col4.metric("DOC Limite Seguro", f"< {min_est:.2f} mm")

st.markdown("---")

# ==========================================
# GRÁFICOS WEB
# ==========================================
fig, (ax_forcas, ax_lobulos) = plt.subplots(2, 1, figsize=(10, 10), facecolor='#0e1117')
ax_forcas.set_facecolor('#0e1117')
ax_lobulos.set_facecolor('#0e1117')

# Gráfico 1
ax_forcas.plot(np.degrees(ang), Fx, label='Força X', color='#4c72b0')
ax_forcas.plot(np.degrees(ang), Fy, label='Força Y', color='#55a868')
ax_forcas.plot(np.degrees(ang), Tq * 100, label='Torque (x100)', color='#c44e52', linestyle='--')
ax_forcas.set_title("Ondas de Força Instantânea", color="white")
ax_forcas.tick_params(colors='white')
ax_forcas.grid(color='gray', linestyle=':', alpha=0.3)
ax_forcas.legend()

# Gráfico 2
for i in range(len(rpm_l)):
    ax_lobulos.plot(rpm_l[i], alim_l[i], color='#4c72b0')
ax_lobulos.axhspan(0, min_est, color='#55a868', alpha=0.3, label="Estabilidade Absoluta")
ax_lobulos.plot(rpm, doc, marker='X', color='red', markersize=12, label="Corte Atual", zorder=5)

ax_lobulos.set_title("Lóbulos de Estabilidade (Previsão Chatter)", color="white")
ax_lobulos.set_xlabel("RPM", color="white")
ax_lobulos.set_ylabel("Profundidade Crítica (mm)", color="white")
ax_lobulos.tick_params(colors='white')
ax_lobulos.set_ylim(0, 8)
ax_lobulos.set_xlim(4000, 16000)
ax_lobulos.grid(color='gray', linestyle=':', alpha=0.3)
ax_lobulos.legend()

fig.tight_layout()
st.pyplot(fig)