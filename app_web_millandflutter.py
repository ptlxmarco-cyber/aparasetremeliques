import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Makera Z1 CNC Simulator", page_icon="⚙️", layout="wide")
st.title("⚙️ Simulador CNC Makera Z1")
st.markdown("Análise de Forças de Corte, Potência e Lóbulos de Estabilidade (Chatter)")

# ==========================================
# 2. BASE DE DADOS DE MATERIAIS (Kienzle)
# ==========================================
# Valores aproximados de Pressão Específica de Corte (kc1.1 em N/mm²) e coeficiente (m)
materiais = {
    "Alumínio 6061-T6": {"kc": 700, "m": 0.25},
    "Alumínio 5000": {"kc": 600, "m": 0.25},
    "POM (Delrin)": {"kc": 150, "m": 0.20},
    "Aço CK55": {"kc": 1900, "m": 0.26}
}

# ==========================================
# 3. BARRA LATERAL (INPUTS DO UTILIZADOR)
# ==========================================
st.sidebar.header("Parâmetros da Máquina e Fresa")

material_escolhido = st.sidebar.selectbox("Material da Peça", list(materiais.keys()))
rpm = st.sidebar.number_input("Rotações do Spindle (RPM)", min_value=1000, max_value=24000, value=11000, step=1000)
num_facas = st.sidebar.number_input("Número de Facas (Flutes)", min_value=1, max_value=6, value=2, step=1)
diametro = st.sidebar.number_input("Diâmetro da Fresa (mm)", min_value=1.0, max_value=20.0, value=6.0, step=0.1)

st.sidebar.header("Parâmetros de Corte")
avanco = st.sidebar.number_input("Avanço (mm/min)", min_value=10, max_value=5000, value=1000, step=50)
ap = st.sidebar.number_input("Profundidade de Corte - ap (mm)", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
ae = st.sidebar.number_input("Largura de Corte - ae (mm)", min_value=0.1, max_value=diametro, value=diametro, step=0.1)

st.sidebar.header("Dinâmica da Makera Z1")
rigidez = st.sidebar.number_input("Rigidez Estrutural (N/m)", value=5.0e6, format="%e", help="Estimativa base da Z1: 5e6 N/m")
freq_natural = st.sidebar.number_input("Frequência Natural (Hz)", min_value=100, max_value=2000, value=800, step=50)

# ==========================================
# 4. CÁLCULOS FÍSICOS (CINEMÁTICA E FORÇAS)
# ==========================================
# 4.1 Cinemática Básica
chipload = avanco / (rpm * num_facas)  # mm/dente
velocidade_corte = (np.pi * diametro * rpm) / 1000  # m/min
mrr = (ap * ae * avanco) / 1000  # cm³/min

# 4.2 Forças e Potência (Modelo simplificado de Kienzle)
kc = materiais[material_escolhido]["kc"]
m = materiais[material_escolhido]["m"]

# Força Tangencial (aproximação)
hm = chipload * np.sqrt(ae / diametro) if ae < diametro else chipload
forca_tangencial = kc * ap * (hm ** (1 - m))

# Potência do Spindle (Watts)
potencia_corte = (forca_tangencial * velocidade_corte) / 60

# ==========================================
# 5. CÁLCULO DOS LÓBULOS DE ESTABILIDADE (Altintas simplificado)
# ==========================================
def calcular_lobulos(rigidez, freq_natural, num_facas, kc):
    # Simulação simplificada de lóbulos para visualização
    # Na prática, a matriz de resposta em frequência (FRF) exige números complexos
    rpm_range = np.linspace(5000, 24000, 500)
    
    # Limite de estabilidade assintótica base (absoluta)
    # a_lim = -1 / (2 * Re(FRF) * Kt * N_facas) -> Abstração para o gráfico
    limite_absoluto = (2 * rigidez) / (kc * num_facas * 1000) # Fator de escala
    
    # Geração das "bolsas" de estabilidade (Ressonância)
    lobulos = limite_absoluto + np.abs(np.sin((freq_natural * 60) / (rpm_range * num_facas) * np.pi)) * (limite_absoluto * 3)
    
    return rpm_range, lobulos, limite_absoluto

rpm_plot, limite_ap, limite_abs = calcular_lobulos(rigidez, freq_natural, num_facas, kc)

# ==========================================
# 6. PAINEL DE RESULTADOS E AVISOS (DASHBOARD)
# ==========================================
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

col1.metric("Chipload (Espessura da Apara)", f"{chipload:.3f} mm/d", help="Valores ideais para alumínio: 0.01 a 0.05 mm/d")
col2.metric("Potência Exigida", f"{potencia_corte:.1f} W")
col3.metric("Velocidade de Corte (Vc)", f"{velocidade_corte:.0f} m/min")
col4.metric("Taxa de Remoção (MRR)", f"{mrr:.1f} cm³/min")

# Verificação do limite do Spindle da Makera Z1 (~150W)
if potencia_corte > 150:
    st.error(f"⚠️ Atenção! A potência calculada ({potencia_corte:.1f} W) ultrapassa o limite seguro do Spindle da Makera Z1 (150W). Risco de estagnar o motor.")
else:
    st.success("✅ Potência dentro dos limites da Makera Z1.")

# ==========================================
# 7. GRÁFICO DE ESTABILIDADE (MATPLOTLIB)
# ==========================================
st.subheader("Gráfico de Lóbulos de Estabilidade (Chatter)")

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(rpm_plot, limite_ap, color='blue', linewidth=2, label='Limite de Chatter')
ax.axhline(y=limite_abs, color='red', linestyle='--', label='Estabilidade Absoluta (Sem Chatter)')

# Ponto atual do utilizador
ax.plot(rpm, ap, marker='o', markersize=10, markeredgecolor='black', markerfacecolor='red', label='O Teu Corte')

# Preencher zonas de estabilidade
ax.fill_between(rpm_plot, 0, limite_ap, color='green', alpha=0.2)
ax.fill_between(rpm_plot, limite_ap, np.max(limite_ap)+1, color='red', alpha=0.1)

ax.set_xlabel('Rotações (RPM)')
ax.set_ylabel('Profundidade de Corte Limite - ap (mm)')
ax.set_title(f'Estabilidade para {material_escolhido}')
ax.set_xlim(5000, 24000)
ax.set_ylim(0, np.max(limite_ap) if np.max(limite_ap) < 10 else 10)
ax.legend()
ax.grid(True, linestyle=':', alpha=0.7)

st.pyplot(fig)

# ==========================================
# 8. NOVO: OTIMIZADOR DE ACABAMENTO SUPERFICIAL
# ==========================================
st.markdown("---")
st.subheader("🎯 Otimizador de Acabamento Superficial")
st.write("Calcula o avanço exato em mm/min para um passe final de acabamento espelhado, evitando empastar a fresa.")

col_opt1, col_opt2 = st.columns([1, 2])

with col_opt1:
    chipload_alvo = st.slider(
        "Chipload Desejado (mm/dente)", 
        min_value=0.005, 
        max_value=0.050, 
        value=0.015, 
        step=0.001,
        format="%.3f",
        help="Para acabamento espelhado no Alumínio 6061, recomenda-se entre 0.010 e 0.020 mm/dente."
    )

avanco_ideal = chipload_alvo * rpm * num_facas

with col_opt2:
    st.info(f"Para conseguires um **Chipload de {chipload_alvo:.3f} mm/dente** com a tua fresa de **{num_facas} cortes** a **{rpm} RPM**:")
    st.success(f"🔥 **Avanço Recomendado: {avanco_ideal:.0f} mm/min**")
    st.write(f"*Dica de CAM:* No teu passe de acabamento, usa estas RPM e este Avanço, mas corta apenas os últimos 0.1 a 0.2 mm da parede para não forçar a ferramenta.")
