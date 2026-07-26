"""Analyse F1 — Streamlit App
=============================
Interface interactive pour analyser les styles de pilotage en F1.

Pour lancer :
    pip install -U streamlit fastf1 plotly pandas numpy scipy
    streamlit run app.py

L'app s'ouvre automatiquement dans ton navigateur (http://localhost:8501).

Prérequis : Streamlit >= 1.46 (utilise width="stretch").
Si tu es bloqué sur une version plus ancienne : remplace width="stretch"
par use_container_width=True.

Changements vs version précédente
---------------------------------
- DATA session.load(weather=True, messages=True) — nouvelles données exploitées :
       · bandeau météo (air, piste, vent, pluie) + durée de roulage dans
         l'en-tête de session ;
       · périodes SC/VSC (statut piste officiel) et pluie surlignées sur le
         graphe d'évolution course, température de piste en axe secondaire ;
       · le filtre outliers exclut d'abord les tours sous SC/VSC/rouge
         (TrackStatus) avant le seuil médiane ;
       · expander « Direction de course » (drapeaux, SC, pénalités, tours
         supprimés) dans l'Overview ; pénalités par pilote dans Race craft ;
       · motif officiel des tours supprimés (DeletedReason) dans le recap.
       Au passage FIX : FastF1 ne renseigne la colonne Deleted que si
       messages=True — l'exclusion des tours supprimés des records ne
       fonctionnait donc jamais avant.
- DATA Canaux RPM et DRS dans l'Overlay (6 sous-graphes) ; « DRS ouvert »
       disponible comme coloration de la Vue circuit.
- DATA Overview enrichi : Δ Grille (places gagnées/perdues vs départ,
       PL = pit lane), progression Q1→Q2→Q3 en qualif, arrêts aux stands
       (temps pit lane entrée→sortie), championnat constructeurs
       avant/après session.
- FIX  Chargement de session impossible depuis Streamlit Cloud : F1 filtre
       les IP de datacenter et renvoie **HTTP 403** sur tous les flux de
       livetiming.formula1.com (diagnostiqué en prod). `select_data_host()`
       sonde les deux serveurs au démarrage (cache 1 h) et bascule
       `fastf1._api.base_url` sur le miroir FastF1 quand le principal est
       bloqué : plus aucune requête ne part vers le serveur qui refuse.
       En complément, `fetch_page` est enveloppé pour rejouer aussi les
       échecs de CONNEXION sur le miroir (FastF1 ne bascule nativement que
       sur une réponse HTTP >= 400 : un timeout court-circuitait le repli).
       En cas d'échec malgré tout : panneau 🩺 Diagnostic (warnings FastF1
       capturés + sondage d'un vrai fichier de données sur chaque serveur)
       et boutons Réessayer / Vider le cache.
- NOUVEAU Overview course : expander « 📈 Position des pilotes par tour » —
  évolution des positions tour par tour de tout le plateau (grille de départ
  en tour 0), filtrable par multiselect, replié par défaut.
- DATA 📻 Radios d'équipe (flux TeamRadio du live timing) : clips MP3
       officiels des « meilleurs moments », jouables dans l'app avec pilote,
       tour approximatif (via LapStartDate) et heure — expander dans
       l'Overview (filtrable par pilote) + onglet Radios des deux pilotes
       comparés sur la page Style. Miroir fastf1 en secours, repli propre
       si le flux est indisponible (fréquent avant 2022).
- DATA Portraits officiels des pilotes (HeadshotUrl) sur la page Style ;
       ° = pneus rodés (FreshTyre) ; ⚠ = chrono jugé imprécis (IsAccurate)
       dans le sélecteur de tours.
- Vue circuit / battle map / heatmap : tracés orientés comme à la TV
  (rotation officielle du circuit) + numéros de virage sur la carte.
- Couleurs d'équipe : fallback vers le référentiel officiel fastf1.plotting
  pour toute équipe absente de la palette locale.
- FIX  UX mobile : plus de clavier virtuel à l'ouverture des menus
       déroulants (inputs des selectbox passés en readonly + inputmode="none"
       en mode compact ; le menu s'ouvre normalement, seule la recherche par
       frappe — inutile au doigt — disparaît).
- RENOMMAGE : l'app s'appelle désormais « Analyse F1 » ; la page d'accueil
  « Timing session » devient « Overview session ».
- NOUVEAU écran de bienvenue : à la première visite, les réglages (saison,
  GP, session) sont aussi proposés au centre de la page — plus besoin de
  trouver la barre latérale (repliée sur mobile) pour démarrer. Ils restent
  synchronisés avec ceux de la sidebar.
- FIX  Garde pilote 1 ≠ pilote 2 : le doublon créait un index dupliqué qui
       cassait l'onglet Signatures et la pace tour par tour.
- FIX  get_lap_options : pick_fastest() peut renvoyer None (ex. tous les
       tours supprimés pour track limits) → fallback sur le tour le plus
       rapide par idxmin.
- FIX  Évolution course : le filtre outliers s'applique aussi aux stats de
       stint et à la pace tour par tour (avant : graphique seulement, les
       moyennes/dégradation restaient polluées par les tours sous SC).
- Couleurs des équipes historiques 2018-2020 (Renault, Toro Rosso, Alfa
  Romeo, Racing Point, Force India) + texte des badges en noir sur fonds
  clairs (lisibilité, ex. jaune Renault).
- Brake et nGear tracés en marches (line_shape="hv") au lieu de rampes.
- Radar : tirets distincts par pilote → deux coéquipiers (même couleur
  équipe) restent discernables.
- Saison par défaut : 2026 (saison en cours).
- REFONTE en deux pages via st.navigation (menu en haut de la sidebar ;
  sur mobile, il s'ouvre par l'icône en haut à gauche) :
  · 📊 Timing session (accueil) : tableau récap façon écran livetiming —
    badges couleur équipe, intervalles/écarts (classement officiel en
    course/sprint), pneus (âge + compound), best lap, dernier tour bouclé
    + secteurs, meilleurs secteurs individuels ; fonds violet (record
    session) / vert (record perso). Rendu HTML mono. Les mini-secteurs
    n'existent pas en post-session (flux live SignalR) → non affichés.
  · 🎨 Style de pilotage : tout l'existant (sélection pilotes + onglets).
- FIX  Tableaux flous sur mobile : st.dataframe dessine dans un canvas
       (Glide Data Grid) → rendu baveux sur écrans Retina. En mode compact,
       la feuille des temps et le recap tour par tour sont rendus en HTML
       natif (texte net), avec en-têtes collants et conteneur scrollable.
- NOUVEAU mode 📱 Affichage compact : auto-détecté via user-agent (forçable
  dans la sidebar). Libère le scroll tactile sur les graphiques (dragmode
  désactivé — sinon Plotly capture le geste et bloque le défilement de la
  page), masque la modebar, empile la vue circuit et le recap tour par tour,
  et allège la feuille des temps (codes pilotes, colonnes essentielles).
- NOUVEAU onglet 📋 Feuille des temps (façon écran de timing) : meilleurs
  tours + meilleurs secteurs individuels (violet = record session, vert =
  record perso), tour théorique et Δ vs réel, vitesses de pointe, et recap
  tour par tour des deux pilotes (IN/OUT, tours supprimés barrés).
- NOUVEAU onglet ⭕ Diagramme g-g (cercle de friction) : accélérations
  latérale/longitudinale reconstruites depuis X/Y + vitesse (Savitzky-Golay),
  nuages + enveloppes p95 par pilote, cercles de référence 1-5 g, métriques
  g max freinage / g max latéral / % trail-braking.
- FIX  Heatmap de gain de temps : delta_time() renvoie du car data SANS X/Y
       → le gain est projeté (np.interp) sur la télémétrie complète de lap1.
       Gradient calculé par rapport à la distance → unités en ms/m,
       comparables partout sur le tour.
- FIX  Bouton "Charger la session" : les paramètres ne s'appliquent qu'au clic
       (avant : tout changement de widget rechargeait sans clic). Un hint
       s'affiche dans la sidebar si les widgets diffèrent de la session chargée.
- FIX  Filtre in/out-laps de l'onglet Évolution course : `&` au lieu de `|`
       (l'ancien filtre ne retirait quasiment rien).
- FIX  Radar : garde du throttle ramp-up (mean d'un array vide → nan, et nan
       est truthy, donc `or 0` ne protégeait rien).
- Brake (booléen chez FastF1) converti en int pour tous les tracés.
- get_circuit_info() appelé une seule fois (plus de warning doublé).
- session.load(weather=False, messages=False) → plus rapide, moins de RAM.
- max_entries=3 sur le cache de session (évite l'OOM sur Streamlit Cloud 1 Go).
- Garde sur les temps de secteur manquants (NaT).
- Les zones des briefings circuit servent de presets dans l'onglet Zoom.
- Top zones de gain dédupliquées (>=150 m d'écart) + virage le plus proche.
- use_container_width (déprécié) → width="stretch".
- Suppression de l'entrée morte "Monaco Grand Prix de Monaco".
"""
import contextlib
import logging
import os

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.ndimage import uniform_filter1d
from scipy.signal import savgol_filter

import fastf1
from fastf1.utils import delta_time

# ============== CONFIG ==============
st.set_page_config(
    page_title="Analyse F1",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="auto",  # repliée sur mobile, dépliée sur desktop
)

os.makedirs("cache_f1", exist_ok=True)
fastf1.Cache.enable_cache("cache_f1")


# ============== ROBUSTESSE RÉSEAU FASTF1 ==============
def _patch_fastf1_mirror_fallback():
    """FastF1 ne bascule sur son miroir QUE si le serveur F1 répond avec un code
    HTTP >= 400 (`fetch_page` dans `fastf1._api`). Si la connexion elle-même
    échoue — timeout, connexion réinitialisée, DNS, filtrage réseau côté
    hébergeur — l'exception remonte et le miroir n'est jamais essayé : la
    session se charge alors totalement vide. On enveloppe `fetch_page` pour
    rejouer aussi ces échecs-là sur le miroir.

    Les fonctions internes de FastF1 appellent `fetch_page` via le global du
    module (résolu à l'appel) : remplacer l'attribut suffit à couvrir tous les
    flux (laps, télémétrie, météo, messages…)."""
    api = fastf1._api
    if getattr(api, "_mirror_fallback_patched", False):
        return
    original = api.fetch_page

    def fetch_page_with_mirror(path, name):
        try:
            return original(path, name)
        except Exception:
            saved = api.base_url
            api.base_url = api.base_url_mirror  # relu à l'appel par fetch_page
            try:
                return original(path, name)
            except Exception:
                return None  # même comportement qu'un échec FastF1 normal
            finally:
                api.base_url = saved

    api.fetch_page = fetch_page_with_mirror
    api._mirror_fallback_patched = True


_patch_fastf1_mirror_fallback()

F1_HOST = fastf1._api.base_url            # serveur officiel
F1_MIRROR = fastf1._api.base_url_mirror   # miroir communautaire FastF1
_HOST_PROBE = "/static/Index.json"        # petit fichier réel, présent sur les deux


def _probe_host(base, timeout=12):
    """Code HTTP du serveur pour un vrai fichier de données, ou nom de
    l'exception si la connexion échoue."""
    import requests

    try:
        return requests.get(base + _HOST_PROBE, timeout=timeout,
                            headers=fastf1._api.headers).status_code
    except Exception as exc:
        return type(exc).__name__


@st.cache_resource(show_spinner=False, ttl=3600)
def select_data_host():
    """Choisit le serveur de données utilisé par toute l'app.

    F1 filtre les IP de datacenter : depuis Streamlit Cloud,
    livetiming.formula1.com répond **HTTP 403** sur tous les flux. FastF1 sait
    basculer sur son miroir, mais requête par requête et seulement après avoir
    perdu un aller-retour à chaque fois. On sonde donc les deux serveurs (une
    fois par heure) et, si le principal est bloqué alors que le miroir répond,
    on bascule `base_url` globalement : plus aucune requête ne part vers le
    serveur bloqué.

    Ne pas émettre de `st.*` ici (fonction cachée, rejouée à chaque hit)."""
    primary = _probe_host(F1_HOST)
    if primary == 200:
        fastf1._api.base_url = F1_HOST
        return {"host": F1_HOST, "primary": primary, "mirror": None, "switched": False}
    mirror = _probe_host(F1_MIRROR)
    if mirror == 200:
        fastf1._api.base_url = F1_MIRROR  # relu à chaque appel par fetch_page
        return {"host": F1_MIRROR, "primary": primary, "mirror": mirror, "switched": True}
    # Les deux en carafe : on garde l'officiel, l'erreur restera explicite
    fastf1._api.base_url = F1_HOST
    return {"host": F1_HOST, "primary": primary, "mirror": mirror, "switched": False}


DATA_HOST = select_data_host()


class SessionLoadError(RuntimeError):
    """Échec de chargement, avec les warnings FastF1 qui expliquent pourquoi."""

    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or []


@contextlib.contextmanager
def _capture_fastf1_logs():
    """Collecte les warnings FastF1 émis pendant un chargement. FastF1 avale
    les erreurs réseau en warnings (« Failed to load timing data! ») : sans ça
    on ne sait pas CE qui a échoué, seulement que la session est vide."""
    records = []

    class _Handler(logging.Handler):
        def emit(self, record):
            if record.levelno >= logging.WARNING:
                records.append(record.getMessage())

    handler = _Handler()
    logger = logging.getLogger("fastf1")
    logger.addHandler(handler)
    try:
        yield records
    finally:
        logger.removeHandler(handler)


def _network_diagnostic():
    """Joignabilité des serveurs depuis l'hébergeur. On sonde un vrai fichier
    de données (pas la racine du site, qui peut répondre 200 alors que les
    données sont refusées) pour que le verdict soit sans ambiguïté."""
    import requests

    lines = []
    for label, base in (("Serveur F1 (données de session)", F1_HOST),
                        ("Miroir FastF1 (secours)", F1_MIRROR)):
        code = _probe_host(base)
        if code == 200:
            mark, txt = "✅", "HTTP 200"
        elif isinstance(code, int):
            mark, txt = "⛔", f"HTTP {code}" + (" (IP de l'hébergeur filtrée)" if code == 403 else "")
        else:
            mark, txt = "❌", str(code)
        actif = " · **utilisé**" if base == fastf1._api.base_url else ""
        lines.append(f"- {mark} **{label}** : {txt}{actif}")
    try:
        r = requests.get("https://api.jolpi.ca/ergast/f1/2025/1/results.json", timeout=12)
        lines.append(f"- {'✅' if r.status_code < 400 else '⛔'} "
                     f"**Jolpica/Ergast (résultats)** : HTTP {r.status_code}")
    except Exception as exc:
        lines.append(f"- ❌ **Jolpica/Ergast (résultats)** : {type(exc).__name__}")
    return lines

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
    # Équipes historiques (l'app couvre 2018 → présent)
    "Toro Rosso": "#469BFF",
    "Alfa Romeo": "#900000", "Alfa Romeo Racing": "#900000",
    "Renault": "#FFF500",
    "Racing Point": "#F596C8", "Force India": "#F596C8",
    "Alpine F1 Team": "#E91E63",
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
# Format des zones : (nom, virage(s), distance début m, distance fin m, description).
# Les distances numériques alimentent aussi les presets de l'onglet "Zoom virage".
CIRCUITS_INFO = {
    "Bahrain Grand Prix": {
        "facts": "Premier circuit nocturne du calendrier. Asphalte abrasif, gros stress pneus. 3 zones DRS, beaucoup d'overtaking spots.",
        "zones": [
            ("T1 entrée", "T1", 0, 400, "Gros freinage de 320 à 80 km/h depuis la ligne droite des stands. Premier overtaking spot, beaucoup de chaos au départ."),
            ("T4 chicane", "T4", 800, 1100, "Freinage en bout de la deuxième plus longue ligne droite. Deuxième zone d'overtaking majeur."),
            ("Esses T9-T10", "T9-T10", 2900, 3300, "Enchaînement rapide gauche-droite, technique. Différencie les champions."),
            ("T13", "T13", 4400, 4700, "Long virage à droite, traction critique sur la sortie pour les stats S3."),
        ],
    },
    "Australian Grand Prix": {
        "facts": "Circuit semi-permanent dans Albert Park. Refait en 2022 (plus rapide). Mur de béton omniprésent — peu de marge d'erreur.",
        "zones": [
            ("T1-T2 chicane", "T1-T2", 0, 500, "Chicane rapide d'ouverture, gros engagement. Premier indicateur de confiance."),
            ("T3 droite", "T3", 600, 900, "Long droite, traction et trail-braking en entrée."),
            ("T9-T10 esses", "T9-T10", 2400, 2900, "Section flowing très rapide, lit le rythme du pilote."),
            ("T11-T12", "T11-T12", 3500, 3900, "Chicane rapide, mur proche, late braking redoutable."),
        ],
    },
    "Chinese Grand Prix": {
        "facts": "Tracé en forme de '上' (caractère 'au-dessus'). Le virage 1-2-3 en spirale est un casse-tête unique : rayon décroissant. Longue ligne droite de retour avec DRS.",
        "zones": [
            ("Spirale T1-T2-T3", "T1-T3", 200, 1100, "Triple droite à rayon décroissant — différencie les pilotes qui anticipent vs ceux qui réagissent. Iconique de Shanghai."),
            ("T6 hairpin", "T6", 1900, 2200, "Épingle serrée, gros freinage, traction critique pour la suite."),
            ("T11-T12-T13", "T11-T13", 3800, 4400, "Section technique avant la longue ligne droite. La sortie de T13 conditionne la Vmax."),
            ("T14 freinage", "T14", 5300, 5700, "Gros freinage de 330 à 60 km/h en bout de back straight. Spot d'overtaking principal."),
        ],
    },
    "Japanese Grand Prix": {
        "facts": "Suzuka, figure-8, légende absolue. Circuit de pilotes par excellence — peu d'overtaking, tout se joue sur l'engagement et la précision.",
        "zones": [
            ("S1 Esses (T2-T7)", "T2-T7", 400, 1300, "Enchaînement de S à haute vitesse. Le rythme et la fluidité du pilote sont mis à nu. Une seule erreur compromet toute la séquence."),
            ("Dunlop Curve + Degner", "T8-T10", 1300, 2200, "Gauche en aveugle puis droite-droite. Trail-braking expert nécessaire."),
            ("Spoon Curve", "T13-T14", 3300, 3800, "Gauche double-apex, très long. Différencie momentum vs rotation."),
            ("130R", "T15", 4300, 4600, "Gauche flat-out à 320 km/h. Engagement pur, peu de marge."),
            ("Casio Triangle", "T16-T18", 4900, 5200, "Chicane finale, freinage tardif depuis 130R, sortie sur la ligne droite des stands."),
        ],
    },
    "Miami Grand Prix": {
        "facts": "Circuit street autour du Hard Rock Stadium. 3 zones DRS, surface lisse. Bus-stop final section très technique.",
        "zones": [
            ("T1 droite", "T1", 0, 400, "Entrée depuis ligne droite, gros freinage. Premier overtaking spot."),
            ("T8 gauche", "T8", 1900, 2200, "Virage long à gauche, traction sur la sortie."),
            ("T11 freinage", "T11", 2700, 3100, "Gros freinage avant le bus-stop, fin de la 2ème zone DRS."),
            ("Bus-stop T13-T16", "T13-T16", 3800, 4500, "Section sinueuse style chicane multiple, ultra technique. Différencie les pilotes capables d'enchaîner les inputs."),
        ],
    },
    "Emilia Romagna Grand Prix": {
        "facts": "Imola, circuit historique en Italie. Très technique, peu d'overtaking. Tamburello et Villeneuve sont des chicanes lourdes de symboles (Senna, Ratzenberger).",
        "zones": [
            ("Tamburello", "T2-T3", 300, 800, "Première chicane gauche-droite. Site historique. Différenciateur sur l'agressivité au freinage initial."),
            ("Villeneuve", "T4-T5", 900, 1300, "Chicane droite-gauche, plus rapide que Tamburello."),
            ("Variante Alta", "T9-T10", 2600, 3000, "Chicane en montée. Engagement total."),
            ("Acque Minerali", "T11-T13", 3100, 3700, "Droite double-apex, descente. Trail-braking expert."),
            ("Rivazza", "T14-T15", 3800, 4400, "Gauche double-apex final, descente. Très précis."),
        ],
    },
    "Monaco Grand Prix": {
        "facts": "Le plus mythique. Pas d'overtaking, tout se joue en qualif. Marge zéro, mur partout. Style chirurgical requis.",
        "zones": [
            ("Sainte-Devote", "T1", 0, 300, "Droite depuis la ligne droite des stands. Crash classique de départ."),
            ("Casino Square", "T4", 700, 900, "Gauche en aveugle après une bosse. Confidence test."),
            ("Mirabeau Haute + Hairpin", "T5-T6", 1100, 1500, "L'épingle la plus lente du calendrier (~50 km/h). Trail-braking max."),
            ("Tunnel + Nouvelle Chicane", "T9-T10", 1800, 2300, "Sortie de tunnel en aveugle à 290 km/h puis gros freinage. Différenciateur visibilité+confiance."),
            ("Swimming Pool", "T13-T16", 2500, 2800, "Enchaînement gauche-droite-gauche-droite, mur très proche. Précision absolue."),
            ("Rascasse + Anthony Noghes", "T17-T19", 2900, 3300, "Final, gauche-droite. Très lent, traction critique."),
        ],
    },
    "Spanish Grand Prix": {
        "facts": "Barcelona-Catalunya. Circuit-référence des ingénieurs (les voitures sont testées ici). Mix de virages rapides et lents, lit toutes les qualités d'une voiture.",
        "zones": [
            ("T1-T2-T3", "T1-T3", 0, 700, "Séquence d'ouverture, gros freinage T1 puis enchaînement."),
            ("T3 long droite", "T3", 700, 1100, "Long virage à droite, traction critique pour Vmax."),
            ("T9 high-speed", "T9", 2900, 3300, "Gauche très rapide, engagement aéro pur."),
            ("T10 hairpin", "T10", 3400, 3700, "Épingle serrée, opportunité d'overtaking."),
            ("Final T13-T15", "T13-T15", 4100, 4600, "Triple gauche, traction sur la sortie. Section critique du tour."),
        ],
    },
    "Canadian Grand Prix": {
        "facts": "Circuit Gilles Villeneuve à Montréal, sur l'île Notre-Dame. Stop-and-go, gros freinages, le mur des champions à la fin.",
        "zones": [
            ("T1-T2 chicane", "T1-T2", 0, 400, "Première chicane après le départ, gros freinage."),
            ("T6-T7 chicane", "T6-T7", 1200, 1500, "Chicane rapide gauche-droite."),
            ("Hairpin", "T10", 2300, 2700, "Épingle très lente (~60 km/h). Modulation throttle critique en sortie sur Casino Straight."),
            ("Wall of Champions", "T13-T14", 3900, 4250, "Chicane finale gauche-droite à 30 cm du mur. Hill, Schumacher, Villeneuve s'y sont crashés en 1999. Le test ultime de confiance dans l'avant."),
        ],
    },
    "Austrian Grand Prix": {
        "facts": "Red Bull Ring. Court (~4.3 km), peu de virages mais très intenses. Beaucoup de dénivelé. 3 zones DRS.",
        "zones": [
            ("T1 Niki Lauda", "T1", 200, 500, "Gros freinage en montée, de 310 à 80 km/h. Premier overtaking spot."),
            ("T3 Remus", "T3", 1100, 1400, "Droite serrée en sommet, freinage tardif depuis la 2ème ligne droite."),
            ("T4 Schlossgold", "T4", 1700, 2000, "Gros freinage, gauche serrée. 3ème overtaking spot."),
            ("T6-T7 Rauch", "T6-T7", 2700, 3200, "Enchaînement rapide droite-gauche en descente."),
            ("T9-T10 final", "T9-T10", 3700, 4300, "Final, droite puis droite en descente."),
        ],
    },
    "British Grand Prix": {
        "facts": "Silverstone, berceau de la F1 (premier GP en 1950). Circuit ultra-rapide, fortes contraintes aéro. Une vraie qualité de châssis nécessaire.",
        "zones": [
            ("Abbey-Farm", "T1-T2", 0, 700, "Enchaînement droite-gauche rapide au départ."),
            ("Village-Loop", "T3-T4", 800, 1300, "Section lente, contraste avec le reste."),
            ("Copse", "T9", 2500, 2900, "Droite flat-out à 290 km/h. Engagement pur."),
            ("Maggotts-Becketts-Chapel", "T10-T13", 3000, 3900, "Enchaînement de virages rapides gauche-droite-gauche-droite. Le passage le plus iconique en F1 moderne. Lit le rythme et le grip aéro."),
            ("Stowe", "T15", 4500, 4900, "Droite rapide après Hangar Straight. Trail-braking modéré."),
            ("Vale-Club", "T16-T18", 5100, 5891, "Chicane finale lente puis sortie sur la ligne droite des stands."),
        ],
    },
    "Hungarian Grand Prix": {
        "facts": "Hungaroring, surnommé 'Monaco sans murs'. Étroit, sinueux, peu d'overtaking. Setup high-downforce.",
        "zones": [
            ("T1", "T1", 0, 400, "Gros freinage en descente."),
            ("T2-T3", "T2-T3", 500, 900, "Droite-gauche rapide."),
            ("T4-T5", "T4-T5", 1000, 1500, "Gauche-droite, double-apex."),
            ("T11-T12-T13", "T11-T13", 3300, 3800, "Section finale technique, traction critique."),
            ("T14", "T14", 4000, 4381, "Droite finale, sortie sur la ligne droite des stands."),
        ],
    },
    "Belgian Grand Prix": {
        "facts": "Spa-Francorchamps, le plus long circuit du calendrier (~7 km). En pleine forêt ardennaise. Météo capricieuse — il peut pleuvoir sur S1 et être sec à S3.",
        "zones": [
            ("La Source", "T1", 150, 400, "Épingle juste après la grille, freinage de 320 à 80 km/h. Premier overtaking spot, chaos au départ."),
            ("Eau Rouge / Raidillon", "T3-T5", 800, 1500, "L'enchaînement gauche-droite-gauche le plus iconique de la F1. Compression en sortie de descente puis montée à 300+ km/h. Engagement total nécessaire. Sans visibilité du sommet à l'entrée. Le test de confiance pure."),
            ("Combes", "T7-T9", 2800, 3300, "Enchaînement droite-gauche-droite, freinage depuis la ligne droite Kemmel. Spot d'overtaking via DRS."),
            ("Pouhon", "T10-T11", 3800, 4400, "Double-apex gauche très rapide à 280 km/h. Trail-braking expert."),
            ("Stavelot", "T13-T14", 5000, 5500, "Droite double-apex, traction critique pour S3."),
            ("Bus Stop chicane", "T18-T19", 6500, 6900, "Chicane finale gauche-droite, gros freinage. Dernier overtaking spot."),
        ],
    },
    "Dutch Grand Prix": {
        "facts": "Zandvoort, circuit côtier néerlandais. Vent omniprésent. Deux virages relevés (T3 et T14) — unique en F1 actuelle.",
        "zones": [
            ("Tarzanbocht", "T1", 0, 400, "Droite relevée après la ligne droite. Beaucoup d'overtaking possible grâce à la pente."),
            ("Hugenholtzbocht", "T3", 600, 900, "Gauche relevée banked. Engagement aéro."),
            ("Slotemakerbocht-Scheivlak", "T7-T9", 1900, 2400, "Section rapide en sommet, sans visibilité de la sortie. Vent ici très perturbant."),
            ("Final banked T14", "T14", 3900, 4259, "Droite finale relevée (18°), exit sur la ligne droite des stands. La banking permet des sorties à très haute vitesse."),
        ],
    },
    "Italian Grand Prix": {
        "facts": "Monza, le 'Temple de la Vitesse'. Setup low-downforce, longues lignes droites. Aspiration et DRS critiques en course.",
        "zones": [
            ("Variante del Rettifilo", "T1-T2", 0, 500, "Gros freinage en bout de ligne droite des stands, première chicane droite-gauche. Sortie sur la traction critique."),
            ("Curva Grande + Roggia", "T3-T5", 1100, 1800, "Droite rapide puis chicane. Section overtaking via aspiration."),
            ("Lesmo 1+2", "T6-T7", 1800, 2400, "Double droite, engagement et confiance dans l'avant."),
            ("Ascari", "T8-T10", 3700, 4300, "Chicane droite-gauche-droite ultra rapide. La plus technique du circuit."),
            ("Parabolica", "T11", 5200, 5700, "Long virage à droite, double apex, sortie sur la ligne droite des stands. La sortie conditionne le tour entier."),
        ],
    },
    "Azerbaijan Grand Prix": {
        "facts": "Baku City Circuit. Mix unique de longue ligne droite (~2 km, la plus longue du calendrier) et de section ville étroite. Imprévisible.",
        "zones": [
            ("T1 entrée", "T1", 0, 300, "Gros freinage de 340 à 90 km/h depuis la ligne droite des stands."),
            ("Castle section T8", "T8", 1800, 2100, "Le virage le plus étroit de la F1 — 7.6 m. Pas d'overtaking, prudence absolue."),
            ("Section ville T9-T15", "T9-T15", 2200, 3800, "Enchaînement de virages serrés, murs proches."),
            ("Long straight + T1", "Long straight", 4000, 6003, "La ligne droite de 2.2 km. Le coup d'aspiration est la donne de la course."),
        ],
    },
    "Singapore Grand Prix": {
        "facts": "Marina Bay Street Circuit. Course nocturne, 23 virages, le plus exigeant physiquement. Murs partout.",
        "zones": [
            ("T1-T2-T3 chicane", "T1-T3", 0, 700, "Triple chicane d'ouverture."),
            ("T5 hairpin", "T5", 1100, 1400, "Épingle après ligne droite, gros freinage."),
            ("Anderson Bridge", "T13", 3000, 3300, "Sortie de pont en aveugle."),
            ("T16-T19 final", "T16-T19", 4400, 5063, "Section finale étroite, mur très proche."),
        ],
    },
    "United States Grand Prix": {
        "facts": "COTA (Circuit of the Americas), Austin. Inspiré de Suzuka et Silverstone. T1 en montée brutale, gros freinage.",
        "zones": [
            ("T1", "T1", 0, 500, "Freinage en montée, 320 à 70 km/h. Premier overtaking spot."),
            ("Esses T2-T6", "T2-T6", 500, 1400, "Enchaînement S inspiré de Suzuka, ultra rapide."),
            ("T11 hairpin", "T11", 2500, 2900, "Épingle après back straight, gros freinage."),
            ("Section moyenne T12-T15", "T12-T15", 3000, 3800, "Section technique de transition."),
            ("T16-T18 hairpin sequence", "T16-T18", 4000, 4600, "Triple gauche serré."),
            ("T19-T20 final", "T19-T20", 4900, 5513, "Droite-gauche final."),
        ],
    },
    "Mexico City Grand Prix": {
        "facts": "Autódromo Hermanos Rodríguez. Altitude 2240 m — air raréfié, moins d'appui et de puissance moteur. Longue ligne droite, stade section iconique.",
        "zones": [
            ("T1-T2-T3", "T1-T3", 0, 800, "Séquence d'ouverture, gros freinage T1 depuis longue ligne droite."),
            ("Esses T7-T11", "T7-T11", 1900, 3000, "Enchaînement rapide en milieu de tour."),
            ("Stadium section T12-T16", "T12-T16", 3100, 3800, "Section dans le stade baseball — peu d'appui efficace, traction critique."),
            ("Peraltada (T17-T18)", "T17-T18", 4000, 4304, "Long droite final relevée. La sortie conditionne la Vmax sur la longue ligne droite."),
        ],
    },
    "São Paulo Grand Prix": {
        "facts": "Interlagos, circuit antihoraire (rare en F1). Météo très changeante (la pluie peut tomber sur S1 et pas S3). Tracé vallonné, course toujours pleine d'action.",
        "zones": [
            ("S do Senna", "T1-T2", 0, 500, "Gauche-droite d'ouverture en descente. Premier overtaking spot, chaos fréquent."),
            ("Descida do Lago", "T4-T5", 800, 1300, "Descente technique."),
            ("Junção", "T6-T7", 1700, 2100, "Épingle à gauche."),
            ("Subida do Boxes", "T12-T15", 3000, 3800, "Montée vers la ligne droite des stands."),
            ("Arquibancadas final", "T15", 3800, 4309, "Long droite finale en montée, jusqu'à la ligne droite des stands."),
        ],
    },
    "Las Vegas Grand Prix": {
        "facts": "Las Vegas Strip Circuit. Nocturne, sur le strip. 1.9 km de ligne droite, freinage massif au bout. Asphalte lisse, températures basses la nuit.",
        "zones": [
            ("T1-T4 opening", "T1-T4", 0, 1300, "Section technique d'ouverture en ville."),
            ("Sphere section T9-T12", "T9-T12", 2500, 3500, "Passage devant la Sphere, virages moyens."),
            ("T14 freinage", "T14", 5400, 5700, "Freinage massif de 340+ à 90 km/h en bout du Strip. Le spot d'overtaking principal."),
            ("T16-T17 final", "T16-T17", 5800, 6201, "Final, droite-gauche avant la ligne d'arrivée."),
        ],
    },
    "Qatar Grand Prix": {
        "facts": "Lusail International Circuit. Beaucoup de virages rapides en S, peu de longues lignes droites. Setup high-downforce.",
        "zones": [
            ("T1 freinage", "T1", 0, 400, "Premier freinage depuis ligne droite des stands."),
            ("T6-T7 esses", "T6-T7", 1500, 2000, "Enchaînement rapide."),
            ("T10-T12 technique", "T10-T12", 2700, 3400, "Section technique en S."),
            ("T13-T14 final", "T13-T14", 4400, 5000, "Final rapide."),
            ("T16 dernier", "T16", 5100, 5419, "Dernier virage, exit critique."),
        ],
    },
    "Abu Dhabi Grand Prix": {
        "facts": "Yas Marina Circuit, finale de saison. Course nocturne (passage jour-nuit). Refait en 2021 pour plus d'overtaking.",
        "zones": [
            ("T1", "T1", 0, 400, "Gros freinage en début de tour, freinage depuis 330 km/h."),
            ("T6-T7", "T6-T7", 1900, 2300, "Chicane droite-gauche, technique."),
            ("T9 long left", "T9", 2700, 3100, "Gauche très long, traction sortie pour la longue ligne droite."),
            ("T10 hairpin", "T10", 3100, 3400, "Épingle après longue ligne droite, gros freinage."),
            ("T12-T16 hotel section", "T12-T16", 4400, 5281, "Section finale autour du hotel Yas, technique."),
        ],
    },
    "Saudi Arabian Grand Prix": {
        "facts": "Jeddah Corniche Circuit. Le plus rapide circuit urbain du calendrier (~250 km/h de moyenne). 27 virages, murs partout, à éviter en course en peloton.",
        "zones": [
            ("T1 freinage", "T1", 0, 400, "Gros freinage de 330 à 100 km/h depuis ligne droite des stands."),
            ("Esses T4-T13", "T4-T13", 900, 3000, "Très long enchaînement de virages rapides, murs proches. Engagement pur."),
            ("T22-T23", "T22-T23", 5000, 5500, "Banked turn rapide, unique en F1."),
            ("T27 final", "T27", 6000, 6174, "Dernier virage, exit sur ligne droite des stands."),
        ],
    },
}

# ============== HELPERS GÉNÉRIQUES ==============
def _detect_mobile():
    """Détection mobile via le user-agent (st.context, Streamlit >= 1.37).
    'Mobi' couvre iPhone/Android ; iPad se présente comme desktop → traité
    comme grand écran, ce qui est le bon choix."""
    try:
        ua = st.context.headers.get("User-Agent") or st.context.headers.get("user-agent") or ""
    except Exception:
        ua = ""
    return ("Mobi" in ua) or ("Android" in ua)


def plot(fig):
    """Affichage Plotly adapté au mode compact. Sur mobile, un graphique Plotly
    interactif capture le geste tactile (pan/zoom) et empêche de faire défiler
    la page → dragmode=False rend le scroll à la page tout en gardant le hover
    au tap. La modebar est masquée (elle mange de la place pour rien au doigt)."""
    if MOBILE:
        fig.update_layout(dragmode=False)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    else:
        st.plotly_chart(fig, width="stretch")  # noqa: appel direct voulu (helper)


def show_table(styler, height=None, force_html=False, mono=False):
    """Affichage d'un tableau stylé, adapté au mode compact.

    st.dataframe dessine les cellules dans un canvas (Glide Data Grid) →
    texte flou sur les écrans Retina des téléphones, surtout après un zoom.
    En mode compact (ou avec force_html=True, ex. page Timing dont les badges
    colorés exigent un rendu maîtrisé), on rend le Styler en HTML natif dans
    un conteneur scrollable avec en-têtes collants ; mono=True bascule en
    police à chasse fixe façon écran de timing. Sur desktop sans force_html,
    on garde st.dataframe (tri, redimensionnement des colonnes)."""
    if not (MOBILE or force_html):
        st.dataframe(styler, width="stretch", hide_index=True, height=height)
        return
    html = styler.hide(axis="index").to_html()
    cls = "tbl-wrap mono" if mono else "tbl-wrap"
    st.markdown(
        f'<div class="{cls}" style="max-height:{int(height or 520)}px">{html}</div>',
        unsafe_allow_html=True,
    )


def _fmt_lap(td):
    """Temps au tour 'm:ss.mmm', ou — si manquant."""
    if pd.isna(td):
        return "—"
    s = td.total_seconds()
    return f"{int(s // 60)}:{s % 60:06.3f}"


def _fmt_sec(td):
    """Temps de secteur 'ss.mmm', ou — si manquant."""
    return f"{td.total_seconds():.3f}" if pd.notna(td) else "—"


SESSION_LABELS = {
    "Q": "Qualifications", "R": "Course", "SQ": "Sprint Shootout", "S": "Sprint",
    "FP3": "Essais Libres 3", "FP2": "Essais Libres 2", "FP1": "Essais Libres 1",
}
SESSION_TYPES = list(SESSION_LABELS.keys())
YEARS = list(range(2026, 2017, -1))


def gp_options_from(sched):
    """Options du sélecteur de Grand Prix depuis un calendrier FastF1 :
    {label affiché: EventName}. Partagé entre la sidebar et l'écran d'accueil."""
    return {
        f"R{int(row.RoundNumber)} — {row.EventName} ({row.Country})": row.EventName
        for _, row in sched.iterrows()
    }


RACE_POINTS = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}
SPRINT_POINTS = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}


def points_from_results(res, ses):
    """Points par pilote depuis une feuille de résultats FastF1.
    La colonne Points est vide pour les sessions Sprint (même trou de données
    que la colonne Time) → fallback : barème officiel appliqué à la position
    d'arrivée. Pas de point de meilleur tour (supprimé depuis 2025)."""
    scale = SPRINT_POINTS if ses == "S" else RACE_POINTS
    pts_col_ok = ("Points" in res.columns and res["Points"].notna().any()
                  and float(res["Points"].fillna(0).sum()) > 0)
    out = {}
    for _, r in res.iterrows():
        code = str(r["Abbreviation"])
        if pts_col_ok:
            p = r.get("Points")
            out[code] = float(p) if pd.notna(p) else 0.0
        else:
            pos = r.get("Position")
            out[code] = float(scale.get(int(pos), 0)) if pd.notna(pos) else 0.0
    return out


def hex_to_rgb_str(h):
    h = h.lstrip("#")
    return f"rgb({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)})"


def hex_to_rgba(h, a):
    h = h.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


def text_on(bg):
    """Noir ou blanc selon la luminance du fond — garde les badges lisibles
    sur les couleurs claires (jaune Renault, gris Haas, pink Racing Point)."""
    h = bg.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return "#111111" if (0.299 * r + 0.587 * g + 0.114 * b) > 150 else "#FFFFFF"


def _chan(tel, ch):
    """Brake est booléen chez FastF1 → int, sinon plotly peut basculer en axe
    catégoriel selon les versions. DRS est un code (0/1 fermé, 8 éligible,
    10/12/14 volet ouvert) → converti en 0/1 « ouvert ». Le reste passe tel quel."""
    if ch == "Brake":
        return tel[ch].astype(int)
    if ch == "DRS":
        return (tel[ch] >= 10).astype(int)
    return tel[ch]


def _top_zones(gain, dist, k=3, min_sep=150.0):
    """Indices des k plus gros gains positifs, en écartant tout point à moins de
    min_sep mètres d'une zone déjà retenue — sinon les 'top zones' sont k
    échantillons consécutifs du même virage."""
    order = np.argsort(gain)[::-1]
    picked = []
    for i in order:
        if gain[i] <= 0 or len(picked) >= k:
            break
        if all(abs(dist[i] - dist[j]) > min_sep for j in picked):
            picked.append(int(i))
    return picked


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
            # prepend=0 garantit au moins un onset dès que brk.any() (y compris
            # si le pilote freinait déjà au 1er échantillon de la fenêtre)
            onsets = np.where(np.diff(brk, prepend=0) == 1)[0]
            onset_d = float(pre["Distance"].iloc[onsets[-1]])
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


def style_sig(tel, name):
    """Métriques chiffrées caractérisant le style d'un pilote sur un tour."""
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
    sig["Throttle ramp-up moyen"] = round(float(rising.mean()) if rising.size else 0.0, 2)
    brake_diff = np.diff((tel["Brake"] > 0).astype(int))
    sig["Nb phases de freinage"] = int((brake_diff == 1).sum())
    return sig


# ============== HELPERS DIAGRAMME G-G ==============
def compute_gg(lap, ds=2.0, window_m=40.0):
    """Accélérations latérale et longitudinale (en g) le long d'un tour.

    - a_long = v·dv/ds : dérivée spatiale de la vitesse lissée.
    - a_lat  = v²·κ : courbure κ calculée depuis X/Y resamplés en distance
      (Savitzky-Golay deriv 1 et 2). ⚠️ X/Y FastF1 sont en 1/10 de mètre
      → division par 10 obligatoire, sinon a_lat est fausse d'un facteur 10.

    Le flux position est du GPS ~4-5 Hz interpolé : valeurs absolues
    indicatives (±10-15 %, dénivelé non pris en compte), mais la comparaison
    entre deux pilotes sur le même tracé reste valide.
    Retourne dict {a_lat, a_long, s} en g / g / m, ou None si données insuffisantes.
    """
    tel = lap.get_telemetry().dropna(subset=["X", "Y", "Speed", "Distance"])
    if len(tel) < 30:
        return None
    s_raw = tel["Distance"].values.astype(float)
    keep = np.diff(s_raw, prepend=s_raw[0] - 1.0) > 0  # interp exige s strictement croissant
    s_raw = s_raw[keep]
    x_raw = tel["X"].values.astype(float)[keep] / 10.0
    y_raw = tel["Y"].values.astype(float)[keep] / 10.0
    v_raw = tel["Speed"].values.astype(float)[keep] / 3.6

    # Resampling uniforme en distance → dérivées spatiales propres
    s = np.arange(s_raw[0], s_raw[-1], ds)
    if len(s) < 50:
        return None
    x = np.interp(s, s_raw, x_raw)
    y = np.interp(s, s_raw, y_raw)
    v = np.interp(s, s_raw, v_raw)

    win = int(window_m / ds)
    win = max(7, win + (win % 2 == 0))  # fenêtre impaire, >= 7 points

    dx = savgol_filter(x, win, 3, deriv=1, delta=ds)
    ddx = savgol_filter(x, win, 3, deriv=2, delta=ds)
    dy = savgol_filter(y, win, 3, deriv=1, delta=ds)
    ddy = savgol_filter(y, win, 3, deriv=2, delta=ds)
    denom = np.power(dx * dx + dy * dy, 1.5)
    denom[denom < 1e-9] = 1e-9
    kappa = (dx * ddy - dy * ddx) / denom  # courbure signée (gauche/droite)

    v_s = savgol_filter(v, win, 3)
    dv = savgol_filter(v, win, 3, deriv=1, delta=ds)
    a_long = v_s * dv / 9.81
    a_lat = v_s ** 2 * kappa / 9.81

    # Bords du lissage + artefacts GPS : on écarte les extrémités du tour
    # et les valeurs physiquement irréalistes pour une F1
    trim = win
    a_lat, a_long, s_out, v_out = a_lat[trim:-trim], a_long[trim:-trim], s[trim:-trim], v_s[trim:-trim]
    ok = (np.abs(a_lat) < 6.5) & (a_long > -7.0) & (a_long < 3.0) & (v_out > 8.0)
    if ok.sum() < 50:
        return None
    return {"a_lat": a_lat[ok], "a_long": a_long[ok], "s": s_out[ok]}


def gg_envelope(a_lat, a_long, n_bins=36, q=95):
    """Enveloppe du nuage g-g : percentile q du rayon par secteur angulaire.
    Rend les deux pilotes comparables d'un coup d'œil là où deux nuages
    superposés sont illisibles. Retourne (x, y) du polygone fermé, ou None."""
    theta = np.arctan2(a_long, a_lat)
    r = np.hypot(a_lat, a_long)
    bins = np.linspace(-np.pi, np.pi, n_bins + 1)
    idx = np.digitize(theta, bins) - 1
    centers, radii = [], []
    for b in range(n_bins):
        m = idx == b
        if m.sum() >= 3:
            centers.append((bins[b] + bins[b + 1]) / 2)
            radii.append(float(np.percentile(r[m], q)))
    if len(centers) < 8:
        return None
    centers.append(centers[0])
    radii.append(radii[0])  # ferme le polygone
    c, rr = np.array(centers), np.array(radii)
    return rr * np.cos(c), rr * np.sin(c)


# ============== CACHED LOADERS ==============
@st.cache_data(show_spinner=False, ttl=24 * 3600)
def load_schedule(year):
    """Charge le calendrier d'une année."""
    sched = fastf1.get_event_schedule(year, include_testing=False)
    return sched[["RoundNumber", "EventName", "Country", "Location", "EventDate"]]


@st.cache_resource(show_spinner=False, ttl=24 * 3600, max_entries=3)
def load_session(year, gp, session_type):
    """Charge une session F1, mise en cache.
    max_entries=3 : une session complète pèse plusieurs centaines de Mo une fois
    chargée — sans limite, quelques sessions suffisent à saturer 1 Go de RAM
    (Streamlit Community Cloud).
    weather=True → bandeau météo + contexte pluie/température sur les graphes.
    messages=True → drapeaux/SC/pénalités, ET la colonne Deleted des laps :
    FastF1 ne marque les tours supprimés QUE si les messages sont chargés."""
    with _capture_fastf1_logs() as fastf1_logs:
        s = fastf1.get_session(year, gp, session_type)
        s.load(telemetry=True, laps=True, weather=True, messages=True)
        # s.load() N'ÉCHOUE PAS si l'API F1 est injoignable : il avale les
        # erreurs en warnings et rend une session vide → session.laps lèverait
        # un DataNotLoadedError brut plus loin, hors du try/except d'affichage.
        # On vérifie ici pour transformer ça en message d'erreur documenté.
        try:
            _ = s.laps
        except Exception as exc:
            raise SessionLoadError(
                "les données de cette session n'ont pas pu être téléchargées — "
                "serveurs F1 injoignables depuis l'hébergeur, ou session pas "
                "encore publiée. Ouvre le diagnostic ci-dessous pour la cause exacte.",
                list(dict.fromkeys(fastf1_logs)),
            ) from exc
    return s


@st.cache_data(show_spinner=False, ttl=6 * 3600)
def season_points_before(year, round_number, session_type):
    """Points cumulés par pilote ET par équipe AVANT la session courante (courses + sprints
    des manches précédentes, plus le sprint du même week-end si la session
    analysée est la course), et countback réglementaire : décompte des
    positions d'arrivée en course [nb de P1, nb de P2, ...] pour départager
    les égalités de points comme la F1. Ne charge que les feuilles de
    résultats (laps/télémétrie exclus) → rapide, puis caches disque + app."""
    sched = fastf1.get_event_schedule(year, include_testing=False)
    pts, cb, team_pts = {}, {}, {}
    for _, ev_row in sched.iterrows():
        rnd = int(ev_row["RoundNumber"])
        if rnd > round_number:
            continue
        is_sprint_we = "sprint" in str(ev_row.get("EventFormat", "")).lower()
        ses_list = []
        if rnd < round_number:
            if is_sprint_we:
                ses_list.append("S")
            ses_list.append("R")
        elif session_type == "R" and is_sprint_we:
            ses_list.append("S")
        for ses in ses_list:
            try:
                s = fastf1.get_session(year, rnd, ses)
                s.load(laps=False, telemetry=False, weather=False, messages=False)
                res = s.results
                if res is None or res.empty:
                    continue
                pfr = points_from_results(res, ses)
                for code, p in pfr.items():
                    pts[code] = pts.get(code, 0.0) + p
                for _, r in res.iterrows():
                    code = str(r["Abbreviation"])
                    team = str(r.get("TeamName", "") or "")
                    if team:  # cumul constructeurs (somme des deux pilotes)
                        team_pts[team] = team_pts.get(team, 0.0) + pfr.get(code, 0.0)
                    if ses == "R":
                        pos = r.get("Position")
                        if pd.notna(pos) and 1 <= int(pos) <= 22:
                            cb.setdefault(code, [0] * 22)[int(pos) - 1] += 1
            except Exception:
                continue  # manche pas encore courue / résultats absents
    return pts, cb, team_pts


def safe_circuit_info(sess):
    """get_circuit_info() peut lever KeyError si le pilote du tour de référence n'a pas
    son flux position complet. On dégrade proprement vers None au lieu de faire planter l'app."""
    try:
        return sess.get_circuit_info()
    except Exception:
        st.warning(
            "⚠️ Position des virages indisponible pour cette session "
            "(flux télémétrie incomplet côté données F1). Les onglets d'analyse virage "
            "seront limités, le reste fonctionne normalement."
        )
        return None


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
    """Vitesse mini par virage pour le tour rapide de chaque pilote du plateau, + Vmax.
    Version silencieuse : pas de st.warning ici (une fonction cachée rejoue ses
    éléments st.* à chaque hit de cache → warning dupliqué avec celui du top-level)."""
    sess = load_session(year, gp, ses)
    try:
        ci = sess.get_circuit_info()
    except Exception:
        return None
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


@st.cache_data(show_spinner=False, ttl=24 * 3600)
def load_team_radio(year, gp, ses):
    """Clips radio publiés par la FOM (flux TeamRadio du live timing) : la
    sélection officielle des « meilleurs moments » diffusés TV/app F1 — pas
    l'intégralité des communications. Endpoint non documenté mais stable ;
    seul le JSON (léger) est téléchargé ici, les MP3 sont lus directement par
    le navigateur via st.audio. Miroir communautaire fastf1 en secours.
    Retourne un DataFrame [Pilote, Lap, utc, url] chronologique, ou None si
    indisponible (fréquent avant ~2022)."""
    import json
    import requests

    sess = load_session(year, gp, ses)
    path = getattr(sess, "api_path", None)
    if not path:
        return None
    captures, audio_base = None, None
    # Serveur actif d'abord (cf. select_data_host), puis les autres en secours
    for base in dict.fromkeys((fastf1._api.base_url, F1_HOST, F1_MIRROR)):
        try:
            r = requests.get(base + path + "TeamRadio.json", timeout=10,
                             headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            captures = json.loads(r.content.decode("utf-8-sig")).get("Captures", [])
            audio_base = base + path
            break
        except Exception:
            continue
    if isinstance(captures, dict):  # quirk de l'API quand il n'y a qu'un clip
        captures = [captures]
    if not captures:
        return None

    laps = sess.laps
    num2code = {}
    if "DriverNumber" in laps.columns:
        num2code = (laps.dropna(subset=["DriverNumber", "Driver"])
                        .drop_duplicates("DriverNumber")
                        .set_index("DriverNumber")["Driver"].to_dict())
    rows = []
    for c in captures:
        utc = pd.to_datetime(c.get("Utc"), errors="coerce", utc=True)
        utc = utc.tz_convert(None) if pd.notna(utc) else pd.NaT
        drv = num2code.get(str(c.get("RacingNumber", "")), str(c.get("RacingNumber", "?")))
        lap_n = np.nan
        if pd.notna(utc) and "LapStartDate" in laps.columns:
            # Tour en cours = dernier tour du pilote démarré avant le message
            ld = laps[(laps["Driver"] == drv) & laps["LapStartDate"].notna()]
            before = ld[ld["LapStartDate"] <= utc]
            if len(before):
                lap_n = int(before["LapNumber"].iloc[-1])
        rows.append({"Pilote": drv, "Lap": lap_n, "utc": utc,
                     "url": audio_base + str(c.get("Path", ""))})
    if not rows:
        return None
    return pd.DataFrame(rows).sort_values("utc", na_position="last").reset_index(drop=True)


def _render_radio_clips(df_clips, max_clips=50):
    """Liste de clips radio jouables (label pilote · tour · heure + lecteur)."""
    for _, r_ in df_clips.head(max_clips).iterrows():
        lap_txt = f"L{int(r_['Lap'])}" if pd.notna(r_["Lap"]) else "—"
        when = f" · {r_['utc']:%H:%M} UTC" if pd.notna(r_["utc"]) else ""
        st.markdown(f"**{r_['Pilote']}** · {lap_txt}{when}")
        st.audio(r_["url"], format="audio/mp3")
    if len(df_clips) > max_clips:
        st.caption(f"… {len(df_clips) - max_clips} clips non affichés — filtre par pilote "
                   f"pour les voir.")


# ============== HEADER ==============
st.markdown("""
# 🏎️ Analyse F1
### Lecture télémétrique des styles de pilotage en Formule 1
""")

# ============== SIDEBAR — CONTRÔLES ==============
st.sidebar.markdown("## 🎛️ Paramètres")

MOBILE = st.sidebar.toggle(
    "📱 Affichage compact",
    value=_detect_mobile(),
    help="Activé automatiquement sur mobile. Empile les vues côte à côte, "
         "allège la feuille des temps et rend le scroll tactile aux graphiques.",
)

# CSS des tableaux HTML natifs (voir show_table) : thème sombre, chiffres
# tabulaires, en-têtes collants. Injecté inconditionnellement — la page
# Timing rend en HTML même sur desktop (badges couleur équipe, fonds records).
st.markdown("""
<style>
.tbl-wrap {overflow: auto; border: 1px solid rgba(255,255,255,.15);
           border-radius: 8px; margin-bottom: 0.6rem;}
.tbl-wrap table {border-collapse: collapse; width: 100%;
                 font-size: 0.85rem; font-variant-numeric: tabular-nums;}
.tbl-wrap th {position: sticky; top: 0; z-index: 1; background: #262730;
              color: #FAFAFA; text-align: left; padding: 6px 8px;
              font-weight: 600; white-space: nowrap;}
.tbl-wrap td {padding: 6px 8px; color: #FAFAFA; white-space: nowrap;
              border-top: 1px solid rgba(255,255,255,.08);}
.tbl-wrap.mono table {font-family: ui-monospace, SFMono-Regular, Menlo,
                      Consolas, monospace; font-size: 0.82rem;}
.tbl-wrap.mono td {padding: 5px 9px;}
</style>
""", unsafe_allow_html=True)

if MOBILE:
    # Les selectbox Streamlit sont des champs de recherche : au tap, le
    # téléphone ouvre le clavier virtuel qui mange la moitié de l'écran.
    # On passe leurs inputs en readonly + inputmode="none" → le menu s'ouvre
    # toujours, mais plus de clavier (seule la recherche par frappe, inutile
    # au doigt, est sacrifiée). Desktop non concerné (recherche conservée).
    # Sélecteurs : react-aria (Streamlit >= 1.59, role="combobox") ET BaseWeb
    # (versions antérieures). Streamlit 1.59 met déjà readonly sur les listes
    # courtes — seules les longues (ex. Grand Prix) restent « cherchables ».
    # Trois filets : patch immédiat, MutationObserver (Streamlit recrée les
    # inputs à chaque rerun et React peut retirer l'attribut), et touchstart
    # en capture (synchrone, AVANT que le focus ne déclenche le clavier).
    components.html("""
    <script>
    const doc = window.parent.document;
    const SEL = '[data-testid="stSelectbox"] input[role="combobox"], '
              + '[data-testid="stMultiSelect"] input[role="combobox"], '
              + 'div[data-baseweb="select"] input';
    const fix = (el) => {
        if (!el.hasAttribute('readonly')) el.setAttribute('readonly', 'readonly');
        if (el.getAttribute('inputmode') !== 'none') el.setAttribute('inputmode', 'none');
    };
    const patch = () => doc.querySelectorAll(SEL).forEach(fix);
    patch();
    new MutationObserver(patch).observe(doc.body, {
        childList: true, subtree: true,
        attributes: true, attributeFilter: ['readonly', 'inputmode'],
    });
    doc.addEventListener('touchstart', patch, {capture: true, passive: true});
    doc.addEventListener('focusin', (e) => {
        if (e.target && e.target.matches && e.target.matches(SEL)) fix(e.target);
    }, true);
    </script>
    """, height=0)

year = st.sidebar.selectbox(
    "Saison",
    options=YEARS,
    index=0,  # saison en cours (2026) par défaut
    help="FastF1 supporte 2018 → présent. Les données 2026 récentes peuvent être partielles.",
)

try:
    with st.spinner(f"Chargement du calendrier {year}…"):
        schedule = load_schedule(year)
except Exception as e:
    st.error(f"❌ Impossible de charger le calendrier {year} (API FastF1 injoignable ?) : {e}")
    st.stop()

gp_options = gp_options_from(schedule)
gp_label = st.sidebar.selectbox(
    "Grand Prix",
    options=list(gp_options.keys()),
    index=min(len(gp_options) - 1, 12),  # Spa par défaut souvent vers le milieu
)
gp_name = gp_options[gp_label]

session_type = st.sidebar.selectbox(
    "Session",
    options=SESSION_TYPES,
    index=0,
    format_func=lambda x: SESSION_LABELS.get(x, x),
)

# Bouton pour déclencher le chargement.
# On n'écrit dans le session_state QUE lors d'un clic : sinon, une fois
# session_loaded posé, chaque interaction recopiait les widgets dans le state
# et changer de GP rechargeait tout sans clic.
load_btn = st.sidebar.button("🚀 Charger la session", type="primary", width="stretch")

if DATA_HOST["switched"]:
    st.sidebar.caption(
        f"🔀 Données via le **miroir FastF1** — le serveur F1 refuse l'IP de "
        f"l'hébergeur (HTTP {DATA_HOST['primary']}). Rien à faire, c'est transparent."
    )

if load_btn:
    st.session_state.session_loaded = True
    st.session_state.year = year
    st.session_state.gp_name = gp_name
    st.session_state.session_type = session_type

if not st.session_state.get("session_loaded"):
    # Écran de bienvenue : les mêmes réglages que la sidebar, au centre de la
    # page — un premier visiteur (sidebar repliée sur mobile) n'est pas perdu.
    st.markdown("### 👋 Bienvenue !")
    st.markdown(
        "Choisis la **session à analyser** ci-dessous, puis clique sur **Charger la session**. "
        "Tu retrouveras ces réglages à tout moment dans la barre latérale "
        "(sur mobile : icône **»** en haut à gauche)."
    )
    if MOBILE:
        c_y = c_gp = c_s = st  # empilé verticalement sur petit écran
    else:
        c_y, c_gp, c_s = st.columns([1, 2, 1])
    home_year = c_y.selectbox(
        "Saison", options=YEARS, index=YEARS.index(year), key="home_year",
        help="FastF1 supporte 2018 → présent.",
    )
    with st.spinner(f"Chargement du calendrier {home_year}…"):
        gp_options_h = gp_options_from(load_schedule(home_year))
    labels_h = list(gp_options_h.keys())
    home_gp_label = c_gp.selectbox(
        "Grand Prix", options=labels_h, key="home_gp",
        index=labels_h.index(gp_label) if gp_label in labels_h else min(len(labels_h) - 1, 12),
    )
    home_session = c_s.selectbox(
        "Session", options=SESSION_TYPES, index=SESSION_TYPES.index(session_type),
        format_func=lambda x: SESSION_LABELS.get(x, x), key="home_session",
    )
    if st.button("🚀 Charger la session", type="primary", key="home_load"):
        st.session_state.session_loaded = True
        st.session_state.year = home_year
        st.session_state.gp_name = gp_options_h[home_gp_label]
        st.session_state.session_type = home_session
        st.rerun()  # repart proprement, sans laisser le formulaire d'accueil affiché
    st.stop()

# Hint si les widgets de la sidebar diffèrent de la session actuellement chargée
if (year, gp_name, session_type) != (
    st.session_state.year, st.session_state.gp_name, st.session_state.session_type
):
    st.sidebar.info("⚙️ Paramètres modifiés — clique sur **Charger la session** pour les appliquer.")

# ============== CHARGEMENT DE LA SESSION ==============
try:
    with st.spinner(f"Chargement {st.session_state.gp_name} {st.session_state.year} {st.session_state.session_type}…"):
        session = load_session(
            st.session_state.year,
            st.session_state.gp_name,
            st.session_state.session_type,
        )
except Exception as e:
    st.error(f"❌ Impossible de charger la session : {e}")

    col_r1, col_r2 = st.columns(2)
    if col_r1.button("🔄 Réessayer", width="stretch"):
        st.rerun()
    if col_r2.button("🧹 Vider le cache et réessayer", width="stretch",
                     help="Un cache corrompu (redémarrage du serveur en pleine écriture) "
                          "peut bloquer tous les chargements."):
        st.cache_data.clear()
        st.cache_resource.clear()
        try:
            fastf1.Cache.clear_cache("cache_f1", deep=True)
        except Exception:
            pass
        st.rerun()

    with st.expander("🩺 Diagnostic — pourquoi ça échoue", expanded=True):
        details = getattr(e, "details", [])
        if details:
            st.markdown("**Ce que FastF1 a signalé pendant le chargement :**")
            st.code("\n".join(details[:15]))
        st.markdown("**Joignabilité des serveurs depuis l'hébergeur :**")
        with st.spinner("Test des serveurs…"):
            for line in _network_diagnostic():
                st.markdown(line)
        st.caption(
            f"FastF1 {fastf1.__version__} · Streamlit {st.__version__}. "
            "Si le serveur F1 répond ⛔ ou ❌ alors que le miroir répond ✅, "
            "c'est un blocage de l'hébergeur côté F1 (le repli miroir est censé "
            "prendre le relais). Si TOUT échoue, c'est le réseau sortant de "
            "Streamlit Cloud. Si tout est ✅, la session n'est probablement pas "
            "encore publiée côté F1."
        )
    st.stop()

# Position des virages — calculée UNE seule fois (le warning éventuel ne sort qu'ici)
circuit_info = safe_circuit_info(session)
corners_df = None
if circuit_info is not None and circuit_info.corners is not None and len(circuit_info.corners):
    corners_df = circuit_info.corners.sort_values("Distance").reset_index(drop=True)

# Rotation officielle du tracé (degrés) : oriente les cartes comme à la TV
TRACK_ROTATION = float(getattr(circuit_info, "rotation", 0) or 0) if circuit_info is not None else 0.0


def _rotate_xy(x, y):
    """Applique la rotation officielle du circuit aux coordonnées X/Y
    (télémétrie et virages partagent le même repère)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if not TRACK_ROTATION:
        return x, y
    rad = np.deg2rad(TRACK_ROTATION)
    return x * np.cos(rad) - y * np.sin(rad), x * np.sin(rad) + y * np.cos(rad)


def _add_corner_labels(fig, row=None, col=None):
    """Écrit T1, T2… sur une carte du circuit (si les positions sont dispo)."""
    if corners_df is None or "X" not in corners_df.columns:
        return
    cx, cy = _rotate_xy(corners_df["X"].values, corners_df["Y"].values)
    fig.add_trace(go.Scatter(
        x=cx, y=cy, mode="text",
        text=[f"T{int(r['Number'])}{r['Letter']}" for _, r in corners_df.iterrows()],
        textfont=dict(size=10, color="rgba(255,255,255,0.65)"),
        hoverinfo="skip", showlegend=False,
    ), row=row, col=col)


def _nearest_corner(d):
    """Étiquette du virage le plus proche d'une distance donnée (si dispo)."""
    if corners_df is None:
        return ""
    i = int((corners_df["Distance"] - d).abs().values.argmin())
    row = corners_df.iloc[i]
    return f" · ≈ T{int(row['Number'])}{row['Letter']}"


# Pilotes disponibles
drivers_in_session = sorted(session.laps["Driver"].dropna().unique().tolist())
if len(drivers_in_session) < 2:
    st.error("⚠️ Il faut au moins deux pilotes avec des tours dans cette session pour comparer "
             "(données partielles ou session pas encore roulée ?).")
    st.stop()

# Récupère les noms complets pour l'UX
driver_full = {}
for d in drivers_in_session:
    try:
        info = session.get_driver(d)
        driver_full[d] = f"{d} — {info['FullName']} ({info['TeamName']})"
    except Exception:
        driver_full[d] = d

# ============== HEADER DE SESSION (commun aux pages) ==============
ev = session.event
st.markdown(f"### {ev['EventName']} {st.session_state.year} — {st.session_state.session_type}")

# Durée de roulage effective (session_status : Started → Finished/Ends)
_dur = ""
try:
    _ss = session.session_status
    _t0 = _ss.loc[_ss["Status"] == "Started", "Time"].iloc[0]
    _t1 = _ss.loc[_ss["Status"].isin(("Finished", "Finalised", "Ends")), "Time"].iloc[-1]
    _dur = f" · ⏱️ ~{(_t1 - _t0).total_seconds() / 60:.0f} min de roulage"
except Exception:
    pass
st.caption(f"📍 {ev['Location']}, {ev['Country']} · {ev['EventDate'].strftime('%d %B %Y')}{_dur}")

# Bandeau météo (session.weather_data, échantillonné ~1/min sur la session)
try:
    _wx = session.weather_data
    if _wx is not None and len(_wx):
        _rain_pct = float(_wx["Rainfall"].mean() * 100) if "Rainfall" in _wx.columns else 0.0
        _rain_txt = (f"🌧️ pluie ~{_rain_pct:.0f} % de la session" if _rain_pct > 0
                     else "☀️ pas de pluie")
        st.caption(
            f"🌡️ Air {_wx['AirTemp'].mean():.0f} °C · Piste {_wx['TrackTemp'].min():.0f}–"
            f"{_wx['TrackTemp'].max():.0f} °C · 💨 vent {_wx['WindSpeed'].mean():.1f} m/s · {_rain_txt}"
        )
except Exception:
    pass


def team_color(team):
    """Couleur d'équipe : notre palette d'abord, sinon le référentiel officiel
    de fastf1.plotting (couvre toutes les équipes de toutes les saisons)."""
    if team in TEAM_COLORS:
        return TEAM_COLORS[team]
    try:
        import fastf1.plotting as f1plt
        c = f1plt.get_team_color(team, session=session)
        if c:
            return c
    except Exception:
        pass
    return "#888888"


def driver_color(drv):
    try:
        return team_color(session.get_driver(drv)["TeamName"])
    except Exception:
        return "#888888"


# ============== PAGE : ANALYSE DU STYLE ==============
def page_style():
    """Page d'analyse du style de pilotage : sélection de deux pilotes et de
    leurs tours, puis les onglets d'analyse (overlay, delta, g-g, feuille des
    temps, etc.). Les widgets sidebar de cette page (pilotes, tours) ne sont
    créés que lorsqu'elle est active."""
    # --- Sélection des pilotes ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Pilotes à comparer")
    default_d1 = "VER" if "VER" in drivers_in_session else drivers_in_session[0]
    default_d2 = "LEC" if "LEC" in drivers_in_session else drivers_in_session[1]
    if default_d2 == default_d1:
        default_d2 = next(x for x in drivers_in_session if x != default_d1)
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

    # Le même pilote deux fois crée un index dupliqué (Signatures) et des
    # colonnes de merge en double (pace tour par tour) → on bloque proprement.
    if d1 == d2:
        st.warning("⚠️ Sélectionne deux pilotes **différents** dans la barre latérale pour comparer.")
        st.stop()

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
        if fastest is None or pd.isna(fastest.get("LapTime")):
            # pick_fastest() renvoie None si aucun tour n'est marqué personal
            # best (ex. tous les tours valides supprimés pour track limits)
            fastest = valid.loc[valid["LapTime"].idxmin()]
        fastest_num = int(fastest["LapNumber"])

        options = []
        descriptions = {}
        for _, row in valid.iterrows():
            n = int(row["LapNumber"])
            lt = row["LapTime"].total_seconds()
            compound = str(row.get("Compound", "—"))[:1] if pd.notna(row.get("Compound")) else "—"
            is_fastest_marker = " ⚡" if n == fastest_num else ""
            acc = row.get("IsAccurate")
            warn = " ⚠" if (pd.notna(acc) and not bool(acc)) else ""
            time_str = f"{int(lt // 60)}:{lt % 60:06.3f}"
            options.append(n)
            descriptions[n] = f"L{n:>2} — {time_str} ({compound}){is_fastest_marker}{warn}"
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
        help="⚡ = tour le plus rapide · ⚠ = chrono jugé imprécis par FastF1 (in/out-lap, "
             "drapeau…). Tu peux choisir n'importe quel tour.",
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
        st.error("⚠️ Données manquantes pour le tour sélectionné.")
        st.stop()

    tel1 = lap1.get_car_data().add_distance()
    tel2 = lap2.get_car_data().add_distance()

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


    with st.expander("🏁 Classement de la session — meilleurs tours", expanded=False):
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
                width="stretch",
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

            # Tableau des zones intéressantes (distances reconstruites depuis les valeurs numériques)
            zones_df = pd.DataFrame(
                [(z[0], z[1], f"{z[2]}–{z[3]} m", z[4]) for z in circuit_info_data["zones"]],
                columns=["Zone", "Virage(s)", "Distance approx.", "Pourquoi c'est intéressant"],
            )
            st.dataframe(
                zones_df,
                width="stretch",
                hide_index=True,
                column_config={
                    "Zone": st.column_config.TextColumn("Zone", width="medium"),
                    "Virage(s)": st.column_config.TextColumn("Virage(s)", width="small"),
                    "Distance approx.": st.column_config.TextColumn("Distance approx.", width="small"),
                    "Pourquoi c'est intéressant": st.column_config.TextColumn("Pourquoi c'est intéressant", width="large"),
                },
            )
            st.caption(
                "💡 Les distances sont indicatives — ces zones sont disponibles en **presets** "
                "dans l'onglet **🔍 Zoom virage** pour les explorer directement."
            )
    else:
        st.info(f"ℹ️ Pas encore de briefing détaillé pour **{event_name}** dans la base. "
                f"Tu peux toujours explorer via les onglets ci-dessous.")

    # --- Métriques principales (+ portraits officiels si disponibles) ---
    def _headshot(drv):
        try:
            url = session.get_driver(drv).get("HeadshotUrl")
            return url if isinstance(url, str) and url.startswith("http") else None
        except Exception:
            return None

    col1, col2, col3, col4 = st.columns(4)
    for _c, _h in ((col1, _headshot(d1)), (col2, _headshot(d2))):
        if _h:
            _c.image(_h, width=72)
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
    tab_sheet, tab1, tab_map, tab2, tab_corners, tab3, tab_gg, tab4, tab5, tab_stint, tab_craft, tab_fit, tab6, tab_radio = st.tabs([
        "📋 Feuille des temps",
        "🎯 Overlay télémétrie",
        "🗺️ Vue circuit",
        "⏱️ Delta time",
        "🧠 Virage par virage",
        "🎨 Signatures de style",
        "⭕ Diagramme g-g",
        "🔍 Zoom virage",
        "📊 Secteurs",
        "📈 Évolution course",
        "🥊 Race craft",
        "🏟️ Auto vs circuit",
        "🕸️ Radar multi-pilotes",
        "📻 Radios",
    ])

    # --- TAB SHEET : FEUILLE DES TEMPS ---
    with tab_sheet:
        st.markdown(
            "La feuille des temps de la session, façon écran de timing : meilleurs tours, "
            "**meilleurs secteurs individuels** (pas forcément réalisés dans le même tour), "
            "tour théorique et vitesses de pointe. "
            "🟣 **Violet** = record de la session · 🟢 **vert** = record perso."
        )

        PURPLE, GREEN = "#C77DFF", "#4ADE80"
        _EPS = pd.Timedelta(milliseconds=1)

        laps_all = session.laps
        # Les tours supprimés (track limits) ne comptent pas pour les records
        laps_ok = laps_all[laps_all["Deleted"] != True] if "Deleted" in laps_all.columns else laps_all

        # Records absolus de la session (→ violet)
        sess_best = {
            "lap": laps_ok["LapTime"].min(),
            "S1": laps_ok["Sector1Time"].min(),
            "S2": laps_ok["Sector2Time"].min(),
            "S3": laps_ok["Sector3Time"].min(),
        }

        rows = []
        for drv in laps_all["Driver"].dropna().unique():
            ld = laps_ok[laps_ok["Driver"] == drv]
            timed = ld[ld["LapTime"].notna()]
            if timed.empty:
                continue
            best = timed.loc[timed["LapTime"].idxmin()]
            b1, b2, b3 = ld["Sector1Time"].min(), ld["Sector2Time"].min(), ld["Sector3Time"].min()
            theo = b1 + b2 + b3 if (pd.notna(b1) and pd.notna(b2) and pd.notna(b3)) else pd.NaT
            speed_cols = [c for c in ("SpeedST", "SpeedFL", "SpeedI1", "SpeedI2") if c in ld.columns]
            if speed_cols and ld[speed_cols].notna().any().any():
                vmax_drv = float(np.nanmax(ld[speed_cols].values.astype(float)))
            else:
                vmax_drv = np.nan
            try:
                info = session.get_driver(drv)
                name, team = info.get("FullName", drv), info.get("TeamName", "—")
            except Exception:
                name, team = drv, "—"
            rows.append({
                "Code": drv, "Pilote": name, "Équipe": team,
                "_best": best["LapTime"].total_seconds(),
                "best_td": best["LapTime"],
                "s1": b1, "s2": b2, "s3": b3, "theo": theo,
                "vmax": vmax_drv,
                "Pneu": ((str(best.get("Compound")) if pd.notna(best.get("Compound")) else "—")
                         + ("°" if pd.notna(best.get("FreshTyre")) and not best.get("FreshTyre") else "")),
                "Tours": int(timed["LapNumber"].nunique()),
            })

        if not rows:
            st.info("Aucun tour chronométré dans cette session.")
        else:
            dft = pd.DataFrame(rows).sort_values("_best").reset_index(drop=True)
            leader = dft["_best"].iloc[0]

            disp = pd.DataFrame({
                "Pos": dft.index + 1,
                "Pilote": dft["Code"] if MOBILE else dft["Pilote"],
                "Équipe": dft["Équipe"],
                "Meilleur tour": dft["best_td"].apply(_fmt_lap),
                "Écart": ["—"] + [f"+{t - leader:.3f}" for t in dft["_best"].iloc[1:]],
                "S1": dft["s1"].apply(_fmt_sec),
                "S2": dft["s2"].apply(_fmt_sec),
                "S3": dft["s3"].apply(_fmt_sec),
                "Théorique": dft["theo"].apply(_fmt_lap),
                "Δ théo": [f"+{(b - t.total_seconds()):.3f}" if pd.notna(t) else "—"
                           for b, t in zip(dft["_best"], dft["theo"])],
                "Vmax": [f"{v:.0f}" if pd.notna(v) else "—" for v in dft["vmax"]],
                "Pneu": dft["Pneu"],
                "Tours": dft["Tours"],
            })

            styles = pd.DataFrame("", index=disp.index, columns=disp.columns)
            purple_css = f"color: {PURPLE}; font-weight: bold"

            def _mark_purple(col_disp, series_td, best_td):
                if pd.isna(best_td):
                    return
                m = series_td.notna() & ((series_td - best_td).abs() < _EPS)
                styles.loc[m.values, col_disp] = purple_css

            _mark_purple("S1", dft["s1"], sess_best["S1"])
            _mark_purple("S2", dft["s2"], sess_best["S2"])
            _mark_purple("S3", dft["s3"], sess_best["S3"])
            _mark_purple("Meilleur tour", dft["best_td"], sess_best["lap"])

            # Surligne les deux pilotes sélectionnés, comme le classement du haut
            for drv_sel, colr in ((d1, c1), (d2, c2)):
                mask = (dft["Code"] == drv_sel).values
                if mask.any():
                    for c in disp.columns:
                        cur = styles.loc[mask, c].iloc[0]
                        styles.loc[mask, c] = (cur + "; " if cur else "") + f"background-color: {colr}30"

            # Mode compact : colonnes essentielles seulement (le tableau complet
            # reste à un toggle de distance dans la sidebar)
            if MOBILE:
                keep = ["Pos", "Pilote", "Meilleur tour", "Écart", "S1", "S2", "S3", "Δ théo", "Pneu"]
                disp, styles = disp[keep], styles[keep]

            show_table(
                disp.style.apply(lambda _: styles, axis=None),
                height=min(38 * (len(disp) + 1) + 3, 700),
            )
            st.caption(
                "**Théorique** = somme des meilleurs secteurs individuels du pilote · "
                "**Δ théo** = temps laissé sur la table (meilleur tour réel − tour théorique) · "
                "**Vmax** = vitesse de pointe max relevée (speed traps), en km/h · "
                "**°** = pneus rodés (pas neufs). "
                "Les tours supprimés (track limits) sont exclus des records."
            )

            # --- Recap tour par tour des deux pilotes sélectionnés ---
            st.markdown("---")
            st.markdown(f"#### 📜 Recap tour par tour — {d1} vs {d2}")
            st.caption(
                "🟣 Violet = record de la session · 🟢 vert = record perso · "
                "OUT = sortie des stands, IN = rentre aux stands · ° = pneus rodés · "
                "ligne barrée = tour supprimé (motif officiel dans la colonne Note)."
            )

            def _render_laps_recap(drv):
                ld = laps_all[laps_all["Driver"] == drv].sort_values("LapNumber")
                ld = ld[ld["LapTime"].notna()].reset_index(drop=True)
                if ld.empty:
                    st.info(f"Pas de tour chronométré pour {drv}.")
                    return
                deleted = (ld["Deleted"] == True).values if "Deleted" in ld.columns \
                    else np.zeros(len(ld), dtype=bool)

                # Records perso (hors tours supprimés)
                ok = ld[~deleted]
                pb = {
                    "lap": ok["LapTime"].min() if len(ok) else pd.NaT,
                    "S1": ok["Sector1Time"].min() if len(ok) else pd.NaT,
                    "S2": ok["Sector2Time"].min() if len(ok) else pd.NaT,
                    "S3": ok["Sector3Time"].min() if len(ok) else pd.NaT,
                }

                notes = []
                for _, r in ld.iterrows():
                    n = []
                    if pd.notna(r.get("PitOutTime")):
                        n.append("OUT")
                    if pd.notna(r.get("PitInTime")):
                        n.append("IN")
                    # Motif officiel de suppression (direction de course)
                    reason = r.get("DeletedReason")
                    if bool(r.get("Deleted")) and pd.notna(reason) and str(reason).strip():
                        n.append(str(reason).strip().capitalize())
                    notes.append(" / ".join(n))

                rec = pd.DataFrame({
                    "Tour": ld["LapNumber"].astype(int).values,
                    "Temps": [_fmt_lap(t) for t in ld["LapTime"]],
                    "S1": [_fmt_sec(t) for t in ld["Sector1Time"]],
                    "S2": [_fmt_sec(t) for t in ld["Sector2Time"]],
                    "S3": [_fmt_sec(t) for t in ld["Sector3Time"]],
                    "Pneu": [(str(c)[:1] if pd.notna(c) else "—")
                             + ("°" if pd.notna(c) and pd.notna(f) and not f else "")
                             for c, f in zip(ld["Compound"],
                                             ld["FreshTyre"] if "FreshTyre" in ld.columns
                                             else [np.nan] * len(ld))],
                    "Note": notes,
                })

                sty = pd.DataFrame("", index=rec.index, columns=rec.columns)
                for col_disp, col_src, key in [("Temps", "LapTime", "lap"),
                                               ("S1", "Sector1Time", "S1"),
                                               ("S2", "Sector2Time", "S2"),
                                               ("S3", "Sector3Time", "S3")]:
                    s = ld[col_src]
                    if pd.notna(pb[key]):
                        m_pers = s.notna() & ((s - pb[key]).abs() < _EPS)
                        sty.loc[m_pers.values, col_disp] = f"color: {GREEN}; font-weight: bold"
                    if pd.notna(sess_best[key]):
                        m_sess = s.notna() & ((s - sess_best[key]).abs() < _EPS)
                        # le violet (record session) écrase le vert (record perso)
                        sty.loc[m_sess.values, col_disp] = f"color: {PURPLE}; font-weight: bold"
                if deleted.any():
                    for c in rec.columns:
                        sty.loc[deleted, c] = sty.loc[deleted, c] + "; text-decoration: line-through; opacity: 0.45"

                show_table(
                    rec.style.apply(lambda _: sty, axis=None),
                    height=min(38 * (len(rec) + 1) + 3, 560),
                )

            if MOBILE:
                st.markdown(f"##### {d1}")
                _render_laps_recap(d1)
                st.markdown(f"##### {d2}")
                _render_laps_recap(d2)
            else:
                col_l, col_r = st.columns(2)
                with col_l:
                    st.markdown(f"##### {d1}")
                    _render_laps_recap(d1)
                with col_r:
                    st.markdown(f"##### {d2}")
                    _render_laps_recap(d2)

    # --- TAB 1 : OVERLAY ---
    with tab1:
        st.markdown("Vitesse, throttle, frein et rapport superposés sur la distance — survole les courbes pour les valeurs précises.")

        CH_TITLES = {"Speed": "Vitesse (km/h)", "Throttle": "Throttle (%)", "Brake": "Frein",
                     "nGear": "Rapport", "RPM": "RPM", "DRS": "DRS ouvert"}
        channels = [c for c in ("Speed", "Throttle", "Brake", "nGear", "RPM", "DRS")
                    if c in tel1.columns and c in tel2.columns]
        n_ch = len(channels)
        fig = make_subplots(
            rows=n_ch, cols=1, shared_xaxes=True, vertical_spacing=0.03,
            subplot_titles=[CH_TITLES[c] for c in channels],
        )
        for i, ch in enumerate(channels, start=1):
            # Brake/DRS (0/1) et nGear (entiers) : tracé en marches — sinon plotly
            # relie les échantillons par des rampes physiquement fausses
            shape = "hv" if ch in ("Brake", "nGear", "DRS") else "linear"
            fig.add_trace(go.Scatter(
                x=tel1["Distance"], y=_chan(tel1, ch), name=d1,
                line=dict(color=c1, width=1.8, shape=shape),
                legendgroup=d1, showlegend=(i == 1),
            ), row=i, col=1)
            fig.add_trace(go.Scatter(
                x=tel2["Distance"], y=_chan(tel2, ch), name=d2,
                line=dict(color=c2, width=1.8, shape=shape),
                legendgroup=d2, showlegend=(i == 1),
            ), row=i, col=1)

        # Lignes verticales aux virages
        if corners_df is not None:
            for _, corner in corners_df.iterrows():
                for r in range(1, n_ch + 1):
                    fig.add_vline(x=corner["Distance"], line=dict(color="white", width=0.5, dash="dot"),
                                  opacity=0.2, row=r, col=1)
            # Annotations virages sur le subplot du bas
            fig.update_xaxes(
                tickvals=corners_df["Distance"].tolist(),
                ticktext=[f"T{int(c['Number'])}{c['Letter']}" for _, c in corners_df.iterrows()],
                tickangle=45 if MOBILE else 0,  # T1…T19 se chevauchent sur petit écran
                row=n_ch, col=1,
            )

        fig.update_layout(
            height=170 * n_ch + 60, template="plotly_dark",
            hovermode="x unified",
            legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"),
            margin=dict(t=40, b=20, l=20, r=20),
        )
        fig.update_xaxes(title_text="Virage" if corners_df is not None else "Distance (m)", row=n_ch, col=1)
        plot(fig)

    # --- TAB MAP : VUE CIRCUIT ---
    with tab_map:
        st.markdown("Le tracé du circuit, colorié selon le paramètre choisi. Repère **où** chaque pilote roule fort, où il freine, où il prend du temps.")

        # Télémétrie complète avec X/Y (position GPS sur le tracé)
        tel1_full = lap1.get_telemetry()
        tel2_full = lap2.get_telemetry()

        color_by = st.radio(
            "Colorer par",
            options=["Speed", "Throttle", "Brake", "nGear", "DRS"],
            format_func=lambda x: {"Speed": "Vitesse", "Throttle": "Throttle",
                                   "Brake": "Frein", "nGear": "Rapport",
                                   "DRS": "DRS ouvert"}[x],
            horizontal=True,
            key="map_color_by",
        )

        # Échelle commune aux deux pilotes pour comparabilité
        vals1, vals2 = _chan(tel1_full, color_by), _chan(tel2_full, color_by)
        vmin = float(min(vals1.min(), vals2.min()))
        vmax = float(max(vals1.max(), vals2.max()))
        colorscale = "Plasma" if color_by == "Speed" else "Viridis"

        # Côte à côte sur desktop, empilés en mode compact (sinon chaque tracé
        # devient un timbre-poste sur un écran de téléphone)
        if MOBILE:
            fig_map = make_subplots(
                rows=2, cols=1,
                subplot_titles=(f"<b>{d1}</b>", f"<b>{d2}</b>"),
                vertical_spacing=0.06,
            )
        else:
            fig_map = make_subplots(
                rows=1, cols=2,
                subplot_titles=(f"<b>{d1}</b>", f"<b>{d2}</b>"),
                horizontal_spacing=0.04,
            )
        for i, (tel, vals) in enumerate([(tel1_full, vals1), (tel2_full, vals2)], start=1):
            r, c = (i, 1) if MOBILE else (1, i)
            xr, yr = _rotate_xy(tel["X"], tel["Y"])
            fig_map.add_trace(go.Scatter(
                x=xr, y=yr,
                mode="markers",
                marker=dict(
                    color=vals,
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
            ), row=r, col=c)
            _add_corner_labels(fig_map, row=r, col=c)
        # Aspect ratio égal pour ne pas déformer le tracé
        # (le subplot i utilise les axes x{i}/y{i} quelle que soit l'orientation)
        for i in (1, 2):
            r, c = (i, 1) if MOBILE else (1, i)
            fig_map.update_xaxes(scaleanchor=f"y{i if i > 1 else ''}", scaleratio=1,
                                 showticklabels=False, showgrid=False, zeroline=False,
                                 row=r, col=c)
            fig_map.update_yaxes(showticklabels=False, showgrid=False, zeroline=False,
                                 row=r, col=c)
        fig_map.update_layout(height=850 if MOBILE else 550, template="plotly_dark",
                              margin=dict(t=50, b=20, l=20, r=80))
        plot(fig_map)

        # --- Battle map : qui est plus rapide à chaque endroit du tracé ---
        st.markdown("---")
        st.markdown("#### ⚔️ Battle map — qui est plus rapide à chaque point du tracé")
        st.caption(
            f"Couleur {d1} = {d1} plus rapide à ce point · Couleur {d2} = {d2} plus rapide · "
            f"Blanc = égalité. L'intensité de la couleur = ampleur de l'écart."
        )

        # Interpole la vitesse de tel2 sur la grille de distance de tel1 pour pouvoir comparer
        tel2_speed_aligned = np.interp(
            tel1_full["Distance"].values,
            tel2_full["Distance"].values,
            tel2_full["Speed"].values,
        )
        speed_delta = tel1_full["Speed"].values - tel2_speed_aligned

        # Custom colorscale : c2 (négatif, d2 plus rapide) → blanc (0) → c1 (positif, d1 plus rapide)
        custom_scale = [
            [0.0, hex_to_rgb_str(c2)],
            [0.5, "rgb(255,255,255)"],
            [1.0, hex_to_rgb_str(c1)],
        ]
        # Échelle symétrique pour que 0 = blanc soit toujours au milieu
        abs_max = float(np.percentile(np.abs(speed_delta), 95))  # robuste aux outliers

        xb, yb = _rotate_xy(tel1_full["X"], tel1_full["Y"])
        fig_battle = go.Figure(go.Scatter(
            x=xb, y=yb,
            mode="markers",
            marker=dict(
                color=speed_delta,
                colorscale=custom_scale,
                cmin=-abs_max, cmax=abs_max,
                size=6,
                colorbar=dict(
                    title=dict(text="Δ vitesse<br>(km/h)", side="right"),
                    thickness=12,
                ),
            ),
            hovertemplate=f"Δ vitesse ({d1}−{d2}): %{{marker.color:+.1f}} km/h<extra></extra>",
        ))
        _add_corner_labels(fig_battle)
        fig_battle.update_xaxes(scaleanchor="y", scaleratio=1,
                                showticklabels=False, showgrid=False, zeroline=False)
        fig_battle.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)
        fig_battle.update_layout(height=600, template="plotly_dark",
                                 margin=dict(t=20, b=20, l=20, r=80))
        plot(fig_battle)

        with st.expander("💡 Comment lire la battle map vitesse"):
            st.markdown(f"""
            - **Zones colorées {d1}** : {d1} était plus rapide à cet endroit précis du tracé
            - **Zones colorées {d2}** : {d2} était plus rapide
            - **Zones blanches** : vitesses quasi identiques (égalité ou écart < 5 km/h)
            - **L'intensité** : plus la couleur est saturée, plus l'écart est grand à cet endroit

            ⚠️ **Attention** : la vitesse ne dit pas tout. Un pilote peut être plus rapide à un point précis mais avoir perdu du temps juste avant. Pour ça, regarde la heatmap de gain de temps ci-dessous.
            """)

        # --- Heatmap de gain/perte de temps ---
        st.markdown("---")
        st.markdown("#### 🌡️ Heatmap du gain de temps — qui prend du temps, où exactement")
        st.caption(
            "Mesure le **gain de temps local** à chaque point du tracé (dérivée du delta time cumulé "
            "par rapport à la distance, en ms par mètre). Bien plus parlant que la vitesse seule : "
            "un pilote peut être plus rapide à un point mais avoir perdu du temps juste avant. "
            "Ici on lit le **temps réellement gagné**, mètre par mètre."
        )

        try:
            delta_t, ref_tel_dt, _ = delta_time(lap1, lap2)
            dist_dt = np.asarray(ref_tel_dt["Distance"], dtype=float)
            # Gain local en s/m : gradient PAR RAPPORT À LA DISTANCE — sinon un gain
            # "par échantillon" est biaisé (un échantillon couvre plus de mètres à
            # haute vitesse qu'à basse vitesse).
            local_gain = np.gradient(np.asarray(delta_t, dtype=float), dist_dt)
            local_gain = np.nan_to_num(local_gain, nan=0.0, posinf=0.0, neginf=0.0)
            # Lissage léger pour atténuer le bruit
            local_gain_smooth = uniform_filter1d(local_gain, size=15)

            # FIX : delta_time() renvoie du car data SANS colonnes X/Y. Impossible de
            # tracer ref_tel_dt["X"] directement (KeyError → l'ancienne version tombait
            # systématiquement dans le except). On projette le gain sur la télémétrie
            # complète de lap1, qui contient la position sur le tracé.
            gain_ms = np.interp(tel1_full["Distance"].values, dist_dt, local_gain_smooth) * 1000

            # Convention : delta = t(D2) − t(D1). delta > 0 = D1 devant (cumulé).
            # gradient > 0 = l'avance de D1 grandit = D1 gagne du temps ici.
            custom_scale_time = [
                [0.0, hex_to_rgb_str(c2)],   # gradient < 0 = D2 gagne
                [0.5, "rgb(255,255,255)"],
                [1.0, hex_to_rgb_str(c1)],   # gradient > 0 = D1 gagne
            ]
            abs_max_gain = max(float(np.percentile(np.abs(gain_ms), 95)), 1e-3)  # garde-fou

            xh, yh = _rotate_xy(tel1_full["X"], tel1_full["Y"])
            fig_heat = go.Figure(go.Scatter(
                x=xh, y=yh,
                mode="markers",
                marker=dict(
                    color=gain_ms,
                    colorscale=custom_scale_time,
                    cmin=-abs_max_gain, cmax=abs_max_gain,
                    size=6,
                    colorbar=dict(
                        title=dict(text="Gain local<br>(ms/m)", side="right"),
                        thickness=12,
                        tickformat=".1f",
                    ),
                ),
                hovertemplate="Gain local: %{marker.color:+.2f} ms/m<extra></extra>",
            ))
            _add_corner_labels(fig_heat)
            fig_heat.update_xaxes(scaleanchor="y", scaleratio=1,
                                  showticklabels=False, showgrid=False, zeroline=False)
            fig_heat.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)
            fig_heat.update_layout(height=600, template="plotly_dark",
                                   margin=dict(t=20, b=20, l=20, r=80))
            plot(fig_heat)

            # Top zones de gain — dédupliquées (>=150 m entre deux zones), avec le
            # virage le plus proche pour se repérer
            gain_d1 = local_gain_smooth * 1000   # D1 gagne quand gradient > 0
            gain_d2 = -gain_d1                   # D2 gagne quand gradient < 0
            col_a, col_b = st.columns(2)
            for col, drv, g in [(col_a, d1, gain_d1), (col_b, d2, gain_d2)]:
                with col:
                    st.markdown(f"**🔝 Top zones de gain pour {drv}**")
                    idxs = _top_zones(g, dist_dt, k=3, min_sep=150.0)
                    if not idxs:
                        st.markdown("- Aucune zone de gain nette sur ce tour.")
                    for i in idxs:
                        st.markdown(
                            f"- Distance {dist_dt[i]:.0f} m{_nearest_corner(dist_dt[i])} : "
                            f"**+{g[i]:.1f} ms/m**"
                        )

            with st.expander("💡 Comment lire la heatmap de gain de temps"):
                st.markdown(f"""
                **C'est la visu la plus précise pour comprendre où la course se joue.**

                - **Zone colorée {d1}** : {d1} **gagne du temps** sur ce mètre de circuit (que ce soit en étant plus rapide en vitesse ou en ayant un meilleur angle d'attaque qui ouvre la suite)
                - **Zone colorée {d2}** : {d2} **gagne du temps** ici
                - **Zone blanche** : ils sont à égalité sur ce micro-segment
                - **Intensité** : ampleur du gain (en ms par **mètre** de circuit — comparable partout, y compris entre lignes droites et virages lents)

                **Combo gagnant à analyser** :
                1. Repère les **clusters** de couleur sur la heatmap (plusieurs dizaines de mètres consécutifs de même couleur)
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
        st.markdown(
            "Écart de temps cumulé le long du tour. **Courbe au-dessus de zéro = {} devant** "
            "(plus rapide à cet instant du tour), en-dessous = {} devant.".format(d1, d2)
        )

        try:
            delta, ref_tel, comp_tel = delta_time(lap1, lap2)
            # Convention FastF1 : delta = t(lap2) - t(lap1) = t(D2) - t(D1).
            # delta > 0  =>  D2 met plus de temps  =>  D1 devant.
            delta_arr = np.asarray(delta, dtype=float)
            xd = ref_tel["Distance"]

            fig = go.Figure()
            # Zone D1 devant (delta > 0)
            fig.add_trace(go.Scatter(
                x=xd, y=np.where(delta_arr >= 0, delta_arr, 0.0),
                mode="lines", line=dict(width=0), fill="tozeroy",
                fillcolor=hex_to_rgba(c1, 0.30), name=f"{d1} devant", hoverinfo="skip",
            ))
            # Zone D2 devant (delta < 0)
            fig.add_trace(go.Scatter(
                x=xd, y=np.where(delta_arr < 0, delta_arr, 0.0),
                mode="lines", line=dict(width=0), fill="tozeroy",
                fillcolor=hex_to_rgba(c2, 0.30), name=f"{d2} devant", hoverinfo="skip",
            ))
            # Courbe réelle
            fig.add_trace(go.Scatter(
                x=xd, y=delta_arr, mode="lines", line=dict(color="white", width=2),
                name="Δt cumulé",
                hovertemplate="%{x:.0f} m<br>Δt %{y:+.3f} s<extra></extra>",
            ))
            fig.add_hline(y=0, line=dict(color="grey", dash="dash"))
            fig.update_layout(
                height=450, template="plotly_dark",
                xaxis_title="Distance (m)",
                yaxis_title=f"Δt (s) · + = {d1} devant",
                hovermode="x unified",
                legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
            )
            plot(fig)
        except Exception as e:
            st.warning(f"Impossible de calculer le delta time : {e}")

    # --- TAB CORNERS : VIRAGE PAR VIRAGE ---
    with tab_corners:
        st.markdown(
            f"Pour chaque virage : **où** chacun commence à freiner, à quelle intensité, et **quand** il remet "
            f"les gaz. C'est ici qu'on voit objectivement qui freine tard et qui sort fort. "
            f"Analyse basée sur les tours sélectionnés dans la barre latérale."
        )
        if corners_df is None:
            st.info("FastF1 ne fournit pas la position des virages pour ce circuit.")
        else:
            cdf = corners_df
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
                st.dataframe(agg.round(1), width="stretch")

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
                plot(fig_c)

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
                    st.dataframe(disp, width="stretch", hide_index=True,
                                 height=min(38 * (len(disp) + 1) + 3, 600))
                    st.caption(
                        "**Frein** = distance avant l'apex où le freinage démarre (petit = freine tard). "
                        "**Gaz** = distance après l'apex où le throttle repasse ≥90 % (petit ou négatif = sort fort). "
                        "**—** = virage pris à fond. ⚠️ Échantillonnage télémétrie ~4-5 Hz : précision ±10-15 m "
                        "à haute vitesse — les écarts <5 m ne sont pas significatifs, les tendances sur "
                        "l'ensemble du tour le sont."
                    )

    # --- TAB 3 : SIGNATURES ---
    with tab3:
        st.markdown("Métriques chiffrées qui caractérisent le style de chaque pilote sur le tour sélectionné.")

        sig1 = style_sig(tel1, d1)
        sig2 = style_sig(tel2, d2)
        df = pd.DataFrame([sig1, sig2]).set_index("Pilote").T
        df["Δ (D1−D2)"] = (df[d1] - df[d2]).round(2)

        st.dataframe(df, width="stretch", height=320)

        # Interprétation
        with st.expander("💡 Comment lire ces signatures"):
            st.markdown("""
            - **`% temps full throttle`** plus élevé = style **binaire/agressif** (rotation-style typique).
            - **`% temps en coast`** plus élevé = pilote qui **module** entre frein et gaz, joue avec la rotation de l'arrière. Signature classique Verstappen.
            - **`Throttle ramp-up`** élevé = réapplication brutale du gaz (Verstappen). Bas = progression lisse (Hamilton, Norris).
            - **`V_min médiane courbes`** élevée = style **momentum** (porte de la vitesse en courbe, Norris, Hamilton). Basse = style **rotation** (V-shape, Verstappen).
            - **`Nb phases de freinage`** : indicateur indirect du nombre de virages où on freine. Diffère peu entre 2 pilotes sur même circuit, mais utile pour repérer des freinages "manqués" ou ajoutés.
            """)

    # --- TAB GG : DIAGRAMME G-G (CERCLE DE FRICTION) ---
    with tab_gg:
        st.markdown(
            "Le **cercle de friction** : accélération latérale vs longitudinale sur tout le tour. "
            "C'est la représentation canonique du style de pilotage — un pilote *V-shape* dessine "
            "une croix (freinage roues droites, puis rotation), un pilote *momentum* remplit les "
            "diagonales basses (trail-braking = frein et charge latérale simultanés). "
            "Basé sur les tours sélectionnés dans la barre latérale."
        )

        gg1 = gg2 = None
        try:
            with st.spinner("Reconstruction des accélérations…"):
                gg1 = compute_gg(lap1)
                gg2 = compute_gg(lap2)
        except Exception as e:
            st.warning(f"Impossible de calculer le diagramme g-g : {e}")

        if gg1 is None or gg2 is None:
            if gg1 is not None or gg2 is not None:
                st.warning("Flux position X/Y insuffisant pour un des deux tours — "
                           "essaie un autre tour ou une autre session.")
        else:
            fig_gg = go.Figure()

            # Cercles de référence 1 à 5 g
            for r in range(1, 6):
                fig_gg.add_shape(type="circle", x0=-r, y0=-r, x1=r, y1=r,
                                 line=dict(color="rgba(255,255,255,0.15)", width=1, dash="dot"))
                fig_gg.add_annotation(x=0, y=r, text=f"{r}g", showarrow=False, yshift=8,
                                      font=dict(color="rgba(255,255,255,0.35)", size=10))

            for gg, drv, col in [(gg1, d1, c1), (gg2, d2, c2)]:
                fig_gg.add_trace(go.Scatter(
                    x=gg["a_lat"], y=gg["a_long"], mode="markers",
                    marker=dict(color=col, size=3, opacity=0.25),
                    name=f"{drv} — points", legendgroup=drv,
                    customdata=gg["s"],
                    hovertemplate=(f"<b>{drv}</b><br>Distance: %{{customdata:.0f}} m<br>"
                                   "a_lat: %{x:+.2f} g<br>a_long: %{y:+.2f} g<extra></extra>"),
                ))
                env = gg_envelope(gg["a_lat"], gg["a_long"])
                if env is not None:
                    fig_gg.add_trace(go.Scatter(
                        x=env[0], y=env[1], mode="lines",
                        line=dict(color=col, width=2.5),
                        name=f"{drv} — enveloppe p95", legendgroup=drv,
                        hoverinfo="skip",
                    ))

            fig_gg.update_xaxes(title="Accélération latérale (g) · gauche ← → droite",
                                scaleanchor="y", scaleratio=1,
                                zeroline=True, zerolinecolor="rgba(255,255,255,0.3)")
            fig_gg.update_yaxes(title="Accélération longitudinale (g) · ↓ freinage / traction ↑",
                                zeroline=True, zerolinecolor="rgba(255,255,255,0.3)")
            fig_gg.update_layout(height=700, template="plotly_dark",
                                 legend=dict(orientation="h", y=1.06, x=0.5, xanchor="center"),
                                 margin=dict(t=30, b=20, l=20, r=20))
            plot(fig_gg)

            # --- Métriques dérivées ---
            def gg_metrics(gg):
                a_lat, a_long = gg["a_lat"], gg["a_long"]
                braking = a_long < -1.0                       # freinage effectif
                trail = braking & (np.abs(a_lat) > 1.5)       # freinage en appui = trail-braking
                neg = a_long[a_long < 0]
                return {
                    "g_brake": float(np.percentile(-neg, 99)) if neg.size else np.nan,
                    "g_lat": float(np.percentile(np.abs(a_lat), 99)),
                    "trail_pct": float(trail.sum() / braking.sum() * 100) if braking.any() else np.nan,
                }

            def _fmt(v, unit):
                return f"{v:.2f}{unit}" if pd.notna(v) else "—"

            met1, met2 = gg_metrics(gg1), gg_metrics(gg2)
            col_a, col_b = st.columns(2)
            for col, drv, met in [(col_a, d1, met1), (col_b, d2, met2)]:
                with col:
                    st.markdown(f"#### {drv}")
                    st.metric("g freinage max (p99)", _fmt(met["g_brake"], " g"))
                    st.metric("g latéral max (p99)", _fmt(met["g_lat"], " g"))
                    st.metric("Trail-braking (part du freinage avec >1.5 g latéral)",
                              f"{met['trail_pct']:.0f} %" if pd.notna(met["trail_pct"]) else "—")

            with st.expander("💡 Comment lire le diagramme g-g (et limites)"):
                st.markdown(f"""
                **Les deux archétypes** :
                - **V-shape (rotation)** : croix marquée — le gros du freinage se fait roues
                  droites (branche basse pure), la rotation à basse vitesse, puis traction.
                  Diagonales basses peu remplies, % trail-braking bas. Signature typique Verstappen.
                - **Momentum** : diagonales basses remplies — le pilote garde du frein en entrée
                  de virage pendant que la charge latérale monte. Enveloppe plus « ronde »,
                  % trail-braking élevé. Signature Norris / Hamilton.

                **À croiser avec** :
                - l'onglet **🧠 Virage par virage** : % trail-braking élevé + freinages tardifs
                  = late braker qui gère la rotation au frein. % bas + vmin élevées = momentum
                  pur qui prépare ses entrées.
                - l'**asymétrie gauche/droite** du nuage reflète simplement le circuit
                  (sens de rotation, répartition des virages) — comparez la *forme*, pas
                  l'orientation.
                - l'**enveloppe p95** : si celle de {d1} englobe celle de {d2} dans un quadrant,
                  {d1} exploite plus de grip dans cette phase (ou sa voiture en offre plus).

                ⚠️ **Limites** : position GPS ~4-5 Hz interpolée → les valeurs absolues sont
                indicatives (±10-15 %), le dénivelé n'est pas pris en compte (la compression
                d'Eau Rouge gonfle localement les g) et le lissage écrête les pics très brefs.
                La **comparaison relative** entre deux pilotes sur le même tour reste valide —
                c'est l'usage prévu. Comme pour l'onglet virage par virage : lisez les
                tendances, pas le centième.
                """)

    # --- TAB 4 : ZOOM ---
    with tab4:
        st.markdown("Zoome sur une portion spécifique du circuit pour décortiquer un virage.")

        max_dist = int(min(tel1["Distance"].max(), tel2["Distance"].max()))

        # Presets alimentés par les zones du briefing circuit (CIRCUITS_INFO)
        def _snap(v):
            return int(round(v / 50.0) * 50)

        presets = {"— Personnalisé —": None}
        if circuit_info_data:
            for z_name, z_turns, z_s, z_e, _ in circuit_info_data["zones"]:
                start = max(0, min(_snap(z_s), max_dist))
                end = max(0, min(_snap(z_e), max_dist))
                if start < end:
                    presets[f"{z_name} ({z_turns})"] = (start, end)

        def _apply_zoom_preset():
            rng = presets.get(st.session_state.get("zoom_preset"))
            if rng:
                st.session_state.zoom_range = rng
                st.session_state.zoom_label = st.session_state.zoom_preset

        # État initial + clamp (au cas où on a changé de circuit avec un ancien range)
        default_range = (int(max_dist * 0.1), int(max_dist * 0.25))
        lo, hi = st.session_state.get("zoom_range", default_range)
        lo, hi = max(0, min(int(lo), max_dist)), max(0, min(int(hi), max_dist))
        if lo >= hi:
            lo, hi = default_range
        st.session_state.zoom_range = (lo, hi)
        st.session_state.setdefault("zoom_label", "Zoom virage")

        col_z1, col_z2 = st.columns(2)
        with col_z1:
            st.selectbox(
                "Zone prédéfinie",
                options=list(presets.keys()),
                key="zoom_preset",
                on_change=_apply_zoom_preset,
                help="Zones du briefing circuit — sélectionne puis affine avec le slider.",
            )
        with col_z2:
            z_label = st.text_input("Étiquette de la section", key="zoom_label")

        z_range = st.slider(
            "Plage de distance (m)",
            min_value=0, max_value=max_dist,
            step=50,
            key="zoom_range",
        )

        z_start, z_end = z_range
        m1 = (tel1["Distance"] > z_start) & (tel1["Distance"] < z_end)
        m2 = (tel2["Distance"] > z_start) & (tel2["Distance"] < z_end)

        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
            subplot_titles=("Vitesse", "Throttle", "Frein"),
        )
        for i, ch in enumerate(["Speed", "Throttle", "Brake"], start=1):
            shape = "hv" if ch == "Brake" else "linear"  # frein 0/1 → marches
            fig.add_trace(go.Scatter(x=tel1.loc[m1, "Distance"], y=_chan(tel1.loc[m1], ch),
                                     name=d1, line=dict(color=c1, width=2, shape=shape),
                                     legendgroup=d1, showlegend=(i == 1)),
                          row=i, col=1)
            fig.add_trace(go.Scatter(x=tel2.loc[m2, "Distance"], y=_chan(tel2.loc[m2], ch),
                                     name=d2, line=dict(color=c2, width=2, shape=shape),
                                     legendgroup=d2, showlegend=(i == 1)),
                          row=i, col=1)
        fig.update_layout(height=600, template="plotly_dark", hovermode="x unified",
                          title=f"{z_label} ({z_start}-{z_end} m)")
        fig.update_xaxes(title_text="Distance (m)", row=3, col=1)
        plot(fig)

    # --- TAB 5 : SECTEURS ---
    with tab5:
        st.markdown("Comparaison secteur par secteur des tours sélectionnés.")

        def _sec(td):
            """Temps de secteur en secondes, nan si manquant (NaT arrive sur certains tours)."""
            return td.total_seconds() if pd.notna(td) else np.nan

        sectors_data = []
        for i in (1, 2, 3):
            s1_val = _sec(lap1[f"Sector{i}Time"])
            s2_val = _sec(lap2[f"Sector{i}Time"])
            if np.isnan(s1_val) or np.isnan(s2_val):
                faster = "—"
            elif s1_val == s2_val:
                faster = "Égalité"
            else:
                faster = d2 if s1_val > s2_val else d1
            sectors_data.append({"Secteur": f"S{i}", d1: s1_val, d2: s2_val,
                                 "Δ": s1_val - s2_val,
                                 "Plus rapide": faster})
        df_sec = pd.DataFrame(sectors_data).set_index("Secteur")

        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.dataframe(df_sec.round(3), width="stretch")
        with col_b:
            bar_colors = [c2 if d > 0 else c1 for d in df_sec["Δ"]]
            fig = go.Figure(go.Bar(
                x=df_sec.index, y=df_sec["Δ"],
                marker_color=bar_colors,
                text=[f"{d:+.3f}s" if pd.notna(d) else "—" for d in df_sec["Δ"]],
                textposition="outside",
                cliponaxis=False,  # sinon le label de la plus grande barre est rogné
            ))
            fig.add_hline(y=0, line=dict(color="white"))
            fig.update_layout(
                height=400, template="plotly_dark",
                yaxis_title=f"Δ {d1} − {d2} (s)",
                title=f"Écart par secteur ({d2 if df_sec['Δ'].sum() > 0 else d1} plus rapide au total)",
            )
            plot(fig)

    # --- TAB STINT : ÉVOLUTION COURSE ---
    with tab_stint:
        st.markdown("Évolution des temps au tour par relais pneu (stint). **Principalement utile en course** (R), mais marche aussi sur les longs runs FP2.")

        def get_stint_laps(drv):
            """Récupère les tours valides d'un pilote avec infos de stint.
            FIX : exclusion des in-laps ET des out-laps — l'ancien filtre
            `PitOutTime.isna() | (LapNumber > 1)` gardait quasiment tout et
            polluait moyenne / écart-type / dégradation."""
            laps_drv = session.laps.pick_drivers(drv)
            valid = laps_drv.loc[laps_drv["LapTime"].notna()].copy()
            if "PitOutTime" in valid.columns and "PitInTime" in valid.columns:
                valid = valid.loc[valid["PitOutTime"].isna() & valid["PitInTime"].isna()]
            valid["LapTimeSeconds"] = valid["LapTime"].dt.total_seconds()
            return valid

        laps_d1_s = get_stint_laps(d1)
        laps_d2_s = get_stint_laps(d2)

        if len(laps_d1_s) < 2 and len(laps_d2_s) < 2:
            st.info("Pas assez de tours pour analyser l'évolution. Cet onglet est conçu pour les sessions de type course ou long-run.")
        else:
            # Option : filtrer les tours non représentatifs
            col_opt1, col_opt2 = st.columns([1, 3])
            with col_opt1:
                filter_outliers = st.checkbox("Filtrer outliers", value=True,
                                              help="Exclut les tours sous SC/VSC/drapeau rouge (statut piste "
                                                   "officiel) puis les tours > 110% de la médiane, du "
                                                   "graphique ET des stats.")

            def _is_neutralized(ts):
                """TrackStatus FastF1 = concaténation de codes : 4 = Safety Car,
                5 = drapeau rouge, 6/7 = Virtual Safety Car (déploiement/fin)."""
                return any(c in str(ts) for c in ("4", "5", "6", "7"))

            # Le filtre s'applique en amont — graphique, stats par stint et pace
            # tour par tour restent cohérents entre eux. Le statut piste officiel
            # attrape les tours neutralisés ; le seuil médiane garde le reste
            # (tête-à-queue, trafic, tour raté).
            def _drop_outliers(laps_drv):
                if not filter_outliers:
                    return laps_drv
                if "TrackStatus" in laps_drv.columns:
                    laps_drv = laps_drv.loc[~laps_drv["TrackStatus"].apply(_is_neutralized)]
                if len(laps_drv) > 3:
                    median = laps_drv["LapTimeSeconds"].median()
                    laps_drv = laps_drv.loc[laps_drv["LapTimeSeconds"] < median * 1.10]
                return laps_drv

            laps_d1_s = _drop_outliers(laps_d1_s)
            laps_d2_s = _drop_outliers(laps_d2_s)

            # --- Graphique principal ---
            fig_stint = go.Figure()

            for laps_drv, drv, line_color in [(laps_d1_s, d1, c1), (laps_d2_s, d2, c2)]:
                if len(laps_drv) == 0:
                    continue

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

            # Contexte de course en fond : périodes SC/VSC (statut piste), pluie
            # (météo) et température de piste (axe secondaire) — ce qui explique
            # les tours « bizarres » sans avoir à les deviner.
            def _lap_ranges(flags):
                """Plages contiguës de tours où flags (Series bool indexée par
                LapNumber) est vraie."""
                ranges, start, prev = [], None, None
                for n in sorted(flags.index):
                    if flags[n] and start is None:
                        start = n
                    elif not flags[n] and start is not None:
                        ranges.append((start, prev))
                        start = None
                    prev = n
                if start is not None:
                    ranges.append((start, prev))
                return ranges

            la_all = session.laps
            if "TrackStatus" in la_all.columns:
                sc_flags = la_all.groupby("LapNumber")["TrackStatus"].agg(
                    lambda s: any(_is_neutralized(v) for v in s))
                for a, b in _lap_ranges(sc_flags):
                    fig_stint.add_vrect(x0=a - 0.5, x1=b + 0.5, line_width=0,
                                        fillcolor="rgba(255,180,0,0.12)",
                                        annotation_text="SC/VSC",
                                        annotation_position="top left",
                                        annotation_font=dict(size=9, color="rgba(255,200,80,0.9)"))
            try:
                wx_s = session.weather_data
            except Exception:
                wx_s = None
            if wx_s is not None and len(wx_s) and "Rainfall" in wx_s.columns:
                lap_t = la_all.dropna(subset=["Time"]).groupby("LapNumber")["Time"].max().dt.total_seconds()
                if len(lap_t) > 1:
                    # Mappe l'horodatage météo (temps session) → numéro de tour
                    wx_lap = np.interp(wx_s["Time"].dt.total_seconds(),
                                       lap_t.values, lap_t.index.values)
                    if bool(wx_s["Rainfall"].any()):
                        rain_flags = pd.Series(False, index=lap_t.index)
                        for ln in np.round(wx_lap[wx_s["Rainfall"].values.astype(bool)]).astype(int):
                            if ln in rain_flags.index:
                                rain_flags[ln] = True
                        for a, b in _lap_ranges(rain_flags):
                            fig_stint.add_vrect(x0=a - 0.5, x1=b + 0.5, line_width=0,
                                                fillcolor="rgba(80,140,255,0.12)",
                                                annotation_text="🌧",
                                                annotation_position="bottom left")
                    fig_stint.add_trace(go.Scatter(
                        x=wx_lap, y=wx_s["TrackTemp"], yaxis="y2", mode="lines",
                        line=dict(color="rgba(255,255,255,0.35)", width=1.5, dash="dot"),
                        name="Temp. piste (°C)",
                        hovertemplate="Temp. piste: %{y:.0f} °C<extra></extra>",
                    ))

            fig_stint.update_layout(
                height=500, template="plotly_dark",
                xaxis_title="Numéro de tour",
                yaxis_title="Temps au tour (s)",
                yaxis2=dict(title="Temp. piste (°C)", overlaying="y", side="right",
                            showgrid=False, tickfont=dict(color="rgba(255,255,255,0.5)")),
                hovermode="closest",
                legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
            )
            plot(fig_stint)

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
                st.dataframe(df_stints, width="stretch", hide_index=True)

                with st.expander("💡 Comment lire ces stats"):
                    st.markdown(f"""
                    - **Best** : meilleur tour du stint — révèle la **pace pure** quand les pneus sont au top
                    - **Moyenne** : pace réelle sur l'ensemble du stint — plus représentative pour comparer
                    - **Écart-type** : indicateur de **consistance**. Bas = pilote métronome (Hamilton, Russell typiquement). Élevé = pilote qui prend des risques ou se bat avec sa voiture
                    - **Dégradation** : pente de la régression linéaire (ms perdues par tour qui passe).
                        - **< +30 ms/tour** : excellente gestion pneus (Verstappen, Hamilton historiquement)
                        - **+30 à +80 ms/tour** : normal
                        - **> +80 ms/tour** : pilote qui en demande trop à ses pneus, ou stratégie risquée
                        - ⚠️ En course, l'allègement carburant fait gagner ~50-80 ms/tour : la pente
                          affichée **sous-estime la vraie dégradation pneu** d'autant. La comparaison
                          entre les deux pilotes reste valide (même effet des deux côtés), les seuils
                          absolus ci-dessus sont à lire avec cette réserve.

                    **Croise ces deux infos** : un pilote avec un meilleur **Best** mais une moins bonne **Moyenne** est rapide quand il pousse mais ne tient pas — il sera défavorisé sur des longues séquences. C'est typiquement le profil "qualif > course".
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
                        hovertemplate="Tour %{x}<br>Δ: %{y:+.3f}s<extra></extra>",
                    ))
                    fig_delta_stint.add_hline(y=0, line=dict(color="white", width=0.8))
                    fig_delta_stint.update_layout(
                        height=350, template="plotly_dark",
                        xaxis_title="Tour",
                        yaxis_title=f"Δ {d1} − {d2} (s)",
                        title=f"Barres positives = {d2} plus rapide · Barres négatives = {d1} plus rapide",
                    )
                    plot(fig_delta_stint)

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
                    plot(fig_p)

                    # Métriques attaque / défense
                    def pct(a, b):
                        return f"{a}/{b} ({a / b * 100:.0f} %)" if b else "—"

                    # Pénalités relevées par la direction de course, par pilote
                    try:
                        rcm_pen = session.race_control_messages
                        if rcm_pen is not None and len(rcm_pen):
                            rcm_pen = rcm_pen[rcm_pen["Message"].astype(str)
                                              .str.contains("PENALTY", na=False)]
                        else:
                            rcm_pen = None
                    except Exception:
                        rcm_pen = None

                    col_a, col_b = st.columns(2)
                    for col, m, drv in [(col_a, m1, d1), (col_b, m2, d2)]:
                        with col:
                            st.markdown(f"#### {drv}")
                            st.metric("Tours sous pression (<1 s derrière)", m["press"])
                            st.metric("Défenses réussies", pct(m["held"], m["press"]))
                            st.metric("Tours à l'attaque (<1 s devant)", m["attack"])
                            st.metric("Attaques converties en dépassement", pct(m["conv"], m["attack"]))
                            st.metric("Positions gagnées / perdues en piste", f"+{m['gained']} / −{m['lost']}")
                            if rcm_pen is not None:
                                mine = rcm_pen[rcm_pen["Message"].astype(str)
                                               .str.contains(f"({drv})", regex=False, na=False)]
                                st.metric("Pénalités (direction de course)", int(len(mine)))
                                for _, pm in mine.iterrows():
                                    st.caption(f"• {str(pm['Message']).capitalize()}")

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
            plot(fig_f)
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

    # --- TAB 6 : RADAR ---
    with tab6:
        st.markdown("Compare jusqu'à 6 pilotes en visu radar. Idéal pour repérer des archétypes opposés.")

        # FIX : si d1/d2 est NOR, HAM ou ALO, la liste par défaut contenait un doublon
        # → index dupliqué après set_index("Pilote") → df_n.loc[drv] renvoyait un
        # DataFrame (pas de .tolist()) → AttributeError. dict.fromkeys déduplique
        # en préservant l'ordre.
        default_radar = list(dict.fromkeys(
            d for d in [d1, d2, "NOR", "HAM", "ALO"] if d in drivers_in_session
        ))[:6]
        drivers_radar = st.multiselect(
            "Pilotes",
            options=drivers_in_session,
            default=default_radar,
            max_selections=6,
            format_func=lambda x: driver_full.get(x, x),
        )
        drivers_radar = list(dict.fromkeys(drivers_radar))  # ceinture + bretelles

        if len(drivers_radar) < 2:
            st.warning("Sélectionne au moins 2 pilotes.")
        else:
            def sig_for(drv):
                lap = session.laps.pick_drivers(drv).pick_fastest()
                if lap is None or pd.isna(lap.get("LapTime")):
                    return None
                tel = lap.get_car_data().add_distance()
                # FIX : mean() d'un array vide → nan, et nan est truthy, donc
                # l'ancien `... .mean() or 0` ne protégeait rien. Garde explicite.
                dthr = np.diff(tel["Throttle"].values)
                rising = dthr[dthr > 0]
                ramp = float(rising.mean()) if rising.size else 0.0
                return {
                    "Pilote": drv,
                    "Vmax": float(tel["Speed"].max()),
                    "V_min courbes": float(tel.loc[tel["Speed"] < tel["Speed"].quantile(0.30), "Speed"].median()),
                    "Full throttle %": float((tel["Throttle"] >= 99).mean() * 100),
                    "Coast time %": float(((tel["Throttle"] < 5) & (tel["Brake"] == 0)).mean() * 100),
                    "Brake %": float((tel["Brake"] > 0).mean() * 100),
                    "Throttle ramp-up": ramp,
                }

            sigs = [s for s in (sig_for(d) for d in drivers_radar) if s is not None]
            if not sigs:
                st.error("Aucun pilote avec données valides.")
            else:
                df_m = pd.DataFrame(sigs).set_index("Pilote")
                # Normalisation 0-1
                df_n = (df_m - df_m.min()) / (df_m.max() - df_m.min() + 1e-9)

                fig = go.Figure()
                dashes = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]
                for k, drv in enumerate(df_n.index):
                    vals = df_n.loc[drv].tolist()
                    vals += vals[:1]
                    labels = df_n.columns.tolist() + [df_n.columns[0]]
                    fig.add_trace(go.Scatterpolar(
                        r=vals, theta=labels, fill="toself",
                        name=drv,
                        # tiret différent par trace : deux coéquipiers (même
                        # couleur équipe) restent discernables
                        line=dict(color=driver_color(drv), width=2,
                                  dash=dashes[k % len(dashes)]),
                        opacity=0.7,
                    ))
                fig.update_layout(
                    height=600, template="plotly_dark",
                    polar=dict(radialaxis=dict(visible=True, range=[0, 1], showticklabels=False)),
                    title="Signatures de style — comparaison normalisée",
                )
                plot(fig)

                with st.expander("Valeurs brutes"):
                    st.dataframe(df_m.round(2), width="stretch")

    # --- TAB RADIO : RADIOS D'ÉQUIPE ---
    with tab_radio:
        st.markdown(
            f"Les échanges radio de **{d1}** et **{d2}** publiés par la FOM — la sélection "
            f"officielle des « meilleurs moments » (tout n'est pas diffusé). "
            f"**L** = tour en cours au moment du message."
        )
        with st.spinner("Recherche des radios d'équipe…"):
            radio_df = load_team_radio(st.session_state.year, st.session_state.gp_name,
                                       st.session_state.session_type)
        if radio_df is None or radio_df.empty:
            st.info("📻 Pas de radios publiées pour cette session — flux indisponible "
                    "(fréquent avant 2022) ou pas encore mis en ligne côté F1.")
        else:
            def _drv_clips(drv):
                clips = radio_df[radio_df["Pilote"] == drv]
                st.markdown(f"##### {drv} — {len(clips)} clip(s)")
                if clips.empty:
                    st.info(f"Aucun clip publié pour {drv} sur cette session.")
                else:
                    _render_radio_clips(clips)

            if MOBILE:
                _drv_clips(d1)
                st.markdown("---")
                _drv_clips(d2)
            else:
                col_l, col_r = st.columns(2)
                with col_l:
                    _drv_clips(d1)
                with col_r:
                    _drv_clips(d2)
            st.caption("Audio lu en direct depuis les serveurs F1 (rien n'est stocké par l'app).")

# ============== PAGE : TIMING SESSION ==============
def page_timing():
    """Récap de session façon écran de timing : ordre d'arrivée, intervalles,
    pneus, meilleur tour, dernier tour bouclé et secteurs (derniers + records
    perso), badges couleur équipe, fonds violet (record session) / vert
    (record perso). Les mini-secteurs n'existent que dans le flux live
    SignalR — absents des données post-session FastF1, donc non affichés."""
    st.markdown(f"## 📊 Overview — {SESSION_LABELS.get(st.session_state.session_type, st.session_state.session_type)}")

    VIOLET_BG = "background-color: #7C3AED; color: #FFFFFF; font-weight: bold; border-radius: 6px; text-align: center"
    GREEN_BG = "background-color: #22C55E; color: #111111; font-weight: bold; border-radius: 6px; text-align: center"
    _EPS = pd.Timedelta(milliseconds=1)
    is_race = st.session_state.session_type in ("R", "S")

    laps_all = session.laps
    laps_ok = laps_all[laps_all["Deleted"] != True] if "Deleted" in laps_all.columns else laps_all
    sess_best = {
        "lap": laps_ok["LapTime"].min(),
        "S1": laps_ok["Sector1Time"].min(),
        "S2": laps_ok["Sector2Time"].min(),
        "S3": laps_ok["Sector3Time"].min(),
    }

    # Résultats officiels (positions d'arrivée, écarts, statuts) si disponibles
    try:
        results = session.results
        if results is None or results.empty or results["Position"].isna().all():
            results = None
    except Exception:
        results = None

    def _res_for(drv):
        if results is None:
            return None
        m = results[results["Abbreviation"] == drv]
        return m.iloc[0] if len(m) else None

    rows = []
    for drv in laps_all["Driver"].dropna().unique():
        ld_raw = laps_all[laps_all["Driver"] == drv]
        ld_ok = laps_ok[laps_ok["Driver"] == drv]
        timed_ok = ld_ok[ld_ok["LapTime"].notna()]
        timed_raw = ld_raw[ld_raw["LapTime"].notna()].sort_values("LapNumber")
        if timed_raw.empty:
            continue
        best_td = timed_ok["LapTime"].min() if len(timed_ok) else pd.NaT
        last = timed_raw.iloc[-1]
        # Pneu courant : compound + âge du dernier tour
        comp = str(last.get("Compound", "—")) if pd.notna(last.get("Compound")) else "—"
        tyre_age = int(last["TyreLife"]) if pd.notna(last.get("TyreLife")) else None
        res = _res_for(drv)
        rows.append({
            "drv": drv,
            "res_pos": float(res["Position"]) if res is not None and pd.notna(res.get("Position")) else np.nan,
            "grid": float(res["GridPosition"]) if res is not None and pd.notna(res.get("GridPosition")) else np.nan,
            "res_status": str(res.get("Status", "")) if res is not None else "",
            "fin_laps": int(last["LapNumber"]),
            "fin_t": last["Time"].total_seconds() if pd.notna(last.get("Time")) else np.nan,
            "best": best_td,
            "best_s": best_td.total_seconds() if pd.notna(best_td) else np.inf,
            "last_lap": last["LapTime"],
            "lS1": last.get("Sector1Time"), "lS2": last.get("Sector2Time"), "lS3": last.get("Sector3Time"),
            "bS1": ld_ok["Sector1Time"].min(), "bS2": ld_ok["Sector2Time"].min(), "bS3": ld_ok["Sector3Time"].min(),
            "pb_lap": best_td,
            "comp": comp, "tyre_age": tyre_age,
            "pits": int(ld_raw["PitInTime"].notna().sum()),
            "laps": int(timed_raw["LapNumber"].nunique()),
        })

    if not rows:
        st.info("Aucun tour chronométré dans cette session.")
        return

    dfr = pd.DataFrame(rows)
    # Ordre : positions officielles si dispo, sinon meilleur tour
    if is_race and dfr["res_pos"].notna().any():
        dfr = dfr.sort_values(["res_pos", "best_s"], na_position="last")
    elif is_race:
        dfr = dfr.sort_values(["fin_laps", "fin_t"], ascending=[False, True], na_position="last")
    else:
        dfr = dfr.sort_values("best_s")
    dfr = dfr.reset_index(drop=True)

    # Écarts au leader et intervalles (+ version numérique pour le schéma)
    gaps, intervals, gap_num = [], [], []
    if is_race:
        # FIX : results["Time"] (écart officiel) est vide pour les sessions
        # Sprint côté FastF1 → tout ressortait NaT. On reconstruit l'écart à
        # l'arrivée depuis les temps de passage de la ligne (laps), toujours
        # présents : pilotes dans le même tour que le leader → différence des
        # passages au dernier tour ; sinon "+N tour(s)" ou statut officiel.
        lead_laps = dfr["fin_laps"].iloc[0]
        lead_t = dfr["fin_t"].iloc[0]
        for i, r in dfr.iterrows():
            if i == 0:
                gaps.append("Leader")
                gap_num.append(0.0)
            elif (pd.notna(r["fin_t"]) and pd.notna(lead_t)
                  and pd.notna(r["fin_laps"]) and r["fin_laps"] == lead_laps):
                g = r["fin_t"] - lead_t
                gaps.append(f"+{g:.3f}")
                gap_num.append(g)
            else:
                status = r["res_status"]
                if status and status not in ("Finished", "Lapped", "nan", ""):
                    gaps.append(status)
                elif pd.notna(r["fin_laps"]) and pd.notna(lead_laps):
                    diff = int(lead_laps - r["fin_laps"])
                    gaps.append(f"+{diff} tour{'s' if diff > 1 else ''}")
                else:
                    gaps.append("—")
                gap_num.append(np.nan)
        for i in range(len(dfr)):
            if i == 0:
                intervals.append("Interval")
            elif np.isfinite(gap_num[i]) and np.isfinite(gap_num[i - 1]):
                intervals.append(f"+{gap_num[i] - gap_num[i - 1]:.3f}")
            else:
                intervals.append(gaps[i])
    else:
        leader_best = dfr["best_s"].iloc[0]
        for i, r in dfr.iterrows():
            if i == 0:
                gaps.append("Leader")
                intervals.append("Interval")
                gap_num.append(0.0)
            else:
                if np.isfinite(r["best_s"]):
                    gaps.append(f"+{r['best_s'] - leader_best:.3f}")
                    gap_num.append(r["best_s"] - leader_best)
                else:
                    gaps.append("—")
                    gap_num.append(np.nan)
                prev = dfr["best_s"].iloc[i - 1]
                intervals.append(f"+{r['best_s'] - prev:.3f}"
                                 if np.isfinite(r["best_s"]) and np.isfinite(prev) else "—")

    def _tyre_str(r):
        letter = r["comp"][:1] if r["comp"] != "—" else "—"
        return f"{r['tyre_age']} {letter}" if r["tyre_age"] is not None else letter

    disp = pd.DataFrame({
        "Pos": dfr.index + 1,
        "Pilote": dfr["drv"],
        "Pit": dfr["pits"],
        "Interval": intervals,
        "Écart": gaps,
        "Pneu": dfr.apply(_tyre_str, axis=1),
        "Best lap": dfr["best"].apply(_fmt_lap),
        "Dernier tour": dfr["last_lap"].apply(_fmt_lap),
        "S1": dfr["lS1"].apply(_fmt_sec),
        "S2": dfr["lS2"].apply(_fmt_sec),
        "S3": dfr["lS3"].apply(_fmt_sec),
        "S1★": dfr["bS1"].apply(_fmt_sec),
        "S2★": dfr["bS2"].apply(_fmt_sec),
        "S3★": dfr["bS3"].apply(_fmt_sec),
    })

    if is_race and dfr["grid"].notna().any():
        # Δ vs grille : places gagnées (vert) / perdues (rouge) depuis le départ
        def _grid_cell(r):
            if pd.isna(r["grid"]) or pd.isna(r["res_pos"]):
                return "—"
            g = int(r["grid"])
            if g <= 0:
                return "PL"  # départ de la pit lane
            d = g - int(r["res_pos"])
            return f"+{d}" if d > 0 else (f"−{abs(d)}" if d < 0 else "=")

        disp.insert(2, "Δ Grille", [_grid_cell(r) for _, r in dfr.iterrows()])

    styles = pd.DataFrame("", index=disp.index, columns=disp.columns)

    if "Δ Grille" in disp.columns:
        for i, v in enumerate(disp["Δ Grille"]):
            if v.startswith("+"):
                styles.loc[i, "Δ Grille"] = "color: #4ADE80; font-weight: bold"
            elif v.startswith("−"):
                styles.loc[i, "Δ Grille"] = "color: #F87171; font-weight: bold"

    # Badge pilote : fond couleur équipe
    for i, drv in enumerate(dfr["drv"]):
        colr = driver_color(drv)
        styles.loc[i, "Pilote"] = (f"background-color: {colr}; color: {text_on(colr)}; "
                                   f"font-weight: bold; border-radius: 6px; text-align: center")
        styles.loc[i, "Pneu"] = f"color: {compound_color(dfr['comp'].iloc[i])}; font-weight: bold"

    def _mark(col_disp, series, best_session, best_perso=None):
        """Fond violet = record session ; fond vert = record perso du pilote."""
        for i, v in enumerate(series):
            if pd.isna(v):
                continue
            if pd.notna(best_session) and abs(v - best_session) < _EPS:
                styles.loc[i, col_disp] = VIOLET_BG
            elif best_perso is not None and pd.notna(best_perso.iloc[i]) and abs(v - best_perso.iloc[i]) < _EPS:
                styles.loc[i, col_disp] = GREEN_BG

    _mark("Best lap", dfr["best"], sess_best["lap"])
    _mark("Dernier tour", dfr["last_lap"], sess_best["lap"], dfr["pb_lap"])
    _mark("S1", dfr["lS1"], sess_best["S1"], dfr["bS1"])
    _mark("S2", dfr["lS2"], sess_best["S2"], dfr["bS2"])
    _mark("S3", dfr["lS3"], sess_best["S3"], dfr["bS3"])
    _mark("S1★", dfr["bS1"], sess_best["S1"])
    _mark("S2★", dfr["bS2"], sess_best["S2"])
    _mark("S3★", dfr["bS3"], sess_best["S3"])

    show_table(
        disp.style.apply(lambda _: styles, axis=None),
        height=min(40 * (len(disp) + 1) + 3, 780),
        force_html=True, mono=True,
    )
    st.caption(
        "🟣 fond violet = record de la session · 🟢 fond vert = record perso · "
        "**S1-S3** = secteurs du dernier tour bouclé · **S1★-S3★** = meilleurs secteurs "
        "individuels · **Pneu** = âge (tours) + compound du dernier relais · "
        "les tours supprimés (track limits) sont exclus des records. "
        + ("Écarts, statuts et **Δ Grille** (places vs grille de départ, PL = départ "
           "pit lane) issus du classement officiel." if is_race
           else "Classement par meilleur tour.")
    )

    # --- Schéma des écarts au leader ---
    st.markdown("---")
    st.markdown("#### ⏱️ Écarts à l'arrivée" if is_race else "#### ⏱️ Écarts au meilleur tour")
    plotted = [(dfr["drv"].iloc[i], gap_num[i]) for i in range(len(dfr))
               if np.isfinite(gap_num[i])]
    if len(plotted) < 2:
        st.info("Pas assez d'écarts chiffrés pour tracer le schéma.")
    else:
        codes = [c for c, _ in plotted]
        xs = [g for _, g in plotted]
        span = (max(xs) - min(xs)) or 1.0
        # Une seule ligne, façon livetiming : les bulles se chevauchent en
        # escalier dans les grappes serrées, le tap/hover donne le détail.
        b_size, f_size = (18, 7) if MOBILE else (22, 8)
        fig_gap = go.Figure()
        fig_gap.add_trace(go.Scatter(  # ligne de fond
            x=[min(xs), max(xs)], y=[0, 0], mode="lines",
            line=dict(color="rgba(255,255,255,0.25)", width=3),
            hoverinfo="skip", showlegend=False,
        ))
        fig_gap.add_trace(go.Scatter(
            x=xs, y=[0] * len(xs), mode="markers+text",
            marker=dict(size=b_size, color=[driver_color(c) for c in codes],
                        line=dict(color="rgba(255,255,255,0.85)", width=1)),
            text=codes, textposition="middle center",
            textfont=dict(size=f_size, color="white"),
            hovertemplate="%{text} : +%{x:.3f} s<extra></extra>",
            cliponaxis=False, showlegend=False,
        ))
        pad = max(span * 0.04, 0.5)
        fig_gap.update_xaxes(title="Écart au leader (s)", showgrid=False, zeroline=False,
                             range=[min(xs) - pad, max(xs) + pad])
        fig_gap.update_yaxes(visible=False, range=[-1, 1], fixedrange=True)
        fig_gap.update_layout(height=140, template="plotly_dark",
                              margin=dict(t=10, b=40, l=20, r=20))
        plot(fig_gap)
        missing = [dfr["drv"].iloc[i] for i in range(len(dfr))
                   if not np.isfinite(gap_num[i])]
        if missing:
            st.caption("Non représentés (écart non chiffré — tour(s) de retard ou abandon) : "
                       + ", ".join(missing))

    # --- Position des pilotes par tour (course/sprint) ---
    if is_race:
        pos_laps = laps_all[["Driver", "LapNumber", "Position"]].dropna()
        if len(pos_laps):
            st.markdown("---")
            with st.expander("📈 Position des pilotes par tour", expanded=False):
                order = dfr["drv"].tolist()  # ordre du classement final
                sel = st.multiselect(
                    "Pilotes affichés",
                    options=order,
                    default=order,
                    key="pos_laps_drivers",
                    format_func=lambda d: driver_full.get(d, d) if not MOBILE else d,
                )
                if not sel:
                    st.info("Sélectionne au moins un pilote.")
                else:
                    grid_map = dict(zip(dfr["drv"], dfr["grid"]))
                    fig_pos = go.Figure()
                    for drv in order:
                        if drv not in sel:
                            continue
                        g = pos_laps[pos_laps["Driver"] == drv].sort_values("LapNumber")
                        if g.empty:
                            continue
                        xs = g["LapNumber"].tolist()
                        ys = g["Position"].tolist()
                        # Point « tour 0 » = grille de départ → le premier tour
                        # (envol ou départ raté) devient lisible
                        g0 = grid_map.get(drv)
                        if pd.notna(g0) and g0 > 0:
                            xs = [0] + xs
                            ys = [float(g0)] + ys
                        fig_pos.add_trace(go.Scatter(
                            x=xs, y=ys, mode="lines+markers", name=drv,
                            line=dict(color=driver_color(drv), width=2),
                            marker=dict(size=4),
                            hovertemplate=f"<b>{drv}</b><br>Tour %{{x}}<br>P%{{y:.0f}}<extra></extra>",
                        ))
                    fig_pos.update_layout(
                        height=550, template="plotly_dark",
                        xaxis_title="Tour (0 = grille de départ)",
                        yaxis=dict(title="Position", autorange="reversed", dtick=1),
                        hovermode="closest",
                        legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center",
                                    font=dict(size=10)),
                        margin=dict(t=20, b=20, l=20, r=20),
                    )
                    plot(fig_pos)
                    st.caption(
                        "Position au passage de la ligne à chaque tour · deux coéquipiers "
                        "partagent la même couleur · une chute brutale suivie d'une remontée "
                        "= arrêt aux stands · une ligne qui s'arrête = abandon."
                    )

    # --- Progression des segments de qualification ---
    if st.session_state.session_type in ("Q", "SQ") and results is not None:
        qcols = [c for c in ("Q1", "Q2", "Q3") if c in results.columns]
        if qcols and results[qcols].notna().any().any():
            seg = "SQ" if st.session_state.session_type == "SQ" else "Q"
            st.markdown("---")
            st.markdown(f"#### 📶 Progression {seg}1 → {seg}2 → {seg}3")
            resq = results.dropna(subset=["Position"]).sort_values("Position")
            dispq = pd.DataFrame({
                "Pos": resq["Position"].astype(int).values,
                "Pilote": resq["Abbreviation"].astype(str).values,
                **{f"{seg}{k}": resq[f"Q{k}"].apply(_fmt_lap).values
                   for k in (1, 2, 3) if f"Q{k}" in qcols},
            })
            stylesq = pd.DataFrame("", index=dispq.index, columns=dispq.columns)
            for i, drv in enumerate(dispq["Pilote"]):
                colr = driver_color(drv)
                stylesq.loc[i, "Pilote"] = (f"background-color: {colr}; color: {text_on(colr)}; "
                                            f"font-weight: bold; border-radius: 6px; text-align: center")
            for k in (1, 2, 3):
                if f"Q{k}" not in qcols:
                    continue
                best_q = results[f"Q{k}"].min()
                if pd.isna(best_q):
                    continue
                m = resq[f"Q{k}"].notna() & ((resq[f"Q{k}"] - best_q).abs() < _EPS)
                stylesq.loc[m.values, f"{seg}{k}"] = "color: #C77DFF; font-weight: bold"
            show_table(dispq.style.apply(lambda _: stylesq, axis=None),
                       height=min(40 * (len(dispq) + 1) + 3, 780),
                       force_html=True, mono=True)
            st.caption("🟣 = meilleur temps du segment · — = éliminé avant ce segment "
                       "(ou pas de temps enregistré).")

    # --- Arrêts aux stands : temps perdu dans la pit lane ---
    if is_race:
        pit_rows = []
        for drv in dfr["drv"]:
            ld_p = laps_all[laps_all["Driver"] == drv].sort_values("LapNumber")
            durs = []
            for _, r in ld_p[ld_p["PitInTime"].notna()].iterrows():
                nxt = ld_p[ld_p["LapNumber"] == r["LapNumber"] + 1]
                if len(nxt) and pd.notna(nxt["PitOutTime"].iloc[0]):
                    durs.append((nxt["PitOutTime"].iloc[0] - r["PitInTime"]).total_seconds())
            if durs:
                pit_rows.append({"Pilote": drv, "Arrêts": len(durs),
                                 "Total pit lane": f"{sum(durs):.1f}s",
                                 "Moyenne": f"{np.mean(durs):.1f}s",
                                 "Plus rapide": f"{min(durs):.1f}s",
                                 "_tot": sum(durs)})
        if pit_rows:
            st.markdown("---")
            with st.expander("🛠️ Arrêts aux stands — temps perdu dans la pit lane", expanded=False):
                dfp = pd.DataFrame(pit_rows).sort_values("_tot").drop(columns="_tot").reset_index(drop=True)
                stylesp = pd.DataFrame("", index=dfp.index, columns=dfp.columns)
                for i, drv in enumerate(dfp["Pilote"]):
                    colr = driver_color(drv)
                    stylesp.loc[i, "Pilote"] = (f"background-color: {colr}; color: {text_on(colr)}; "
                                                f"font-weight: bold; border-radius: 6px; text-align: center")
                show_table(dfp.style.apply(lambda _: stylesp, axis=None),
                           height=min(40 * (len(dfp) + 1) + 3, 600),
                           force_html=True, mono=True)
                st.caption("Temps entrée → sortie de la pit lane (traversée + arrêt), reconstruit "
                           "depuis PitInTime/PitOutTime. Trié du moins au plus de temps perdu.")

    # --- Messages de la direction de course ---
    try:
        rcm = session.race_control_messages
    except Exception:
        rcm = None
    if rcm is not None and len(rcm):
        st.markdown("---")
        with st.expander("📢 Direction de course — drapeaux, SC, pénalités, tours supprimés",
                         expanded=False):
            msgs = rcm["Message"].astype(str)
            cat = rcm["Category"].astype(str) if "Category" in rcm.columns \
                else pd.Series("", index=rcm.index)
            important = rcm[
                (cat.isin(("Flag", "SafetyCar")) & ~msgs.str.contains("GREEN|CLEAR", na=False))
                | msgs.str.contains("PENALTY|INVESTIGAT|DELETED|SAFETY CAR|VIRTUAL|RED FLAG",
                                    case=False, na=False)
            ]
            df_rcm = important if len(important) else rcm
            cols_rcm = [c for c in ("Lap", "Category", "Message") if c in df_rcm.columns]
            st.dataframe(df_rcm[cols_rcm], width="stretch", hide_index=True,
                         height=min(38 * (len(df_rcm) + 1) + 3, 480))
            st.caption("Messages officiels FIA, filtrés sur l'essentiel : drapeaux, SC/VSC, "
                       "pénalités, enquêtes et tours supprimés.")

    # --- Radios d'équipe ---
    with st.spinner("Recherche des radios d'équipe…"):
        radio_df = load_team_radio(st.session_state.year, st.session_state.gp_name,
                                   st.session_state.session_type)
    if radio_df is not None and len(radio_df):
        st.markdown("---")
        with st.expander(f"📻 Radios d'équipe — {len(radio_df)} clips publiés", expanded=False):
            st.caption(
                "Sélection officielle FOM (les clips diffusés TV/app F1 — tout n'est pas "
                "publié) · **L** = tour en cours au moment du message · audio lu en direct "
                "depuis les serveurs F1."
            )
            drv_sel = st.multiselect("Filtrer par pilote",
                                     options=sorted(radio_df["Pilote"].unique().tolist()),
                                     key="radio_filter")
            shown = radio_df[radio_df["Pilote"].isin(drv_sel)] if drv_sel else radio_df
            _render_radio_clips(shown)

    # --- Championnat pilotes : impact de la session ---
    if not is_race:
        return
    st.markdown("---")
    st.markdown("#### 🏆 Championnat pilotes — impact de la session")
    with st.spinner("Calcul des points de la saison (long au premier chargement, ensuite en cache)…"):
        pts_before, cb_before, team_before = season_points_before(
            st.session_state.year, int(ev["RoundNumber"]), st.session_state.session_type
        )
    pts_session = {}
    if results is not None:
        pts_session = points_from_results(results, st.session_state.session_type)
    all_drv = set(pts_before) | set(pts_session)
    if not all_drv:
        st.info("Points indisponibles pour cette session.")
        return
    after = {d: pts_before.get(d, 0.0) + pts_session.get(d, 0.0) for d in all_drv}

    # Countback après : les positions de CETTE course s'ajoutent au décompte
    # (les sprints ne comptent pas dans le départage réglementaire)
    cb_after = {d: list(cb_before.get(d, [0] * 22)) for d in all_drv}
    if st.session_state.session_type == "R" and results is not None:
        for _, r in results.iterrows():
            code = str(r["Abbreviation"])
            pos = r.get("Position")
            if code in cb_after and pd.notna(pos) and 1 <= int(pos) <= 22:
                cb_after[code][int(pos) - 1] += 1

    def _ranks(pts, cb):
        def key(k):
            return (-pts[k],) + tuple(-c for c in cb.get(k, [0] * 22)) + (k,)
        return {k: i + 1 for i, k in enumerate(sorted(pts, key=key))}

    rk_b = _ranks({d: pts_before.get(d, 0.0) for d in all_drv},
                  {d: cb_before.get(d, [0] * 22) for d in all_drv})
    rk_a = _ranks(after, cb_after)

    def _full_name(drv):
        try:
            return session.get_driver(drv)["FullName"]
        except Exception:
            return drv

    rows_c = []
    for d in sorted(all_drv, key=lambda k: rk_a[k]):
        delta = rk_b[d] - rk_a[d]
        rows_c.append({
            "Pos": rk_a[d],
            "Pilote": _full_name(d),
            "_code": d,
            "Points": f"{after[d]:g}",
            "+ Session": f"+{pts_session.get(d, 0):g}" if pts_session.get(d, 0) else "–",
            "Δ Pos": (f"+{delta}" if delta > 0 else f"−{abs(delta)}") if delta else "–",
            "_delta": delta,
        })
    dcp = pd.DataFrame(rows_c)
    disp_c = dcp[["Pos", "Pilote", "Points", "+ Session", "Δ Pos"]]
    styles_c = pd.DataFrame("", index=disp_c.index, columns=disp_c.columns)
    for i in disp_c.index:
        colr = driver_color(dcp["_code"].iloc[i])
        styles_c.loc[i, "Pilote"] = (f"background-color: {colr}; color: {text_on(colr)}; "
                                     f"font-weight: bold; border-radius: 6px")
        dlt = dcp["_delta"].iloc[i]
        if dlt > 0:
            styles_c.loc[i, "Δ Pos"] = "color: #4ADE80; font-weight: bold"
        elif dlt < 0:
            styles_c.loc[i, "Δ Pos"] = "color: #F87171; font-weight: bold"
    show_table(disp_c.style.apply(lambda _: styles_c, axis=None),
               height=min(40 * (len(disp_c) + 1) + 3, 780),
               force_html=True, mono=True)
    st.caption(
        "Points cumulés courses + sprints, recalculés depuis les feuilles de résultats "
        "FastF1 · **+ Session** = points marqués dans cette session · **Δ Pos** = places "
        "gagnées/perdues au général grâce à cette session. Les égalités de points sont "
        "départagées comme au règlement : décompte des meilleures positions d'arrivée "
        "en course (les sprints ne comptent pas dans le départage)."
    )

    # --- Championnat constructeurs : impact de la session ---
    st.markdown("---")
    st.markdown("#### 🏭 Championnat constructeurs — impact de la session")
    team_session = {}
    if results is not None:
        for _, r in results.iterrows():
            team = str(r.get("TeamName", "") or "")
            if team:
                team_session[team] = (team_session.get(team, 0.0)
                                      + pts_session.get(str(r["Abbreviation"]), 0.0))
    all_teams = set(team_before) | set(team_session)
    if not all_teams:
        st.info("Points constructeurs indisponibles pour cette session.")
        return
    t_after = {t: team_before.get(t, 0.0) + team_session.get(t, 0.0) for t in all_teams}
    trk_b = {t: i + 1 for i, t in enumerate(
        sorted(all_teams, key=lambda t: (-team_before.get(t, 0.0), t)))}
    trk_a = {t: i + 1 for i, t in enumerate(
        sorted(all_teams, key=lambda t: (-t_after[t], t)))}
    rows_t = []
    for t in sorted(all_teams, key=lambda k: trk_a[k]):
        dlt = trk_b[t] - trk_a[t]
        rows_t.append({
            "Pos": trk_a[t], "Équipe": t,
            "Points": f"{t_after[t]:g}",
            "+ Session": f"+{team_session.get(t, 0):g}" if team_session.get(t, 0) else "–",
            "Δ Pos": (f"+{dlt}" if dlt > 0 else f"−{abs(dlt)}") if dlt else "–",
            "_delta": dlt,
        })
    dct = pd.DataFrame(rows_t)
    disp_t = dct[["Pos", "Équipe", "Points", "+ Session", "Δ Pos"]]
    styles_t = pd.DataFrame("", index=disp_t.index, columns=disp_t.columns)
    for i in disp_t.index:
        colr = team_color(dct["Équipe"].iloc[i])
        styles_t.loc[i, "Équipe"] = (f"background-color: {colr}; color: {text_on(colr)}; "
                                     f"font-weight: bold; border-radius: 6px")
        dlt = dct["_delta"].iloc[i]
        if dlt > 0:
            styles_t.loc[i, "Δ Pos"] = "color: #4ADE80; font-weight: bold"
        elif dlt < 0:
            styles_t.loc[i, "Δ Pos"] = "color: #F87171; font-weight: bold"
    show_table(disp_t.style.apply(lambda _: styles_t, axis=None),
               height=min(40 * (len(disp_t) + 1) + 3, 560),
               force_html=True, mono=True)
    st.caption(
        "Somme des points des pilotes de chaque équipe, courses + sprints. "
        "Égalités départagées par points uniquement (le countback constructeurs "
        "n'est pas appliqué)."
    )


# ============== NAVIGATION ==============
pg = st.navigation([
    st.Page(page_timing, title="Overview session", icon="📊", default=True),
    st.Page(page_style, title="Style de pilotage", icon="🎨"),
])
pg.run()

# ============== FOOTER ==============
st.markdown("---")
st.caption("Données : F1 Live Timing via FastF1 · Couleurs équipes 2026 · Analyse F1 by you")
