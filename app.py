"""
F1 Style Decoder — Streamlit App
================================
Interface interactive pour analyser les styles de pilotage en F1.

Pour lancer :
    pip install streamlit fastf1 plotly pandas numpy
    streamlit run app.py

L'app s'ouvre automatiquement dans ton navigateur (http://localhost:8501).
"""
import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import fastf1
from fastf1.utils import delta_time

# ============== CONFIG ==============
st.set_page_config(
    page_title="F1 Style Decoder",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="auto",  # repliée sur mobile, dépliée sur desktop
)

os.makedirs("cache_f1", exist_ok=True)
fastf1.Cache.enable_cache("cache_f1")

# --- Couleurs équipes (mises à jour 2026) ---
TEAM_COLORS = {
    "Red Bull Racing": "#1E40AF", "Red Bull": "#1E40AF",
    "McLaren": "#FF8000",
    "Ferrari": "#DC0000",
    "Mercedes": "#00A19B",
    "Aston Martin": "#229971",
    "Alpine": "#E91E63",
    "Williams": "#1868DB",
    "Audi": "#52E252", "Kick Sauber": "#52E252", "Sauber": "#52E252",
    "Haas F1 Team": "#9C9FA2", "Haas": "#9C9FA2",
    "Racing Bulls": "#6692FF", "RB": "#6692FF",
    "Cadillac": "#C9B037",
    "AlphaTauri": "#6692FF",
}

# --- Couleurs des compounds pneus (officiel F1) ---
COMPOUND_COLORS = {
    "SOFT": "#FF3333", "S": "#FF3333",
    "MEDIUM": "#FFCC33", "M": "#FFCC33",
    "HARD": "#F0F0F0", "H": "#F0F0F0",
    "INTERMEDIATE": "#33B53C", "INTER": "#33B53C", "I": "#33B53C",
    "WET": "#4D7BC2", "W": "#4D7BC2",
    "UNKNOWN": "#888888", "TEST_UNKNOWN": "#888888",
}
def compound_color(c):
    return COMPOUND_COLORS.get(str(c).upper(), "#888888")

# --- Briefing circuit : zones notables par circuit ---
CIRCUITS_INFO = {
    "Bahrain Grand Prix": {
        "facts": "Premier circuit nocturne du calendrier. Asphalte abrasif, gros stress pneus. 3 zones DRS, beaucoup d'overtaking spots.",
        "zones": [
            ("T1 entrée", "T1", "0-400 m", "Gros freinage de 320 à 80 km/h depuis la ligne droite des stands. Premier overtaking spot, beaucoup de chaos au départ."),
            ("T4 chicane", "T4", "800-1100 m", "Freinage en bout de la deuxième plus longue ligne droite. Deuxième zone d'overtaking majeur."),
            ("Esses T9-T10", "T9-T10", "2900-3300 m", "Enchaînement rapide gauche-droite, technique. Différencie les caméléons."),
            ("T13", "T13", "4400-4700 m", "Long virage à droite, traction critique sur la sortie pour les stats S3."),
        ],
    },
    "Australian Grand Prix": {
        "facts": "Circuit semi-permanent dans Albert Park. Refait en 2022 (plus rapide). Mur de béton omniprésent — peu de marge d'erreur.",
        "zones": [
            ("T1-T2 chicane", "T1-T2", "0-500 m", "Chicane rapide d'ouverture, gros engagement. Premier indicateur de confiance."),
            ("T3 droite", "T3", "600-900 m", "Long droite, traction et trail-braking en entrée."),
            ("T9-T10 esses", "T9-T10", "2400-2900 m", "Section flowing très rapide, lit le rythme du pilote."),
            ("T11-T12", "T11-T12", "3500-3900 m", "Chicane rapide, mur proche, late braking redoutable."),
        ],
    },
    "Chinese Grand Prix": {
        "facts": "Tracé en forme de '上' (caractère 'au-dessus'). Le virage 1-2-3 en spirale est un casse-tête unique : rayon décroissant. Longue ligne droite de retour avec DRS.",
        "zones": [
            ("Spirale T1-T2-T3", "T1-T3", "200-1100 m", "Triple droite à rayon décroissant — différencie les pilotes qui anticipent vs ceux qui réagissent. Iconique de Shanghai."),
            ("T6 hairpin", "T6", "1900-2200 m", "Épingle serrée, gros freinage, traction critique pour la suite."),
            ("T11-T12-T13", "T11-T13", "3800-4400 m", "Section technique avant la longue ligne droite. La sortie de T13 conditionne la Vmax."),
            ("T14 freinage", "T14", "5300-5700 m", "Gros freinage de 330 à 60 km/h en bout de back straight. Spot d'overtaking principal."),
        ],
    },
    "Japanese Grand Prix": {
        "facts": "Suzuka, figure-8, légende absolue. Circuit de pilotes par excellence — peu d'overtaking, tout se joue sur l'engagement et la précision.",
        "zones": [
            ("S1 Esses (T2-T7)", "T2-T7", "400-1300 m", "Enchaînement de S à haute vitesse. Le rythme et la fluidité du pilote sont mis à nu. Une seule erreur compromet toute la séquence."),
            ("Dunlop Curve + Degner", "T8-T10", "1300-2200 m", "Gauche en aveugle puis droite-droite. Trail-braking expert nécessaire."),
            ("Spoon Curve", "T13-T14", "3300-3800 m", "Gauche double-apex, very long. Différencie momentum vs rotation."),
            ("130R", "T15", "4300-4600 m", "Gauche flat-out à 320 km/h. Engagement pur, peu de marge."),
            ("Casio Triangle", "T16-T18", "4900-5200 m", "Chicane finale, freinage tardif depuis 130R, sortie sur la ligne droite des stands."),
        ],
    },
    "Miami Grand Prix": {
        "facts": "Circuit street autour du Hard Rock Stadium. 3 zones DRS, surface lisse. Bus-stop final section très technique.",
        "zones": [
            ("T1 droite", "T1", "0-400 m", "Entrée depuis ligne droite, gros freinage. Premier overtaking spot."),
            ("T8 gauche", "T8", "1900-2200 m", "Virage long à gauche, traction sur la sortie."),
            ("T11 freinage", "T11", "2700-3100 m", "Gros freinage avant le bus-stop, fin de la 2ème zone DRS."),
            ("Bus-stop T13-T16", "T13-T16", "3800-4500 m", "Section sinueuse style chicane multiple, ultra technique. Différencie les pilotes capables d'enchaîner les inputs."),
        ],
    },
    "Emilia Romagna Grand Prix": {
        "facts": "Imola, circuit historique en Italie. Très technique, peu d'overtaking. Tamburello et Villeneuve sont des chicanes lourdes de symboles (Senna, Ratzenberger).",
        "zones": [
            ("Tamburello", "T2-T3", "300-800 m", "Première chicane gauche-droite. Site historique. Différenciateur sur l'agressivité au freinage initial."),
            ("Villeneuve", "T4-T5", "900-1300 m", "Chicane droite-gauche, plus rapide que Tamburello."),
            ("Variante Alta", "T9-T10", "2600-3000 m", "Chicane en montée. Engagement total."),
            ("Acque Minerali", "T11-T13", "3100-3700 m", "Droite double-apex, descente. Trail-braking expert."),
            ("Rivazza", "T14-T15", "3800-4400 m", "Gauche double-apex final, descente. Très précis."),
        ],
    },
    "Monaco Grand Prix": {
        "facts": "Le plus mythique. Pas d'overtaking, tout se joue en qualif. Marge zéro, mur partout. Style chirurgical requis.",
        "zones": [
            ("Sainte-Devote", "T1", "0-300 m", "Droite depuis la ligne droite des stands. Crash classique de départ."),
            ("Casino Square", "T4", "700-900 m", "Gauche en aveugle après une bosse. Confidence test."),
            ("Mirabeau Haute + Hairpin", "T5-T6", "1100-1500 m", "L'épingle la plus lente du calendrier (~50 km/h). Trail-braking max."),
            ("Tunnel + Nouvelle Chicane", "T9-T10", "1800-2300 m", "Sortie de tunnel en aveugle à 290 km/h puis gros freinage. Différenciateur visibilité+confiance."),
            ("Swimming Pool", "T13-T16", "2500-2800 m", "Enchaînement gauche-droite-gauche-droite, mur très proche. Précision absolue."),
            ("Rascasse + Anthony Noghes", "T17-T19", "2900-3300 m", "Final, gauche-droite. Très lent, traction critique."),
        ],
    },
    "Spanish Grand Prix": {
        "facts": "Barcelona-Catalunya. Circuit-référence des ingénieurs (les voitures sont testées ici). Mix de virages rapides et lents, lit toutes les qualités d'une voiture.",
        "zones": [
            ("T1-T2-T3", "T1-T3", "0-700 m", "Séquence d'ouverture, gros freinage T1 puis enchaînement."),
            ("T3 long droite", "T3", "700-1100 m", "Long virage à droite, traction critique pour Vmax."),
            ("T9 high-speed", "T9", "2900-3300 m", "Gauche très rapide, engagement aéro pur."),
            ("T10 hairpin", "T10", "3400-3700 m", "Épingle serrée, opportunité d'overtaking."),
            ("Final T13-T15", "T13-T15", "4100-4600 m", "Triple gauche, traction sur la sortie. Section critique du tour."),
        ],
    },
    "Monaco Grand Prix de Monaco": {
        "facts": "Le plus mythique. Pas d'overtaking, tout se joue en qualif.",
        "zones": [
            ("Hairpin", "T6", "1400-1500 m", "L'épingle la plus lente."),
            ("Tunnel", "T9-T10", "1800-2300 m", "Sortie en aveugle puis chicane."),
            ("Swimming Pool", "T13-T16", "2500-2800 m", "Très précis."),
        ],
    },
    "Canadian Grand Prix": {
        "facts": "Circuit Gilles Villeneuve à Montréal, sur l'île Notre-Dame. Stop-and-go, gros freinages, le mur des champions à la fin.",
        "zones": [
            ("T1-T2 chicane", "T1-T2", "0-400 m", "Première chicane après le départ, gros freinage."),
            ("T6-T7 chicane", "T6-T7", "1200-1500 m", "Chicane rapide gauche-droite."),
            ("Hairpin", "T10", "2300-2700 m", "L'épingle la plus lente du calendrier (~60 km/h). Modulation throttle critique en sortie sur Casino Straight."),
            ("Wall of Champions", "T13-T14", "3900-4250 m", "Chicane finale gauche-droite à 30 cm du mur. Hill, Schumacher, Villeneuve s'y sont crashés en 1999. Le test ultime de confiance dans l'avant."),
        ],
    },
    "Austrian Grand Prix": {
        "facts": "Red Bull Ring. Court (~4.3 km), peu de virages mais très intenses. Beaucoup de dénivelé. 3 zones DRS.",
        "zones": [
            ("T1 Niki Lauda", "T1", "200-500 m", "Gros freinage en montée, de 310 à 80 km/h. Premier overtaking spot."),
            ("T3 Remus", "T3", "1100-1400 m", "Droite serrée en sommet, freinage tardif depuis la 2ème ligne droite."),
            ("T4 Schlossgold", "T4", "1700-2000 m", "Gros freinage, gauche serrée. 3ème overtaking spot."),
            ("T6-T7 Rauch", "T6-T7", "2700-3200 m", "Enchaînement rapide droite-gauche en descente."),
            ("T9-T10 final", "T9-T10", "3700-4300 m", "Final, droite puis droite en descente."),
        ],
    },
    "British Grand Prix": {
        "facts": "Silverstone, berceau de la F1 (premier GP en 1950). Circuit ultra-rapide, fortes contraintes aéro. Une vraie qualité de châssis nécessaire.",
        "zones": [
            ("Abbey-Farm", "T1-T2", "0-700 m", "Enchaînement droite-gauche rapide au départ."),
            ("Village-Loop", "T3-T4", "800-1300 m", "Section lente, contraste avec le reste."),
            ("Copse", "T9", "2500-2900 m", "Droite flat-out à 290 km/h. Engagement pur."),
            ("Maggotts-Becketts-Chapel", "T10-T13", "3000-3900 m", "Enchaînement de virages rapides gauche-droite-gauche-droite. Le passage le plus iconique en F1 moderne. Lit le rythme et le grip aéro."),
            ("Stowe", "T15", "4500-4900 m", "Droite rapide après Hangar Straight. Trail-braking modéré."),
            ("Vale-Club", "T16-T18", "5100-5891 m", "Chicane finale lente puis sortie sur la ligne droite des stands."),
        ],
    },
    "Hungarian Grand Prix": {
        "facts": "Hungaroring, surnommé 'Monaco sans murs'. Étroit, sinueux, peu d'overtaking. Setup high-downforce.",
        "zones": [
            ("T1", "T1", "0-400 m", "Gros freinage en descente."),
            ("T2-T3", "T2-T3", "500-900 m", "Droite-gauche rapide."),
            ("T4-T5", "T4-T5", "1000-1500 m", "Gauche-droite, double-apex."),
            ("T11-T12-T13", "T11-T13", "3300-3800 m", "Section finale technique, traction critique."),
            ("T14", "T14", "4000-4381 m", "Droite finale, sortie sur la ligne droite des stands."),
        ],
    },
    "Belgian Grand Prix": {
        "facts": "Spa-Francorchamps, le plus long circuit du calendrier (~7 km). En pleine forêt ardennaise. Météo capricieuse — il peut pleuvoir sur S1 et être sec à S3.",
        "zones": [
            ("La Source", "T1", "150-400 m", "Épingle juste après la grille, freinage de 320 à 80 km/h. Premier overtaking spot, chaos au départ."),
            ("Eau Rouge / Raidillon", "T3-T5", "800-1500 m", "L'enchaînement gauche-droite-gauche le plus iconique de la F1. Compression en sortie de descente puis montée à 300+ km/h. Engagement total nécessaire. Sans visibilité du sommet à l'entrée. Le test de confiance pure."),
            ("Combes", "T7-T9", "2800-3300 m", "Enchaînement droite-gauche-droite, freinage depuis la ligne droite Kemmel. Spot d'overtaking via DRS."),
            ("Pouhon", "T10-T11", "3800-4400 m", "Double-apex gauche très rapide à 280 km/h. Trail-braking expert."),
            ("Stavelot", "T13-T14", "5000-5500 m", "Droite double-apex, traction critique pour S3."),
            ("Bus Stop chicane", "T18-T19", "6500-6900 m", "Chicane finale gauche-droite, gros freinage. Dernier overtaking spot."),
        ],
    },
    "Dutch Grand Prix": {
        "facts": "Zandvoort, circuit côtier néerlandais. Vent omniprésent. Deux virages relevés (T3 et T14) — unique en F1 actuelle.",
        "zones": [
            ("Tarzanbocht", "T1", "0-400 m", "Droite relevée après la ligne droite. Beaucoup d'overtaking possible grâce à la pente."),
            ("Hugenholtzbocht", "T3", "600-900 m", "Gauche relevée banked. Engagement aéro."),
            ("Slotemakerbocht-Scheivlak", "T7-T9", "1900-2400 m", "Section rapide en sommet, sans visibilité de la sortie. Vent ici très perturbant."),
            ("Final banked T14", "T14", "3900-4259 m", "Droite finale relevée (18°), exit sur la ligne droite des stands. La banking permet des sorties à très haute vitesse."),
        ],
    },
    "Italian Grand Prix": {
        "facts": "Monza, le 'Temple de la Vitesse'. Setup low-downforce, longues lignes droites. Aspiration et DRS critiques en course.",
        "zones": [
            ("Variante del Rettifilo", "T1-T2", "0-500 m", "Gros freinage en bout de ligne droite des stands, première chicane droite-gauche. Sortie sur la traction critique."),
            ("Curva Grande + Roggia", "T3-T5", "1100-1800 m", "Droite rapide puis chicane. Section overtaking via aspiration."),
            ("Lesmo 1+2", "T6-T7", "1800-2400 m", "Double droite, engagement et confiance dans l'avant."),
            ("Ascari", "T8-T10", "3700-4300 m", "Chicane droite-gauche-droite ultra rapide. La plus technique du circuit."),
            ("Parabolica", "T11", "5200-5700 m", "Long virage à droite, double apex, sortie sur la ligne droite des stands. La sortie conditionne le tour entier."),
        ],
    },
    "Azerbaijan Grand Prix": {
        "facts": "Baku City Circuit. Mix unique de longue ligne droite (~2 km, la plus longue du calendrier) et de section ville étroite. Imprévisible.",
        "zones": [
            ("T1 entrée", "T1", "0-300 m", "Gros freinage de 340 à 90 km/h depuis la ligne droite des stands."),
            ("Castle section T8", "T8", "1800-2100 m", "Le virage le plus étroit de la F1 — 7.6 m. Pas d'overtaking, prudence absolue."),
            ("Section ville T9-T15", "T9-T15", "2200-3800 m", "Enchaînement de virages serrés, murs proches."),
            ("Long straight + T1", "Long straight", "4000-6003 m", "La ligne droite de 2.2 km. Le coup d'aspiration est la donne de la course."),
        ],
    },
    "Singapore Grand Prix": {
        "facts": "Marina Bay Street Circuit. Course nocturne, 23 virages, le plus exigeant physiquement. Murs partout.",
        "zones": [
            ("T1-T2-T3 chicane", "T1-T3", "0-700 m", "Triple chicane d'ouverture."),
            ("T5 hairpin", "T5", "1100-1400 m", "Épingle après ligne droite, gros freinage."),
            ("Anderson Bridge", "T13", "3000-3300 m", "Sortie de pont en aveugle."),
            ("T16-T19 final", "T16-T19", "4400-5063 m", "Section finale étroite, mur très proche."),
        ],
    },
    "United States Grand Prix": {
        "facts": "COTA (Circuit of the Americas), Austin. Inspiré de Suzuka et Silverstone. T1 en montée brutale, gros freinage.",
        "zones": [
            ("T1", "T1", "0-500 m", "Freinage en montée, 320 à 70 km/h. Premier overtaking spot."),
            ("Esses T2-T6", "T2-T6", "500-1400 m", "Enchaînement S inspiré de Suzuka, ultra rapide."),
            ("T11 hairpin", "T11", "2500-2900 m", "Épingle après back straight, gros freinage."),
            ("Section moyenne T12-T15", "T12-T15", "3000-3800 m", "Section technique de transition."),
            ("T16-T18 hairpin sequence", "T16-T18", "4000-4600 m", "Triple gauche serré."),
            ("T19-T20 final", "T19-T20", "4900-5513 m", "Droite-gauche final."),
        ],
    },
    "Mexico City Grand Prix": {
        "facts": "Autódromo Hermanos Rodríguez. Altitude 2240 m — air raréfié, moins d'appui et de puissance moteur. Longue ligne droite, stade section iconique.",
        "zones": [
            ("T1-T2-T3", "T1-T3", "0-800 m", "Séquence d'ouverture, gros freinage T1 depuis longue ligne droite."),
            ("Esses T7-T11", "T7-T11", "1900-3000 m", "Enchaînement rapide en milieu de tour."),
            ("Stadium section T12-T16", "T12-T16", "3100-3800 m", "Section dans le stade baseball — peu d'appui efficace, traction critique."),
            ("Peraltada (T17-T18)", "T17-T18", "4000-4304 m", "Long droite final relevée. La sortie conditionne la Vmax sur la longue ligne droite."),
        ],
    },
    "São Paulo Grand Prix": {
        "facts": "Interlagos, circuit antihoraire (rare en F1). Météo très changeante (la pluie peut tomber sur S1 et pas S3). Sentier vallonné, course toujours pleine d'action.",
        "zones": [
            ("S do Senna", "T1-T2", "0-500 m", "Gauche-droite d'ouverture en descente. Premier overtaking spot, chaos fréquent."),
            ("Descida do Lago", "T4-T5", "800-1300 m", "Descente technique."),
            ("Junção", "T6-T7", "1700-2100 m", "Épingle à gauche."),
            ("Subida do Boxes", "T12-T15", "3000-3800 m", "Montée vers la ligne droite des stands."),
            ("Arquibancadas final", "T15", "3800-4309 m", "Long droite finale en montée, jusqu'à la ligne droite des stands."),
        ],
    },
    "Las Vegas Grand Prix": {
        "facts": "Las Vegas Strip Circuit. Nocturne, sur le strip. 1.9 km de ligne droite, freinage massif au bout. Asphalte lisse, températures basses la nuit.",
        "zones": [
            ("T1-T4 opening", "T1-T4", "0-1300 m", "Section technique d'ouverture en ville."),
            ("Sphere section T9-T12", "T9-T12", "2500-3500 m", "Passage devant la Sphere, virages moyens."),
            ("T14 freinage", "T14", "5400-5700 m", "Freinage massif de 340+ à 90 km/h en bout du Strip. Le spot d'overtaking principal."),
            ("T16-T17 final", "T16-T17", "5800-6201 m", "Final, droite-gauche avant la ligne d'arrivée."),
        ],
    },
    "Qatar Grand Prix": {
        "facts": "Lusail International Circuit. Beaucoup de virages rapides en S, peu de longues lignes droites. Setup high-downforce.",
        "zones": [
            ("T1 freinage", "T1", "0-400 m", "Premier freinage depuis ligne droite des stands."),
            ("T6-T7 esses", "T6-T7", "1500-2000 m", "Enchaînement rapide."),
            ("T10-T12 technique", "T10-T12", "2700-3400 m", "Section technique en S."),
            ("T13-T14 final", "T13-T14", "4400-5000 m", "Final rapide."),
            ("T16 dernier", "T16", "5100-5419 m", "Dernier virage, exit critique."),
        ],
    },
    "Abu Dhabi Grand Prix": {
        "facts": "Yas Marina Circuit, finale de saison. Course nocturne (passage jour-nuit). Refait en 2021 pour plus d'overtaking.",
        "zones": [
            ("T1", "T1", "0-400 m", "Gros freinage en début de tour, freinage depuis 330 km/h."),
            ("T6-T7", "T6-T7", "1900-2300 m", "Chicane droite-gauche, technique."),
            ("T9 long left", "T9", "2700-3100 m", "Gauche très long, traction sortie pour la longue ligne droite."),
            ("T10 hairpin", "T10", "3100-3400 m", "Épingle après longue ligne droite, gros freinage."),
            ("T12-T16 hotel section", "T12-T16", "4400-5281 m", "Section finale autour du hotel Yas, technique."),
        ],
    },
    "Saudi Arabian Grand Prix": {
        "facts": "Jeddah Corniche Circuit. Le plus rapide circuit urbain du calendrier (~250 km/h de moyenne). 27 virages, murs partout, à éviter en course en peloton.",
        "zones": [
            ("T1 freinage", "T1", "0-400 m", "Gros freinage de 330 à 100 km/h depuis ligne droite des stands."),
            ("Esses T4-T13", "T4-T13", "900-3000 m", "Très long enchaînement de virages rapides, murs proches. Engagement pur."),
            ("T22-T23", "T22-T23", "5000-5500 m", "Banked turn rapide, unique en F1."),
            ("T27 final", "T27", "6000-6174 m", "Dernier virage, exit sur ligne droite des stands."),
        ],
    },
}

# ============== CACHED LOADERS ==============
@st.cache_data(show_spinner=False, ttl=24*3600)
def load_schedule(year):
    """Charge le calendrier d'une année."""
    sched = fastf1.get_event_schedule(year, include_testing=False)
    return sched[["RoundNumber", "EventName", "Country", "Location", "EventDate"]]

@st.cache_resource(show_spinner=False, ttl=24*3600)
def load_session(year, gp, session_type):
    """Charge une session F1. Le résultat est mis en cache pour éviter de rerecharger."""
    s = fastf1.get_session(year, gp, session_type)
    s.load()
    return s

# ============== HEADER ==============
st.markdown("""
# 🏎️ F1 Style Decoder
### Lecture télémétrique des styles de pilotage en Formule 1
""")

# ============== SIDEBAR — CONTRÔLES ==============
st.sidebar.markdown("## 🎛️ Paramètres")

year = st.sidebar.selectbox(
    "Saison",
    options=list(range(2026, 2017, -1)),
    index=1,  # 2025 par défaut
    help="FastF1 supporte 2018 → présent. Les données 2026 récentes peuvent être partielles.",
)

with st.spinner(f"Chargement du calendrier {year}…"):
    schedule = load_schedule(year)

gp_options = {
    f"R{int(row.RoundNumber)} — {row.EventName} ({row.Country})": row.EventName
    for _, row in schedule.iterrows()
}
gp_label = st.sidebar.selectbox(
    "Grand Prix",
    options=list(gp_options.keys()),
    index=min(len(gp_options) - 1, 12),  # Spa par défaut souvent vers le milieu
)
gp_name = gp_options[gp_label]

session_type = st.sidebar.selectbox(
    "Session",
    options=["Q", "R", "SQ", "S", "FP3", "FP2", "FP1"],
    index=0,
    format_func=lambda x: {
        "Q": "Qualifications",
        "R": "Course",
        "SQ": "Sprint Shootout",
        "S": "Sprint",
        "FP3": "Essais Libres 3",
        "FP2": "Essais Libres 2",
        "FP1": "Essais Libres 1",
    }[x],
)

# Bouton pour déclencher le chargement
load_btn = st.sidebar.button("🚀 Charger la session", type="primary", use_container_width=True)

if load_btn or "session_loaded" in st.session_state:
    st.session_state.session_loaded = True
    st.session_state.year = year
    st.session_state.gp_name = gp_name
    st.session_state.session_type = session_type

if not st.session_state.get("session_loaded"):
    st.info("👈 Configure les paramètres dans la barre latérale et clique sur **Charger la session**.")
    st.stop()

# ============== CHARGEMENT DE LA SESSION ==============
try:
    with st.spinner(f"Chargement {gp_name} {year} {session_type}…"):
        session = load_session(
            st.session_state.year,
            st.session_state.gp_name,
            st.session_state.session_type,
        )
except Exception as e:
    st.error(f"❌ Impossible de charger la session : {e}")
    st.stop()

# Pilotes disponibles
drivers_in_session = sorted(session.laps["Driver"].unique().tolist())
if not drivers_in_session:
    st.error("Aucun pilote n'a roulé dans cette session.")
    st.stop()

# Récupère les noms complets pour l'UX
driver_full = {}
for d in drivers_in_session:
    try:
        info = session.get_driver(d)
        driver_full[d] = f"{d} — {info['FullName']} ({info['TeamName']})"
    except Exception:
        driver_full[d] = d

# --- Sélection des pilotes ---
st.sidebar.markdown("---")
st.sidebar.markdown("### Pilotes à comparer")
default_d1 = "VER" if "VER" in drivers_in_session else drivers_in_session[0]
default_d2 = "LEC" if "LEC" in drivers_in_session else drivers_in_session[1]
d1 = st.sidebar.selectbox(
    "Pilote 1",
    options=drivers_in_session,
    index=drivers_in_session.index(default_d1),
    format_func=lambda x: driver_full.get(x, x),
)
d2 = st.sidebar.selectbox(
    "Pilote 2",
    options=drivers_in_session,
    index=drivers_in_session.index(default_d2),
    format_func=lambda x: driver_full.get(x, x),
)

def driver_color(drv):
    try:
        team = session.get_driver(drv)["TeamName"]
        return TEAM_COLORS.get(team, "#888888")
    except Exception:
        return "#888888"

c1, c2 = driver_color(d1), driver_color(d2)
# S'assure que les deux couleurs sont différentes
if c1 == c2:
    c2 = "#FFD700"  # gold fallback

# ============== SÉLECTION DU TOUR À ANALYSER ==============
st.sidebar.markdown("---")
st.sidebar.markdown("### Tour à analyser")

def get_lap_options(drv):
    """Retourne la liste des tours valides + descriptions + tour rapide pour le sélecteur."""
    laps_drv = session.laps.pick_drivers(drv)
    valid = laps_drv.loc[laps_drv["LapTime"].notna()].copy()
    if valid.empty:
        return [], {}, None
    fastest = valid.pick_fastest()
    fastest_num = int(fastest["LapNumber"])
    
    options = []
    descriptions = {}
    for _, row in valid.iterrows():
        n = int(row["LapNumber"])
        lt = row["LapTime"].total_seconds()
        compound = str(row.get("Compound", "—"))[:1] if pd.notna(row.get("Compound")) else "—"
        is_fastest_marker = " ⚡" if n == fastest_num else ""
        time_str = f"{int(lt // 60)}:{lt % 60:06.3f}"
        options.append(n)
        descriptions[n] = f"L{n:>2} — {time_str} ({compound}){is_fastest_marker}"
    return options, descriptions, fastest_num

opts1, desc1, fast1 = get_lap_options(d1)
opts2, desc2, fast2 = get_lap_options(d2)

if not opts1 or not opts2:
    st.error("⚠️ Un des deux pilotes n'a pas de tour valide dans cette session.")
    st.stop()

lap_n1 = st.sidebar.selectbox(
    f"Tour {d1}",
    options=opts1,
    index=opts1.index(fast1),
    format_func=lambda n: desc1.get(n, f"L{n}"),
    help="⚡ marque le tour le plus rapide. Tu peux choisir n'importe quel autre tour.",
)
lap_n2 = st.sidebar.selectbox(
    f"Tour {d2}",
    options=opts2,
    index=opts2.index(fast2),
    format_func=lambda n: desc2.get(n, f"L{n}"),
)

# Récupère l'objet Lap correspondant au tour choisi
laps_d1_all = session.laps.pick_drivers(d1)
laps_d2_all = session.laps.pick_drivers(d2)
lap1 = laps_d1_all[laps_d1_all["LapNumber"] == lap_n1].iloc[0]
lap2 = laps_d2_all[laps_d2_all["LapNumber"] == lap_n2].iloc[0]

if pd.isna(lap1.get("LapTime")) or pd.isna(lap2.get("LapTime")):
    st.error(f"⚠️ Données manquantes pour le tour sélectionné.")
    st.stop()

tel1 = lap1.get_car_data().add_distance()
tel2 = lap2.get_car_data().add_distance()

# ============== HEADER DE SESSION ==============
ev = session.event
st.markdown(f"### {ev['EventName']} {st.session_state.year} — {st.session_state.session_type}")
st.caption(f"📍 {ev['Location']}, {ev['Country']} · {ev['EventDate'].strftime('%d %B %Y')}")

# ============== CLASSEMENT DE LA SESSION ==============
def build_leaderboard(sess):
    """Construit le classement des meilleurs tours de la session."""
    rows = []
    for drv in sess.laps["Driver"].unique():
        fast = sess.laps.pick_drivers(drv).pick_fastest()
        if fast is None or pd.isna(fast.get("LapTime")):
            continue
        try:
            info = sess.get_driver(drv)
            team = info.get("TeamName", "—")
            name = info.get("FullName", drv)
        except Exception:
            team = "—"
            name = drv
        lap_s = fast["LapTime"].total_seconds()
        rows.append({
            "Code": drv,
            "Pilote": name,
            "Équipe": team,
            "_lap_seconds": lap_s,
            "Meilleur tour": f"{int(lap_s // 60)}:{lap_s % 60:06.3f}",
            "Pneu": fast.get("Compound", "—"),
        })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values("_lap_seconds").reset_index(drop=True)
    leader = df["_lap_seconds"].iloc[0]
    df["Écart"] = df["_lap_seconds"].apply(
        lambda t: "—" if t == leader else f"+{t - leader:.3f}s"
    )
    df.insert(0, "Pos", df.index + 1)
    df = df.drop(columns="_lap_seconds")
    return df

with st.expander("🏁 Classement de la session — meilleurs tours", expanded=True):
    leaderboard = build_leaderboard(session)
    if leaderboard.empty:
        st.info("Aucun tour valide enregistré.")
    else:
        # Surligne les 2 pilotes sélectionnés
        def highlight_selected(row):
            if row["Code"] == d1:
                return [f"background-color: {c1}30; font-weight: bold"] * len(row)
            if row["Code"] == d2:
                return [f"background-color: {c2}30; font-weight: bold"] * len(row)
            return [""] * len(row)
        
        styled = leaderboard.style.apply(highlight_selected, axis=1)
        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True,
            height=min(38 * (len(leaderboard) + 1) + 3, 600),
            column_config={
                "Pos": st.column_config.NumberColumn("Pos", width="small"),
                "Code": st.column_config.TextColumn("Code", width="small"),
                "Pilote": st.column_config.TextColumn("Pilote", width="medium"),
                "Équipe": st.column_config.TextColumn("Équipe", width="medium"),
                "Meilleur tour": st.column_config.TextColumn("Meilleur tour", width="small"),
                "Écart": st.column_config.TextColumn("Écart", width="small"),
                "Pneu": st.column_config.TextColumn("Pneu", width="small"),
            },
        )
        st.caption(
            f"👉 Les lignes surlignées correspondent aux pilotes sélectionnés ({d1} et {d2}). "
            f"Change-les dans la barre latérale pour voir une autre comparaison."
        )

# ============== BRIEFING CIRCUIT ==============
event_name = ev["EventName"]
circuit_info_data = CIRCUITS_INFO.get(event_name)

if circuit_info_data:
    with st.expander(f"📍 Briefing circuit — {ev['Location']}", expanded=True):
        st.markdown(f"**{circuit_info_data['facts']}**")
        st.markdown("")
        
        # Tableau des zones intéressantes
        zones_df = pd.DataFrame(
            circuit_info_data["zones"],
            columns=["Zone", "Virage(s)", "Distance approx.", "Pourquoi c'est intéressant"],
        )
        st.dataframe(
            zones_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Zone": st.column_config.TextColumn("Zone", width="medium"),
                "Virage(s)": st.column_config.TextColumn("Virage(s)", width="small"),
                "Distance approx.": st.column_config.TextColumn("Distance approx.", width="small"),
                "Pourquoi c'est intéressant": st.column_config.TextColumn("Pourquoi c'est intéressant", width="large"),
            },
        )
        st.caption(
            "💡 Les distances sont indicatives — utilise l'onglet **🔍 Zoom virage** pour ajuster précisément, "
            "ou tape `session.get_circuit_info().corners` dans une cellule notebook pour les distances exactes "
            "selon la mesure FastF1."
        )
else:
    st.info(f"ℹ️ Pas encore de briefing détaillé pour **{event_name}** dans la base. "
            f"Tu peux toujours explorer via les onglets ci-dessous.")

# --- Métriques principales ---
col1, col2, col3, col4 = st.columns(4)
t1 = lap1["LapTime"].total_seconds()
t2 = lap2["LapTime"].total_seconds()
lap_label1 = f"L{lap_n1} {'⚡' if lap_n1 == fast1 else ''}"
lap_label2 = f"L{lap_n2} {'⚡' if lap_n2 == fast2 else ''}"
col1.metric(f"{d1} — {lap_label1}", f"{t1:.3f}s",
            help=f"Tour {lap_n1} de {d1}" + (" (le plus rapide)" if lap_n1 == fast1 else ""))
col2.metric(f"{d2} — {lap_label2}", f"{t2:.3f}s",
            help=f"Tour {lap_n2} de {d2}" + (" (le plus rapide)" if lap_n2 == fast2 else ""))
col3.metric("Écart", f"{abs(t1-t2):.3f}s",
            delta=f"{d1 if t1 < t2 else d2} plus rapide", delta_color="off")
col4.metric("Circuit", f"{tel1['Distance'].max():.0f} m")

# ============== TABS ==============
tab1, tab_map, tab2, tab_corners, tab3, tab4, tab5, tab_stint, tab_craft, tab_fit, tab6 = st.tabs([
    "🎯 Overlay télémétrie",
    "🗺️ Vue circuit",
    "⏱️ Delta time",
    "🧠 Virage par virage",
    "🎨 Signatures de style",
    "🔍 Zoom virage",
    "📊 Secteurs",
    "📈 Évolution course",
    "🥊 Race craft",
    "🏟️ Auto vs circuit",
    "🕸️ Radar multi-pilotes",
])

# --- TAB 1 : OVERLAY ---
with tab1:
    st.markdown("Vitesse, throttle, frein et rapport superposés sur la distance — survole les courbes pour les valeurs précises.")
    
    circuit_info = session.get_circuit_info()
    corners = circuit_info.corners if circuit_info else None
    
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04,
        subplot_titles=("Vitesse (km/h)", "Throttle (%)", "Frein", "Rapport"),
    )
    channels = ["Speed", "Throttle", "Brake", "nGear"]
    for i, ch in enumerate(channels, start=1):
        fig.add_trace(go.Scatter(
            x=tel1["Distance"], y=tel1[ch], name=d1,
            line=dict(color=c1, width=1.8),
            legendgroup=d1, showlegend=(i == 1),
        ), row=i, col=1)
        fig.add_trace(go.Scatter(
            x=tel2["Distance"], y=tel2[ch], name=d2,
            line=dict(color=c2, width=1.8),
            legendgroup=d2, showlegend=(i == 1),
        ), row=i, col=1)
    
    # Lignes verticales aux virages
    if corners is not None:
        for _, corner in corners.iterrows():
            for r in range(1, 5):
                fig.add_vline(x=corner["Distance"], line=dict(color="white", width=0.5, dash="dot"),
                              opacity=0.2, row=r, col=1)
        # Annotations virages sur le subplot du bas
        fig.update_xaxes(
            tickvals=corners["Distance"].tolist(),
            ticktext=[f"T{int(c['Number'])}{c['Letter']}" for _, c in corners.iterrows()],
            row=4, col=1,
        )
    
    fig.update_layout(
        height=750, template="plotly_dark",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"),
        margin=dict(t=40, b=20, l=20, r=20),
    )
    fig.update_xaxes(title_text="Virage" if corners is not None else "Distance (m)", row=4, col=1)
    st.plotly_chart(fig, use_container_width=True)

# --- TAB MAP : VUE CIRCUIT ---
with tab_map:
    st.markdown("Le tracé du circuit, colorié selon le paramètre choisi. Repère **où** chaque pilote roule fort, où il freine, où il prend du temps.")
    
    # Télémétrie complète avec X/Y (position GPS sur le tracé)
    tel1_full = lap1.get_telemetry()
    tel2_full = lap2.get_telemetry()
    
    color_by = st.radio(
        "Colorer par",
        options=["Speed", "Throttle", "Brake", "nGear"],
        format_func=lambda x: {"Speed": "Vitesse", "Throttle": "Throttle",
                                "Brake": "Frein", "nGear": "Rapport"}[x],
        horizontal=True,
        key="map_color_by",
    )
    
    # Échelle commune aux deux pilotes pour comparabilité
    vmin = float(min(tel1_full[color_by].min(), tel2_full[color_by].min()))
    vmax = float(max(tel1_full[color_by].max(), tel2_full[color_by].max()))
    colorscale = "Plasma" if color_by == "Speed" else "Viridis"
    
    fig_map = make_subplots(
        rows=1, cols=2,
        subplot_titles=(f"<b>{d1}</b>", f"<b>{d2}</b>"),
        horizontal_spacing=0.04,
    )
    for i, (tel, drv) in enumerate([(tel1_full, d1), (tel2_full, d2)], start=1):
        fig_map.add_trace(go.Scatter(
            x=tel["X"], y=tel["Y"],
            mode="markers",
            marker=dict(
                color=tel[color_by],
                colorscale=colorscale,
                cmin=vmin, cmax=vmax,
                size=4,
                showscale=(i == 2),
                colorbar=dict(
                    title=dict(text=color_by, side="right"),
                    thickness=12, x=1.02,
                ) if i == 2 else None,
            ),
            showlegend=False,
            hovertemplate=f"{color_by}: %{{marker.color:.0f}}<extra></extra>",
        ), row=1, col=i)
    # Aspect ratio égal pour ne pas déformer le tracé
    for col in (1, 2):
        fig_map.update_xaxes(scaleanchor=f"y{col if col > 1 else ''}", scaleratio=1,
                             showticklabels=False, showgrid=False, zeroline=False,
                             row=1, col=col)
        fig_map.update_yaxes(showticklabels=False, showgrid=False, zeroline=False,
                             row=1, col=col)
    fig_map.update_layout(height=550, template="plotly_dark",
                          margin=dict(t=50, b=20, l=20, r=80))
    st.plotly_chart(fig_map, use_container_width=True)
    
    # --- Battle map : qui est plus rapide à chaque endroit du tracé ---
    st.markdown("---")
    st.markdown(f"#### ⚔️ Battle map — qui est plus rapide à chaque point du tracé")
    st.caption(
        f"Couleur {d1} = {d1} plus rapide à ce point · Couleur {d2} = {d2} plus rapide · "
        f"Blanc = égalité. L'intensité de la couleur = ampleur de l'écart."
    )
    
    # Interpole la vitesse de tel2 sur la grille de distance de tel1 pour pouvoir comparer
    from numpy import interp
    tel2_speed_aligned = interp(
        tel1_full["Distance"].values,
        tel2_full["Distance"].values,
        tel2_full["Speed"].values,
    )
    speed_delta = tel1_full["Speed"].values - tel2_speed_aligned
    
    # Custom colorscale : c2 (négatif, d2 plus rapide) → blanc (0) → c1 (positif, d1 plus rapide)
    def hex_to_rgb_str(h):
        h = h.lstrip("#")
        return f"rgb({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)})"
    
    custom_scale = [
        [0.0, hex_to_rgb_str(c2)],
        [0.5, "rgb(255,255,255)"],
        [1.0, hex_to_rgb_str(c1)],
    ]
    # Échelle symétrique pour que 0 = blanc soit toujours au milieu
    abs_max = float(np.percentile(np.abs(speed_delta), 95))  # robuste aux outliers
    
    fig_battle = go.Figure(go.Scatter(
        x=tel1_full["X"], y=tel1_full["Y"],
        mode="markers",
        marker=dict(
            color=speed_delta,
            colorscale=custom_scale,
            cmin=-abs_max, cmax=abs_max,
            size=6,
            colorbar=dict(
                title=dict(text=f"Δ vitesse<br>(km/h)", side="right"),
                thickness=12,
            ),
        ),
        hovertemplate=f"Δ vitesse ({d1}−{d2}): %{{marker.color:+.1f}} km/h<extra></extra>",
    ))
    fig_battle.update_xaxes(scaleanchor="y", scaleratio=1,
                            showticklabels=False, showgrid=False, zeroline=False)
    fig_battle.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)
    fig_battle.update_layout(height=600, template="plotly_dark",
                             margin=dict(t=20, b=20, l=20, r=80))
    st.plotly_chart(fig_battle, use_container_width=True)
    
    with st.expander("💡 Comment lire la battle map vitesse"):
        st.markdown(f"""
        - **Zones bleues/colorées D1** : {d1} était plus rapide à cet endroit précis du tracé
        - **Zones colorées D2** : {d2} était plus rapide
        - **Zones blanches** : vitesses quasi identiques (égalité ou écart < 5 km/h)
        - **L'intensité** : plus la couleur est saturée, plus l'écart est grand à cet endroit
        
        ⚠️ **Attention** : la vitesse ne dit pas tout. Un pilote peut être plus rapide à un point précis mais avoir perdu du temps juste avant. Pour ça, regarde la heatmap de gain de temps ci-dessous.
        """)
    
    # --- Heatmap de gain/perte de temps ---
    st.markdown("---")
    st.markdown(f"#### 🌡️ Heatmap du gain de temps — qui prend du temps, où exactement")
    st.caption(
        f"Mesure le **gain de temps local** à chaque mètre du tracé (dérivée du delta time cumulé). "
        f"Bien plus parlant que la vitesse seule : un pilote peut être plus rapide à un point mais avoir "
        f"perdu du temps juste avant. Ici on lit le **temps réellement gagné** seconde par seconde."
    )
    
    try:
        from scipy.ndimage import uniform_filter1d
        delta_t, ref_tel_dt, _ = delta_time(lap1, lap2)
        local_gain = np.gradient(np.asarray(delta_t))
        # Lissage léger pour atténuer le bruit (sur ~10 échantillons)
        local_gain_smooth = uniform_filter1d(local_gain, size=10)
        
        # Convention sign : delta > 0 = D2 plus rapide cumulé → gradient > 0 = D2 gagne du temps
        custom_scale_time = [
            [0.0, hex_to_rgb_str(c1)],   # D1 gagne (gain négatif)
            [0.5, "rgb(255,255,255)"],
            [1.0, hex_to_rgb_str(c2)],   # D2 gagne (gain positif)
        ]
        abs_max_gain = float(np.percentile(np.abs(local_gain_smooth), 95))
        if abs_max_gain == 0:
            abs_max_gain = 1e-4  # garde-fou
        
        fig_heat = go.Figure(go.Scatter(
            x=ref_tel_dt["X"], y=ref_tel_dt["Y"],
            mode="markers",
            marker=dict(
                color=local_gain_smooth,
                colorscale=custom_scale_time,
                cmin=-abs_max_gain, cmax=abs_max_gain,
                size=6,
                colorbar=dict(
                    title=dict(text="Gain local<br>(s)", side="right"),
                    thickness=12,
                    tickformat=".4f",
                ),
            ),
            customdata=np.stack([local_gain_smooth * 1000], axis=-1),
            hovertemplate=f"Gain local: %{{customdata[0]:+.2f}} ms<extra></extra>",
        ))
        fig_heat.update_xaxes(scaleanchor="y", scaleratio=1,
                              showticklabels=False, showgrid=False, zeroline=False)
        fig_heat.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)
        fig_heat.update_layout(height=600, template="plotly_dark",
                               margin=dict(t=20, b=20, l=20, r=80))
        st.plotly_chart(fig_heat, use_container_width=True)
        
        # Trouve les 3 zones où chaque pilote gagne le plus
        gain_d1 = -local_gain_smooth  # D1 gain = gradient négatif
        gain_d2 = local_gain_smooth
        # Distance des top zones
        if "Distance" in ref_tel_dt.columns:
            top_d1_idx = np.argsort(gain_d1)[-5:][::-1]
            top_d2_idx = np.argsort(gain_d2)[-5:][::-1]
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**🔝 Top zones de gain pour {d1}**")
                for i in top_d1_idx:
                    dist = ref_tel_dt["Distance"].iloc[i]
                    gain = gain_d1[i] * 1000
                    st.markdown(f"- Distance {dist:.0f} m : **+{gain:.1f} ms/échantillon**")
            with col_b:
                st.markdown(f"**🔝 Top zones de gain pour {d2}**")
                for i in top_d2_idx:
                    dist = ref_tel_dt["Distance"].iloc[i]
                    gain = gain_d2[i] * 1000
                    st.markdown(f"- Distance {dist:.0f} m : **+{gain:.1f} ms/échantillon**")
        
        with st.expander("💡 Comment lire la heatmap de gain de temps"):
            st.markdown(f"""
            **C'est la visu la plus précise pour comprendre où la course se joue.**
            
            - **Zone colorée {d1}** : {d1} **gagne du temps** sur ce mètre de circuit (que ce soit en étant plus rapide en vitesse ou en ayant un meilleur angle d'attaque qui ouvre la suite)
            - **Zone colorée {d2}** : {d2} **gagne du temps** ici
            - **Zone blanche** : ils sont à égalité sur ce micro-segment
            - **Intensité** : ampleur du gain (en ms par échantillon de télémétrie)
            
            **Combo gagnant à analyser** :
            1. Repère les **clusters** de couleur sur la heatmap (3-5 mètres consécutifs de même couleur)
            2. Croise avec l'onglet **Overlay** pour comprendre **pourquoi** : freinage plus tardif ? throttle plus tôt ? vitesse mini plus haute ?
            3. Ça te dit qu'à ce virage spécifique, ce pilote a un **avantage technique** précis
            
            ⚠️ La différence fondamentale avec la battle map vitesse :
            - **Battle map vitesse** : où chacun **roule plus vite** (peut être trompeur)
            - **Heatmap gain temps** : où chacun **gagne réellement du temps** (la vérité au chrono)
            """)
    except Exception as e:
        st.warning(f"Impossible de calculer la heatmap de gain : {e}")

# --- TAB 2 : DELTA TIME ---
with tab2:
    st.markdown("Où chaque pilote gagne ou perd du temps. **Courbe au-dessus de zéro = {} plus rapide**, en-dessous = {} plus rapide.".format(d2, d1))
    
    try:
        delta, ref_tel, comp_tel = delta_time(lap1, lap2)
        
        fig = go.Figure()
        # Fill positif
        fig.add_trace(go.Scatter(
            x=ref_tel["Distance"], y=delta,
            mode="lines", line=dict(color="white", width=2),
            fill="tozeroy", fillcolor=f"rgba{tuple(int(c2[i:i+2], 16) for i in (1,3,5)) + (0.3,)}",
            name=f"Δ {d1} − {d2}",
        ))
        fig.add_hline(y=0, line=dict(color="grey", dash="dash"))
        fig.update_layout(
            height=450, template="plotly_dark",
            xaxis_title="Distance (m)",
            yaxis_title=f"Δ {d1} − {d2} (s)",
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Impossible de calculer le delta time : {e}")

# --- TAB 3 : SIGNATURES ---
with tab3:
    st.markdown("Métriques chiffrées qui caractérisent le style de chaque pilote sur son tour rapide.")
    
    def style_sig(tel, name):
        sig = {"Pilote": name}
        sig["Vmax (km/h)"] = round(float(tel["Speed"].max()), 1)
        low_mask = tel["Speed"] < tel["Speed"].quantile(0.30)
        sig["V_min médiane courbes (km/h)"] = round(float(tel.loc[low_mask, "Speed"].median()), 1)
        sig["% temps full throttle"] = round(float((tel["Throttle"] >= 99).mean() * 100), 1)
        sig["% temps au frein"] = round(float((tel["Brake"] > 0).mean() * 100), 1)
        coast = (tel["Throttle"] < 5) & (tel["Brake"] == 0)
        sig["% temps en coast"] = round(float(coast.mean() * 100), 1)
        dthr = np.diff(tel["Throttle"].values)
        rising = dthr[dthr > 0]
        sig["Throttle ramp-up moyen"] = round(float(rising.mean()) if len(rising) else 0, 2)
        brake_diff = np.diff((tel["Brake"] > 0).astype(int))
        sig["Nb phases de freinage"] = int((brake_diff == 1).sum())
        return sig
    
    sig1 = style_sig(tel1, d1)
    sig2 = style_sig(tel2, d2)
    df = pd.DataFrame([sig1, sig2]).set_index("Pilote").T
    df["Δ (D1−D2)"] = (df[d1] - df[d2]).round(2)
    
    st.dataframe(df, use_container_width=True, height=320)
    
    # Interprétation
    with st.expander("💡 Comment lire ces signatures"):
        st.markdown("""
        - **`% temps full throttle`** plus élevé = style **binaire/agressif** (rotation-style typique).
        - **`% temps en coast`** plus élevé = pilote qui **module** entre frein et gaz, joue avec le rotation de l'arrière. Signature classique Verstappen.
        - **`Throttle ramp-up`** élevé = réapplication brutale du gaz (Verstappen). Bas = progression lisse (Hamilton, Norris).
        - **`V_min médiane courbes`** élevée = style **momentum** (porte de la vitesse en courbe, Norris, Hamilton). Basse = style **rotation** (V-shape, Verstappen).
        - **`Nb phases de freinage`** : indicateur indirect du nombre de virages où on freine. Diffère peu entre 2 pilotes sur même circuit, mais utile pour repérer des freinages "manqués" ou ajoutés.
        """)

# --- TAB 4 : ZOOM ---
with tab4:
    st.markdown("Zoome sur une portion spécifique du circuit pour décortiquer un virage.")
    
    max_dist = int(min(tel1["Distance"].max(), tel2["Distance"].max()))
    col_z1, col_z2 = st.columns(2)
    with col_z1:
        z_range = st.slider(
            "Plage de distance (m)",
            min_value=0, max_value=max_dist,
            value=(int(max_dist*0.1), int(max_dist*0.25)),
            step=50,
        )
    with col_z2:
        z_label = st.text_input("Étiquette de la section", value="Zoom virage")
    
    z_start, z_end = z_range
    m1 = (tel1["Distance"] > z_start) & (tel1["Distance"] < z_end)
    m2 = (tel2["Distance"] > z_start) & (tel2["Distance"] < z_end)
    
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
        subplot_titles=("Vitesse", "Throttle", "Frein"),
    )
    for i, ch in enumerate(["Speed", "Throttle", "Brake"], start=1):
        fig.add_trace(go.Scatter(x=tel1.loc[m1, "Distance"], y=tel1.loc[m1, ch],
                                 name=d1, line=dict(color=c1, width=2),
                                 legendgroup=d1, showlegend=(i == 1)),
                      row=i, col=1)
        fig.add_trace(go.Scatter(x=tel2.loc[m2, "Distance"], y=tel2.loc[m2, ch],
                                 name=d2, line=dict(color=c2, width=2),
                                 legendgroup=d2, showlegend=(i == 1)),
                      row=i, col=1)
    fig.update_layout(height=600, template="plotly_dark", hovermode="x unified",
                      title=f"{z_label} ({z_start}-{z_end} m)")
    fig.update_xaxes(title_text="Distance (m)", row=3, col=1)
    st.plotly_chart(fig, use_container_width=True)
    
    # Préselections de zoom utiles
    with st.expander("📍 Plages utiles selon le circuit"):
        st.markdown("""
        **Spa-Francorchamps (~7004 m)** : Eau Rouge/Raidillon `800-2000` · Pouhon `3800-4400` · Stavelot `5000-5500` · Bus Stop `6500-6900`  
        **Monaco (~3337 m)** : Tunnel `1800-2300` · Rascasse `2900-3300`  
        **Monza (~5793 m)** : Variante del Rettifilo `0-500` · Lesmo 1+2 `1800-2400` · Parabolica `5200-5700`  
        **Circuit Gilles Villeneuve (~4361 m)** : Hairpin `2300-2700` · Wall of Champions `3900-4250`  
        **Suzuka (~5807 m)** : Esses S1-S6 `400-1300` · 130R `4300-4600` · Casio Triangle `4900-5200`
        """)

# --- TAB 5 : SECTEURS ---
with tab5:
    st.markdown("Comparaison secteur par secteur des tours rapides.")
    
    sectors_data = []
    for i in (1, 2, 3):
        s1_val = lap1[f"Sector{i}Time"].total_seconds()
        s2_val = lap2[f"Sector{i}Time"].total_seconds()
        sectors_data.append({"Secteur": f"S{i}", d1: s1_val, d2: s2_val,
                             "Δ": s1_val - s2_val,
                             "Plus rapide": d2 if s1_val > s2_val else d1})
    df_sec = pd.DataFrame(sectors_data).set_index("Secteur")
    
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.dataframe(df_sec.round(3), use_container_width=True)
    with col_b:
        bar_colors = [c2 if d > 0 else c1 for d in df_sec["Δ"]]
        fig = go.Figure(go.Bar(
            x=df_sec.index, y=df_sec["Δ"],
            marker_color=bar_colors,
            text=[f"{d:+.3f}s" for d in df_sec["Δ"]],
            textposition="outside",
        ))
        fig.add_hline(y=0, line=dict(color="white"))
        fig.update_layout(
            height=400, template="plotly_dark",
            yaxis_title=f"Δ {d1} − {d2} (s)",
            title=f"Écart par secteur ({d2 if df_sec['Δ'].sum() > 0 else d1} plus rapide au total)",
        )
        st.plotly_chart(fig, use_container_width=True)

# --- TAB STINT : ÉVOLUTION COURSE ---
with tab_stint:
    st.markdown("Évolution des temps au tour par relai pneu (stint). **Principalement utile en course** (R), mais marche aussi sur les longs runs FP2.")
    
    def get_stint_laps(drv):
        """Récupère les tours valides d'un pilote avec infos de stint."""
        laps_drv = session.laps.pick_drivers(drv)
        # Filtre : tours avec LapTime valide, exclut in/out laps
        valid = laps_drv.loc[laps_drv["LapTime"].notna()].copy()
        if "PitOutTime" in valid.columns:
            valid = valid.loc[valid["PitOutTime"].isna() | (valid["LapNumber"] > 1)]
        valid["LapTimeSeconds"] = valid["LapTime"].dt.total_seconds()
        return valid
    
    laps_d1_s = get_stint_laps(d1)
    laps_d2_s = get_stint_laps(d2)
    
    if len(laps_d1_s) < 2 and len(laps_d2_s) < 2:
        st.info("Pas assez de tours pour analyser l'évolution. Cet onglet est conçu pour les sessions de type course ou long-run.")
    else:
        # Option : filtrer les outliers (tours > médiane × 1.1)
        col_opt1, col_opt2 = st.columns([1, 3])
        with col_opt1:
            filter_outliers = st.checkbox("Filtrer outliers", value=True,
                                          help="Cache les tours > 110% de la médiane (sortie de piste, drapeau jaune, etc.)")
        
        # --- Graphique principal ---
        fig_stint = go.Figure()
        
        for laps_drv, drv, line_color in [(laps_d1_s, d1, c1), (laps_d2_s, d2, c2)]:
            if len(laps_drv) == 0:
                continue
            
            # Filtre outliers
            if filter_outliers and len(laps_drv) > 3:
                median = laps_drv["LapTimeSeconds"].median()
                laps_drv = laps_drv.loc[laps_drv["LapTimeSeconds"] < median * 1.10]
            
            # Une trace par stint pour casser les lignes entre stints
            if "Stint" in laps_drv.columns:
                stints_groups = laps_drv.groupby("Stint")
            else:
                stints_groups = [(1, laps_drv)]
            
            for stint_num, stint_laps in stints_groups:
                if len(stint_laps) == 0:
                    continue
                compound = str(stint_laps["Compound"].iloc[0]) if "Compound" in stint_laps else "—"
                comp_col = compound_color(compound)
                
                fig_stint.add_trace(go.Scatter(
                    x=stint_laps["LapNumber"],
                    y=stint_laps["LapTimeSeconds"],
                    mode="lines+markers",
                    line=dict(color=line_color, width=2.5),
                    marker=dict(
                        color=comp_col, size=10,
                        line=dict(color=line_color, width=2),
                    ),
                    name=f"{drv} - Stint {int(stint_num)} ({compound})",
                    hovertemplate=(
                        f"<b>{drv}</b><br>"
                        "Tour %{x}<br>"
                        "Temps: %{y:.3f}s<br>"
                        f"Compound: {compound}<extra></extra>"
                    ),
                ))
        
        fig_stint.update_layout(
            height=500, template="plotly_dark",
            xaxis_title="Numéro de tour",
            yaxis_title="Temps au tour (s)",
            hovermode="closest",
            legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
        )
        st.plotly_chart(fig_stint, use_container_width=True)
        
        # Légende des compounds visible
        with st.expander("🛞 Légende des compounds", expanded=False):
            cols = st.columns(5)
            compounds_legend = [
                ("Soft", "#FF3333", "Le plus rapide, dégrade vite"),
                ("Medium", "#FFCC33", "Compromis vitesse/dégradation"),
                ("Hard", "#F0F0F0", "Le plus durable, moins de grip"),
                ("Intermediate", "#33B53C", "Pluie légère / piste humide"),
                ("Wet", "#4D7BC2", "Pluie soutenue"),
            ]
            for col, (name, color_, desc) in zip(cols, compounds_legend):
                col.markdown(f"<div style='background-color:{color_}; padding:6px 10px; border-radius:5px; color:#000; font-weight:bold; text-align:center'>{name}</div>", unsafe_allow_html=True)
                col.caption(desc)
        
        st.markdown("---")
        st.markdown("#### 📊 Statistiques par stint")
        
        def compute_stint_stats(laps_drv, drv):
            """Calcule les stats clés de chaque stint."""
            if "Stint" not in laps_drv.columns or len(laps_drv) == 0:
                return []
            stats = []
            for stint_num, stint_laps in laps_drv.groupby("Stint"):
                if len(stint_laps) < 1:
                    continue
                lt = stint_laps["LapTimeSeconds"].values
                # Régression linéaire pour la dégradation
                if len(lt) >= 3:
                    n = np.arange(len(lt))
                    slope, _ = np.polyfit(n, lt, 1)
                    degrad = f"{slope*1000:+.1f} ms/tour"
                else:
                    degrad = "—"
                compound = str(stint_laps["Compound"].iloc[0]) if "Compound" in stint_laps else "—"
                stats.append({
                    "Pilote": drv,
                    "Stint": int(stint_num),
                    "Compound": compound,
                    "Tours": len(stint_laps),
                    "Best": f"{lt.min():.3f}s",
                    "Moyenne": f"{lt.mean():.3f}s",
                    "Écart-type": f"{lt.std():.3f}s" if len(lt) > 1 else "—",
                    "Dégradation": degrad,
                })
            return stats
        
        all_stats = compute_stint_stats(laps_d1_s, d1) + compute_stint_stats(laps_d2_s, d2)
        if all_stats:
            df_stints = pd.DataFrame(all_stats)
            st.dataframe(df_stints, use_container_width=True, hide_index=True)
            
            with st.expander("💡 Comment lire ces stats"):
                st.markdown(f"""
                - **Best** : meilleur tour du stint — révèle la **pace pure** quand les pneus sont au top
                - **Moyenne** : pace réelle sur l'ensemble du stint — plus représentative pour comparer
                - **Écart-type** : indicateur de **consistance**. Bas = pilote métronome (Hamilton, Russell typiquement). Élevé = pilote qui prend des risques ou se bat avec sa voiture
                - **Dégradation** : pente de la régression linéaire (ms perdues par tour qui passe). 
                    - **< +30 ms/tour** : excellente gestion pneus (Verstappen, Hamilton historiquement)
                    - **+30 à +80 ms/tour** : normal
                    - **> +80 ms/tour** : pilote qui en demande trop à ses pneus, ou stratégie risquée
                
                **Crois ces deux infos** : un pilote avec un meilleur **Best** mais une moins bonne **Moyenne** est rapide quand il pousse mais ne tient pas — il sera défavorisé sur des longues séquences. C'est typiquement le profil "qualif > course".
                """)
        
        # --- Bonus : différence de pace par tour ---
        if len(laps_d1_s) > 5 and len(laps_d2_s) > 5:
            st.markdown("---")
            st.markdown("#### ⚔️ Différence de pace tour par tour")
            
            # Aligne les deux pilotes sur les tours communs
            common = pd.merge(
                laps_d1_s[["LapNumber", "LapTimeSeconds"]].rename(columns={"LapTimeSeconds": f"t_{d1}"}),
                laps_d2_s[["LapNumber", "LapTimeSeconds"]].rename(columns={"LapTimeSeconds": f"t_{d2}"}),
                on="LapNumber", how="inner",
            )
            common["delta"] = common[f"t_{d1}"] - common[f"t_{d2}"]
            
            if len(common) > 0:
                fig_delta_stint = go.Figure()
                fig_delta_stint.add_trace(go.Bar(
                    x=common["LapNumber"], y=common["delta"],
                    marker_color=[c2 if d > 0 else c1 for d in common["delta"]],
                    name=f"Δ {d1} − {d2}",
                    hovertemplate=f"Tour %{{x}}<br>Δ: %{{y:+.3f}}s<extra></extra>",
                ))
                fig_delta_stint.add_hline(y=0, line=dict(color="white", width=0.8))
                fig_delta_stint.update_layout(
                    height=350, template="plotly_dark",
                    xaxis_title="Tour",
                    yaxis_title=f"Δ {d1} − {d2} (s)",
                    title=f"Barres positives = {d2} plus rapide · Barres négatives = {d1} plus rapide",
                )
                st.plotly_chart(fig_delta_stint, use_container_width=True)

# --- TAB 6 : RADAR ---
with tab6:
    st.markdown("Compare jusqu'à 6 pilotes en visu radar. Idéal pour repérer des archétypes opposés.")
    
    default_radar = [d for d in [d1, d2, "NOR", "HAM", "ALO"] if d in drivers_in_session][:5]
    drivers_radar = st.multiselect(
        "Pilotes",
        options=drivers_in_session,
        default=default_radar,
        max_selections=6,
        format_func=lambda x: driver_full.get(x, x),
    )
    
    if len(drivers_radar) < 2:
        st.warning("Sélectionne au moins 2 pilotes.")
    else:
        def sig_for(drv):
            lap = session.laps.pick_drivers(drv).pick_fastest()
            if lap is None or pd.isna(lap.get("LapTime")):
                return None
            tel = lap.get_car_data().add_distance()
            return {
                "Pilote": drv,
                "Vmax": float(tel["Speed"].max()),
                "V_min courbes": float(tel.loc[tel["Speed"] < tel["Speed"].quantile(0.30), "Speed"].median()),
                "Full throttle %": float((tel["Throttle"] >= 99).mean() * 100),
                "Coast time %": float(((tel["Throttle"] < 5) & (tel["Brake"] == 0)).mean() * 100),
                "Brake %": float((tel["Brake"] > 0).mean() * 100),
                "Throttle ramp-up": float(np.diff(tel["Throttle"].values)[np.diff(tel["Throttle"].values) > 0].mean() or 0),
            }
        
        sigs = [s for s in (sig_for(d) for d in drivers_radar) if s is not None]
        if not sigs:
            st.error("Aucun pilote avec données valides.")
        else:
            df_m = pd.DataFrame(sigs).set_index("Pilote")
            # Normalisation 0-1
            df_n = (df_m - df_m.min()) / (df_m.max() - df_m.min() + 1e-9)
            
            fig = go.Figure()
            for drv in df_n.index:
                vals = df_n.loc[drv].tolist()
                vals += vals[:1]
                labels = df_n.columns.tolist() + [df_n.columns[0]]
                fig.add_trace(go.Scatterpolar(
                    r=vals, theta=labels, fill="toself",
                    name=drv, line=dict(color=driver_color(drv), width=2),
                    opacity=0.7,
                ))
            fig.update_layout(
                height=600, template="plotly_dark",
                polar=dict(radialaxis=dict(visible=True, range=[0, 1], showticklabels=False)),
                title="Signatures de style — comparaison normalisée",
            )
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("Valeurs brutes"):
                st.dataframe(df_m.round(2), use_container_width=True)

# ============== HELPERS ANALYSE VIRAGES ==============
def _corner_bounds(corner_dists, lap_len):
    """Bornes de fenêtre par virage : mi-distance avec les virages voisins, cap à 600 m."""
    bounds = []
    n = len(corner_dists)
    for i, d in enumerate(corner_dists):
        prev_b = (corner_dists[i - 1] + d) / 2 if i > 0 else max(0.0, d - 600)
        next_b = (d + corner_dists[i + 1]) / 2 if i < n - 1 else min(lap_len, d + 600)
        prev_b = max(prev_b, d - 600)
        next_b = min(next_b, d + 600)
        bounds.append((prev_b, next_b))
    return bounds


def analyze_corner(tel, apex_d, prev_b, next_b):
    """Analyse un virage : point de freinage, décélération max, vitesse mini, remise des gaz.

    - brake_before : m avant l'apex où le freinage commence (petit = freine tard). None si à fond.
    - max_g : décélération maxi (g) sur la zone de freinage.
    - vmin / vmin_d : vitesse mini autour de l'apex et sa position.
    - throttle_after : m après l'apex où le throttle repasse >=90 % soutenu (négatif possible).
    """
    w = tel[(tel["Distance"] >= prev_b) & (tel["Distance"] <= next_b)]
    if len(w) < 5:
        return None
    res = {}
    aw = w[(w["Distance"] >= apex_d - 120) & (w["Distance"] <= apex_d + 120)]
    if aw.empty:
        aw = w
    i_min = aw["Speed"].idxmin()
    res["vmin"] = float(aw.loc[i_min, "Speed"])
    vmin_d = float(aw.loc[i_min, "Distance"])
    res["vmin_d"] = vmin_d

    # Point de freinage : dernier déclenchement (0->1) avant le point de vitesse mini
    pre = w[w["Distance"] <= vmin_d]
    res["brake_before"] = None
    res["max_g"] = None
    if len(pre):
        brk = (pre["Brake"].astype(float) > 0).astype(int).values
        if brk.any():
            onsets = np.where(np.diff(brk, prepend=0) == 1)[0]
            if len(onsets):
                onset_d = float(pre["Distance"].iloc[onsets[-1]])
            else:
                onset_d = float(pre["Distance"].iloc[0])  # freinait déjà (chicane)
            res["brake_before"] = apex_d - onset_d
            zone = pre[pre["Distance"] >= onset_d]
            if len(zone) >= 3:
                v = zone["Speed"].rolling(3, center=True, min_periods=1).mean().values / 3.6
                t = zone["Time"].dt.total_seconds().values
                dt = np.diff(t)
                ok = dt > 1e-3
                if ok.any():
                    dec = -np.diff(v)[ok] / dt[ok]
                    res["max_g"] = float(np.clip(dec.max() / 9.81, 0, 7))

    # Remise des gaz : premier passage soutenu >=90 % après le point de vitesse mini
    post = w[w["Distance"] >= vmin_d]
    res["throttle_after"] = None
    thr = post["Throttle"].values
    for j in range(len(thr)):
        if thr[j] >= 90 and thr[j:j + 5].min() >= 80:
            res["throttle_after"] = float(post["Distance"].iloc[j]) - apex_d
            break
    return res


def corner_class(vmin):
    if pd.isna(vmin):
        return "?"
    if vmin < 120:
        return "Lent"
    if vmin <= 200:
        return "Moyen"
    return "Rapide"


@st.cache_data(show_spinner=False, ttl=24 * 3600)
def compute_race_gaps(year, gp, ses):
    """Écarts avant/arrière au passage de la ligne, pour chaque pilote et chaque tour."""
    sess = load_session(year, gp, ses)
    laps = sess.laps[["Driver", "LapNumber", "Position", "Time", "PitInTime", "PitOutTime"]].copy()
    laps = laps.dropna(subset=["Position", "Time"])
    if laps.empty:
        return pd.DataFrame()
    rows = []
    for _, g in laps.groupby("LapNumber"):
        g = g.sort_values("Position")
        t = g["Time"].dt.total_seconds().values
        gap_ahead = np.full(len(g), np.nan)
        gap_behind = np.full(len(g), np.nan)
        if len(g) > 1:
            gap_ahead[1:] = t[1:] - t[:-1]
            gap_behind[:-1] = t[1:] - t[:-1]
        rows.append(g.assign(GapAhead=gap_ahead, GapBehind=gap_behind))
    return pd.concat(rows, ignore_index=True)


@st.cache_data(show_spinner=False, ttl=24 * 3600)
def field_corner_profile(year, gp, ses):
    """Vitesse mini par virage pour le tour rapide de chaque pilote du plateau, + Vmax."""
    sess = load_session(year, gp, ses)
    ci = sess.get_circuit_info()
    if ci is None or ci.corners is None or len(ci.corners) == 0:
        return None
    corners = ci.corners.sort_values("Distance").reset_index(drop=True)
    labels = [f"T{int(r['Number'])}{r['Letter']}" for _, r in corners.iterrows()]
    speeds, vmax = {}, {}
    for drv in sess.laps["Driver"].unique():
        try:
            lap = sess.laps.pick_drivers(drv).pick_fastest()
            if lap is None or pd.isna(lap.get("LapTime")):
                continue
            tel = lap.get_car_data().add_distance()
            lap_len = float(tel["Distance"].max())
            bounds = _corner_bounds(corners["Distance"].tolist(), lap_len)
            vals = []
            for (pb, nb), d in zip(bounds, corners["Distance"]):
                aw = tel[(tel["Distance"] >= max(pb, d - 120)) & (tel["Distance"] <= min(nb, d + 120))]
                vals.append(float(aw["Speed"].min()) if len(aw) else np.nan)
            speeds[drv] = vals
            vmax[drv] = float(tel["Speed"].max())
        except Exception:
            continue
    if not speeds:
        return None
    return pd.DataFrame(speeds, index=labels), pd.Series(vmax)


# --- TAB CORNERS : VIRAGE PAR VIRAGE ---
with tab_corners:
    st.markdown(
        f"Pour chaque virage : **où** chacun commence à freiner, à quelle intensité, et **quand** il remet "
        f"les gaz. C'est ici qu'on voit objectivement qui freine tard et qui sort fort. "
        f"Analyse basée sur les tours sélectionnés dans la barre latérale."
    )
    ci = session.get_circuit_info()
    if ci is None or ci.corners is None or len(ci.corners) == 0:
        st.info("FastF1 ne fournit pas la position des virages pour ce circuit.")
    else:
        cdf = ci.corners.sort_values("Distance").reset_index(drop=True)
        lap_len = float(min(tel1["Distance"].max(), tel2["Distance"].max()))
        bounds = _corner_bounds(cdf["Distance"].tolist(), lap_len)

        rows = []
        for (pb, nb), (_, c) in zip(bounds, cdf.iterrows()):
            r1 = analyze_corner(tel1, float(c["Distance"]), pb, nb)
            r2 = analyze_corner(tel2, float(c["Distance"]), pb, nb)
            if r1 is None or r2 is None:
                continue
            rows.append({
                "Virage": f"T{int(c['Number'])}{c['Letter']}",
                "Type": corner_class(max(r1["vmin"], r2["vmin"])),
                "frein1": r1["brake_before"], "frein2": r2["brake_before"],
                "g1": r1["max_g"], "g2": r2["max_g"],
                "vmin1": r1["vmin"], "vmin2": r2["vmin"],
                "gaz1": r1["throttle_after"], "gaz2": r2["throttle_after"],
            })

        if not rows:
            st.warning("Impossible d'analyser les virages sur ces tours.")
        else:
            dfc = pd.DataFrame(rows)
            for col in ["frein1", "frein2", "g1", "g2", "vmin1", "vmin2", "gaz1", "gaz2"]:
                dfc[col] = pd.to_numeric(dfc[col], errors="coerce")
            dfc["dfrein"] = dfc["frein2"] - dfc["frein1"]   # > 0 = D1 freine plus tard
            dfc["dgaz"] = dfc["gaz2"] - dfc["gaz1"]         # > 0 = D1 remet les gaz plus tôt

            # --- Verdicts synthétiques ---
            vf = dfc.dropna(subset=["dfrein"])
            vg = dfc.dropna(subset=["dgaz"])
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                st.markdown("##### 🛑 Freinage")
                if len(vf):
                    l1 = int((vf["dfrein"] > 5).sum())
                    l2 = int((vf["dfrein"] < -5).sum())
                    m = vf["dfrein"].mean()
                    leader = d1 if m > 0 else d2
                    st.markdown(
                        f"- **{d1}** freine plus tard sur **{l1}** virage(s), **{d2}** sur **{l2}** "
                        f"(égalité ±5 m sur les autres)\n"
                        f"- En moyenne, **{leader}** retarde son freinage de **{abs(m):.0f} m**"
                    )
                else:
                    st.markdown("Pas de virage freiné comparable.")
            with col_v2:
                st.markdown("##### 🚀 Remise des gaz")
                if len(vg):
                    e1 = int((vg["dgaz"] > 5).sum())
                    e2 = int((vg["dgaz"] < -5).sum())
                    m = vg["dgaz"].mean()
                    leader = d1 if m > 0 else d2
                    st.markdown(
                        f"- **{d1}** remet les gaz plus tôt sur **{e1}** virage(s), **{d2}** sur **{e2}**\n"
                        f"- En moyenne, **{leader}** repasse à fond **{abs(m):.0f} m** plus tôt"
                    )
                else:
                    st.markdown("Pas de remise des gaz comparable.")

            # --- Agrégats par type de virage ---
            agg = dfc.groupby("Type").agg(
                n=("Virage", "count"),
                d_frein_moy=("dfrein", "mean"),
                d_gaz_moy=("dgaz", "mean"),
            ).reindex(["Lent", "Moyen", "Rapide"]).dropna(how="all")
            agg = agg.rename(columns={
                "n": "Virages",
                "d_frein_moy": f"Δ frein moy (m, + = {d1} plus tard)",
                "d_gaz_moy": f"Δ gaz moy (m, + = {d1} plus tôt)",
            })
            st.markdown("##### Par type de virage")
            st.dataframe(agg.round(1), use_container_width=True)

            # --- Graphique par virage ---
            fig_c = make_subplots(
                rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.10,
                subplot_titles=(
                    f"Δ point de freinage (m) — barre couleur {d1} = {d1} freine plus tard",
                    f"Δ remise des gaz (m) — barre couleur {d1} = {d1} remet plus tôt",
                ),
            )
            fig_c.add_trace(go.Bar(
                x=dfc["Virage"], y=dfc["dfrein"],
                marker_color=[c1 if (pd.notna(v) and v > 0) else c2 for v in dfc["dfrein"]],
                hovertemplate="%{x}<br>Δ frein: %{y:+.0f} m<extra></extra>",
            ), row=1, col=1)
            fig_c.add_trace(go.Bar(
                x=dfc["Virage"], y=dfc["dgaz"],
                marker_color=[c1 if (pd.notna(v) and v > 0) else c2 for v in dfc["dgaz"]],
                hovertemplate="%{x}<br>Δ gaz: %{y:+.0f} m<extra></extra>",
            ), row=2, col=1)
            fig_c.add_hline(y=0, line=dict(color="white", width=0.8), row=1, col=1)
            fig_c.add_hline(y=0, line=dict(color="white", width=0.8), row=2, col=1)
            fig_c.update_layout(height=550, template="plotly_dark", showlegend=False,
                                margin=dict(t=60, b=20, l=20, r=20))
            st.plotly_chart(fig_c, use_container_width=True)

            # --- Tableau détaillé ---
            disp = pd.DataFrame({
                "Virage": dfc["Virage"], "Type": dfc["Type"],
                f"Frein {d1} (m)": dfc["frein1"].round(0),
                f"Frein {d2} (m)": dfc["frein2"].round(0),
                f"g max {d1}": dfc["g1"].round(1),
                f"g max {d2}": dfc["g2"].round(1),
                f"Vmin {d1}": dfc["vmin1"].round(0),
                f"Vmin {d2}": dfc["vmin2"].round(0),
                f"Gaz {d1} (m)": dfc["gaz1"].round(0),
                f"Gaz {d2} (m)": dfc["gaz2"].round(0),
            })
            with st.expander("📋 Tableau détaillé par virage"):
                st.dataframe(disp, use_container_width=True, hide_index=True,
                             height=min(38 * (len(disp) + 1) + 3, 600))
                st.caption(
                    "**Frein** = distance avant l'apex où le freinage démarre (petit = freine tard). "
                    "**Gaz** = distance après l'apex où le throttle repasse ≥90 % (petit ou négatif = sort fort). "
                    "**—** = virage pris à fond. ⚠️ Échantillonnage télémétrie ~4-5 Hz : précision ±10-15 m "
                    "à haute vitesse — les écarts <5 m ne sont pas significatifs, les tendances sur "
                    "l'ensemble du tour le sont."
                )

# --- TAB CRAFT : ATTAQUE / DÉFENSE ---
with tab_craft:
    ses_type = st.session_state.session_type
    if ses_type not in ("R", "S"):
        st.info("🥊 Le race craft (attaque, défense, dépassements) ne se mesure qu'en **course** ou en "
                "**sprint**. Charge une session R ou S pour cet onglet.")
    else:
        st.markdown(
            "Qui attaque, qui défend, qui concrétise. Basé sur les écarts au passage de la ligne, "
            "tour par tour, pour toute la course."
        )
        with st.spinner("Calcul des écarts tour par tour…"):
            gaps = compute_race_gaps(st.session_state.year, st.session_state.gp_name, ses_type)
        if gaps.empty:
            st.warning("Pas de données de position exploitables pour cette session.")
        else:
            def craft_metrics(drv):
                g = gaps[gaps["Driver"] == drv].sort_values("LapNumber").reset_index(drop=True)
                if g.empty:
                    return None
                g["NextPos"] = g["Position"].shift(-1)
                pit = g["PitInTime"].notna() | g["PitOutTime"].notna()
                clean = (~pit) & (~pit.shift(-1, fill_value=False)) & g["NextPos"].notna()
                press = clean & (g["GapBehind"] < 1.0)
                held = press & (g["NextPos"] <= g["Position"])
                attack = clean & (g["GapAhead"] < 1.0)
                conv = attack & (g["NextPos"] < g["Position"])
                gained = clean & (g["NextPos"] < g["Position"])
                lost = clean & (g["NextPos"] > g["Position"])
                return {
                    "pos": g[["LapNumber", "Position"]],
                    "press": int(press.sum()), "held": int(held.sum()),
                    "attack": int(attack.sum()), "conv": int(conv.sum()),
                    "gained": int(gained.sum()), "lost": int(lost.sum()),
                }

            m1, m2 = craft_metrics(d1), craft_metrics(d2)
            if m1 is None or m2 is None:
                st.warning("Un des deux pilotes n'a pas de données de course.")
            else:
                # Évolution des positions
                fig_p = go.Figure()
                for m, drv, col in [(m1, d1, c1), (m2, d2, c2)]:
                    fig_p.add_trace(go.Scatter(
                        x=m["pos"]["LapNumber"], y=m["pos"]["Position"],
                        mode="lines+markers", name=drv,
                        line=dict(color=col, width=2.5), marker=dict(size=5),
                        hovertemplate=f"<b>{drv}</b><br>Tour %{{x}}<br>P%{{y:.0f}}<extra></extra>",
                    ))
                fig_p.update_layout(
                    height=400, template="plotly_dark",
                    xaxis_title="Tour", yaxis_title="Position",
                    yaxis=dict(autorange="reversed", dtick=1),
                    legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
                )
                st.plotly_chart(fig_p, use_container_width=True)

                # Métriques attaque / défense
                def pct(a, b):
                    return f"{a}/{b} ({a / b * 100:.0f} %)" if b else "—"

                col_a, col_b = st.columns(2)
                for col, m, drv in [(col_a, m1, d1), (col_b, m2, d2)]:
                    with col:
                        st.markdown(f"#### {drv}")
                        st.metric("Tours sous pression (<1 s derrière)", m["press"])
                        st.metric("Défenses réussies", pct(m["held"], m["press"]))
                        st.metric("Tours à l'attaque (<1 s devant)", m["attack"])
                        st.metric("Attaques converties en dépassement", pct(m["conv"], m["attack"]))
                        st.metric("Positions gagnées / perdues en piste", f"+{m['gained']} / −{m['lost']}")

                with st.expander("💡 Comment lire (et limites)"):
                    st.markdown("""
                    - **Défenses réussies élevées** (>80 %) = pilote solide sous pression, place bien sa voiture.
                    - **Conversion d'attaque élevée** = agressif ET efficace. Beaucoup de tours à l'attaque
                      avec peu de conversions = suiveur qui n'ose pas, ou voiture sans top speed.
                    - **Positions gagnées/perdues** : hors tours d'arrêt du pilote lui-même.

                    ⚠️ **Limites** : écarts mesurés au passage de la ligne uniquement ; les arrêts des
                    *autres* pilotes ne sont pas neutralisés (un undercut compte comme un dépassement) ;
                    le trafic retardataire peut générer de la fausse "pression". À lire comme des
                    **tendances**, pas une vérité au tour près.
                    """)

# --- TAB FIT : AUTO VS CIRCUIT ---
with tab_fit:
    st.markdown(
        "La voiture aime-t-elle ce tracé ? Chaque pilote est comparé au **meilleur du plateau** "
        "virage par virage (tours rapides), agrégé par type de virage, puis croisé avec la "
        "typologie du circuit."
    )
    with st.spinner("Analyse du plateau complet (peut prendre quelques secondes)…"):
        profile = field_corner_profile(
            st.session_state.year, st.session_state.gp_name, st.session_state.session_type
        )
    if profile is None:
        st.info("Pas de données virages disponibles pour ce circuit/session.")
    else:
        df_speeds, vmax_all = profile
        best = df_speeds.max(axis=1)
        classes = best.apply(corner_class)
        counts = classes.value_counts().reindex(["Lent", "Moyen", "Rapide"]).fillna(0).astype(int)
        dominant = counts.idxmax()

        dominant_label = {"Lent": "lente", "Moyen": "moyenne", "Rapide": "rapide"}[dominant]
        st.markdown(
            f"**Typologie {ev['Location']}** : {counts.get('Lent', 0)} lent(s) · "
            f"{counts.get('Moyen', 0)} moyen(s) · {counts.get('Rapide', 0)} rapide(s) "
            f"→ dominante **{dominant_label}**"
        )

        fig_f = go.Figure()
        verdicts = []
        for drv, col in [(d1, c1), (d2, c2)]:
            if drv not in df_speeds.columns:
                st.warning(f"Pas de tour rapide exploitable pour {drv}.")
                continue
            deficit = best - df_speeds[drv]
            agg = deficit.groupby(classes).mean().reindex(["Lent", "Moyen", "Rapide"])
            fig_f.add_trace(go.Bar(
                x=agg.index, y=agg.values, name=drv, marker_color=col,
                hovertemplate=f"<b>{drv}</b><br>%{{x}} : −%{{y:.1f}} km/h vs meilleur<extra></extra>",
            ))
            valid = agg.dropna()
            if len(valid) >= 2:
                strong, weak = valid.idxmin(), valid.idxmax()
                fit = ("✅ la typologie du circuit lui convient" if strong == dominant
                       else "❌ typologie défavorable" if weak == dominant
                       else "➖ typologie neutre pour lui")
                vmax_def = vmax_all.max() - vmax_all.get(drv, np.nan)
                verdicts.append(
                    f"**{drv}** — à l'aise en virages **{strong.lower()}s** "
                    f"(−{valid[strong]:.1f} km/h vs meilleur), en retrait en **{weak.lower()}s** "
                    f"(−{valid[weak]:.1f}) · Vmax : −{vmax_def:.0f} km/h vs meilleur → {fit}"
                )

        fig_f.update_layout(
            height=420, template="plotly_dark", barmode="group",
            yaxis_title="Déficit moyen vs meilleur du plateau (km/h)",
            xaxis_title="Type de virage",
            legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
        )
        st.plotly_chart(fig_f, use_container_width=True)
        for v in verdicts:
            st.markdown(v)

        with st.expander("💡 Comment lire (et limites)"):
            st.markdown("""
            - **Déficit faible en virages rapides** = voiture efficace en appui aéro.
            - **Déficit faible en virages lents** = bon grip mécanique / traction.
            - **Vmax proche du meilleur** = peu de traînée ou moteur fort.
            - Croisé avec la dominante du circuit : une voiture forte en appui sur un tracé
              à dominante rapide (Suzuka, Silverstone) = circuit qui lui convient.

            ⚠️ Ce benchmark mélange **voiture + pilote**. Pour isoler le pilote, l'astuce
            classique : sélectionner les deux **coéquipiers** dans la barre latérale
            (même voiture) et regarder l'onglet *Virage par virage*.
            """)

# ============== FOOTER ==============
st.markdown("---")
st.caption("Données : F1 Live Timing via FastF1 · Couleurs équipes 2026 · Style decoder by you")
