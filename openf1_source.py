"""Source de données OpenF1 — alternative à FastF1 pour les hébergements filtrés.

Pourquoi ce module
------------------
La F1 renvoie HTTP 403 aux IP de datacenter (constaté en prod sur Streamlit
Cloud, cf. CLAUDE.md) et le miroir FastF1 ne sert pas les flux de session.
`api.openf1.org` re-sert les mêmes données depuis sa propre infrastructure,
sans filtrage d'hébergeur — vérifié joignable depuis tous les nœuds testés.

Principe
--------
On imite l'interface FastF1 attendue par `app.py` plutôt que de réécrire les
14 onglets d'analyse :

    get_event_schedule(year)          -> DataFrame [RoundNumber, EventName, …]
    get_session(year, gp, ses)        -> Session
    Session.laps                      -> Laps (DataFrame + pick_drivers/pick_fastest)
    Lap.get_car_data().add_distance() -> Telemetry [Distance, Speed, Throttle, …]
    Lap.get_telemetry()               -> idem + X/Y
    Session.results / .weather_data / .race_control_messages / .get_driver()

⚠️ Différences de fond avec FastF1, assumées :
- couverture **2023 → présent** seulement (FastF1 remonte à 2018) ;
- pas de notion de tour supprimé (`Deleted`) : OpenF1 ne l'expose pas ;
- la distance parcourue est **reconstruite** en intégrant la vitesse dans le
  temps (FastF1 la fournit) — voir `Telemetry.add_distance()` ;
- les virages viennent de l'API MultiViewer, pas d'OpenF1.

Le mapping des champs est centralisé en tête de chaque fonction `_map_*`
pour qu'une correction de schéma ne demande qu'une seule retouche.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import requests

BASE_URL = "https://api.openf1.org/v1"
MV_URL = "https://api.multiviewer.app/api/v1"  # position des virages
TIMEOUT = 30

# Codes DRS OpenF1 : 0/1 = fermé, 8 = éligible, 10/12/14 = volet ouvert
DRS_OPEN_CODES = (10, 12, 14)

# Codes de mini-secteur (flux `segments_sector_*`). Repris du live timing F1 :
# ce sont les couleurs affichées à l'écran, secteur par secteur.
# ⚠️ à confirmer sur données réelles — la table officieuse peut varier.
SEGMENT_COLORS = {
    0: None,          # pas de donnée
    2048: "yellow",   # plus lent que son propre référence
    2049: "green",    # meilleur perso sur ce mini-secteur
    2051: "purple",   # meilleur de la session
    2064: "pit",      # passage par la voie des stands
}


def segment_label(code):
    """Couleur d'un mini-secteur, ou None si le code est inconnu/absent."""
    try:
        return SEGMENT_COLORS.get(int(code))
    except (TypeError, ValueError):
        return None

# session_name OpenF1 -> code utilisé par l'app
SESSION_NAMES = {
    "Practice 1": "FP1", "Practice 2": "FP2", "Practice 3": "FP3",
    "Qualifying": "Q", "Sprint": "S", "Sprint Qualifying": "SQ",
    "Sprint Shootout": "SQ", "Race": "R",
}
CODE_TO_NAME = {
    "FP1": "Practice 1", "FP2": "Practice 2", "FP3": "Practice 3",
    "Q": "Qualifying", "S": "Sprint", "SQ": "Sprint Qualifying", "R": "Race",
}


class OpenF1Error(RuntimeError):
    """Échec de récupération côté OpenF1 (réseau, schéma inattendu, vide)."""


def _get(endpoint, **params):
    """Appel GET sur l'API, renvoie une liste de dicts (éventuellement vide).

    OpenF1 renvoie toujours un tableau JSON ; un dict seul signale une erreur
    applicative (ex. quota) qu'on remonte explicitement."""
    url = f"{BASE_URL}/{endpoint}"
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT)
    except Exception as exc:
        raise OpenF1Error(f"{endpoint} injoignable : {type(exc).__name__}") from exc
    if r.status_code != 200:
        raise OpenF1Error(f"{endpoint} : HTTP {r.status_code}")
    try:
        data = r.json()
    except Exception as exc:
        raise OpenF1Error(f"{endpoint} : réponse illisible") from exc
    if isinstance(data, dict):
        raise OpenF1Error(f"{endpoint} : {data.get('detail') or data}")
    return data


def _df(records, dates=()):
    """Liste de dicts -> DataFrame, avec conversion des colonnes de dates.

    ⚠️ `format="ISO8601"` est indispensable : OpenF1 mélange les précisions
    ("…:35+00:00" et "…:35.200000+00:00") au sein d'un même flux. Sans lui,
    pandas déduit le format du premier élément et convertit silencieusement
    tous les autres en NaT (avec errors="coerce"), ce qui vidait la moitié
    de la télémétrie et faisait échouer l'appariement des positions."""
    df = pd.DataFrame(records)
    for col in dates:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="ISO8601", utc=True,
                                     errors="coerce").dt.tz_localize(None)
    return df


# ============== CALENDRIER & SESSIONS ==============
def get_event_schedule(year, include_testing=False):
    """Calendrier d'une saison, au format attendu par l'app.

    OpenF1 expose les week-ends via `/meetings` ; le numéro de manche n'y
    figure pas, on le reconstruit par ordre chronologique."""
    meetings = _get("meetings", year=int(year))
    if not meetings:
        raise OpenF1Error(f"aucun week-end trouvé pour {year}")
    df = _df(meetings, dates=("date_start",))
    df = df.sort_values("date_start").reset_index(drop=True)
    if not include_testing:
        # Les essais de pré-saison n'ont pas de Grand Prix associé
        mask = ~df["meeting_name"].astype(str).str.contains("Testing", case=False, na=False)
        df = df[mask].reset_index(drop=True)
    out = pd.DataFrame({
        "RoundNumber": np.arange(1, len(df) + 1),
        "EventName": df["meeting_name"].astype(str),
        "Country": df.get("country_name", pd.Series([""] * len(df))).astype(str),
        "Location": df.get("location", pd.Series([""] * len(df))).astype(str),
        "EventDate": df["date_start"],
        "_meeting_key": df["meeting_key"],
    })
    # EventFormat : FastF1 le fournit, pas OpenF1. Sans lui, l'app ne détecte
    # aucun week-end sprint et oublie ces points au championnat. On le déduit
    # de la présence d'une session « Sprint », en une seule requête pour toute
    # la saison.
    sprint_meetings = set()
    try:
        for s in _get("sessions", year=int(year)) or []:
            if "sprint" in str(s.get("session_name", "")).lower():
                mk = s.get("meeting_key")
                if mk is not None:
                    sprint_meetings.add(int(mk))
    except OpenF1Error:
        pass
    out["EventFormat"] = ["sprint_qualifying" if int(k) in sprint_meetings
                          else "conventional" for k in df["meeting_key"]]
    return out


def _find_meeting(year, gp):
    """Retrouve la clé du week-end depuis son nom, ou son numéro de manche
    (FastF1 accepte les deux, `season_points_before` s'en sert)."""
    sched = get_event_schedule(year, include_testing=True)
    if isinstance(gp, (int, np.integer)) or (isinstance(gp, str) and gp.isdigit()):
        rnd = int(gp)
        row = sched[sched["RoundNumber"] == rnd]
        if len(row):
            return int(row.iloc[0]["_meeting_key"])
        raise OpenF1Error(f"manche {rnd} introuvable en {year}")
    exact = sched[sched["EventName"] == gp]
    if len(exact):
        return int(exact.iloc[0]["_meeting_key"])
    # Repli : correspondance partielle (« Dutch » ↔ « Dutch Grand Prix »)
    loose = sched[sched["EventName"].str.contains(str(gp).split(" Grand")[0],
                                                  case=False, na=False)]
    if len(loose):
        return int(loose.iloc[0]["_meeting_key"])
    raise OpenF1Error(f"week-end introuvable : {gp} ({year})")


def _find_session_key(meeting_key, session_type):
    """Clé de la session (Q, R, FP1…) dans un week-end donné."""
    sessions = _get("sessions", meeting_key=meeting_key)
    if not sessions:
        raise OpenF1Error("aucune session pour ce week-end")
    wanted = CODE_TO_NAME.get(session_type, session_type)
    for s in sessions:
        if str(s.get("session_name", "")).lower() == wanted.lower():
            return s
    # Sprint Shootout / Sprint Qualifying selon les saisons
    if session_type == "SQ":
        for s in sessions:
            if "sprint" in str(s.get("session_name", "")).lower() \
                    and "qualif" in str(s.get("session_name", "")).lower():
                return s
    dispo = ", ".join(str(s.get("session_name")) for s in sessions)
    raise OpenF1Error(f"session {session_type} absente (disponibles : {dispo})")


# ============== TÉLÉMÉTRIE ==============
class Telemetry(pd.DataFrame):
    """DataFrame de télémétrie avec l'API que l'app attend de FastF1."""

    _metadata = ["_lap_ref"]

    @property
    def _constructor(self):
        return Telemetry

    def add_distance(self):
        """Ajoute la colonne `Distance` (m depuis le début du tour).

        FastF1 la fournit ; OpenF1 non. On l'intègre depuis la vitesse :
        d(i) = Σ v·Δt. L'échantillonnage étant irrégulier (~3,7 Hz), on
        utilise la vitesse moyenne entre deux points (méthode des trapèzes),
        nettement plus juste qu'un simple rectangle sur les phases de
        freinage où la vitesse chute vite."""
        if "Distance" in self.columns or self.empty:
            return self
        t = self["Time"].dt.total_seconds().values.astype(float)
        v = self["Speed"].values.astype(float) / 3.6  # km/h -> m/s
        dt = np.diff(t, prepend=t[0])
        v_moy = np.concatenate([[v[0]], (v[1:] + v[:-1]) / 2.0])
        self["Distance"] = np.cumsum(np.clip(v_moy * dt, 0, None))
        return self


def _merge_location(car, loc):
    """Associe les positions X/Y aux points de télémétrie les plus proches
    dans le temps. Les deux flux ont des cadences différentes : `merge_asof`
    apparie chaque échantillon à la position la plus récente."""
    if loc is None or loc.empty:
        for c in ("X", "Y", "Z"):
            car[c] = np.nan
        return car
    # merge_asof refuse les clés nulles : on écarte les points sans horodatage
    left = car.dropna(subset=["Date"]).sort_values("Date")
    right = loc.dropna(subset=["Date"]).sort_values("Date")[["Date", "x", "y", "z"]]
    if left.empty or right.empty:
        for c in ("X", "Y", "Z"):
            car[c] = np.nan
        return car
    merged = pd.merge_asof(left, right, on="Date", direction="nearest",
                           tolerance=pd.Timedelta(seconds=1))
    return merged.rename(columns={"x": "X", "y": "Y", "z": "Z"})


class Lap(pd.Series):
    """Un tour, avec accès à sa télémétrie (interface FastF1)."""

    _metadata = ["_session"]

    @property
    def _constructor(self):
        return Lap

    @property
    def _constructor_expanddim(self):
        return Laps

    def _window(self):
        """Bornes temporelles du tour, pour découper les flux continus."""
        start = self.get("LapStartDate")
        if pd.isna(start):
            raise OpenF1Error("tour sans horodatage de départ")
        dur = self.get("LapTime")
        end = start + (dur if pd.notna(dur) else pd.Timedelta(seconds=120))
        return start, end

    def get_car_data(self, **_):
        """Canaux moteur/pilote du tour : Speed, Throttle, Brake, nGear, RPM, DRS."""
        start, end = self._window()
        return self._session._telemetry_for(int(self["DriverNumber"]), start, end,
                                            with_position=False)

    def get_telemetry(self, **_):
        """Idem + position X/Y sur le tracé, et Distance déjà calculée."""
        start, end = self._window()
        tel = self._session._telemetry_for(int(self["DriverNumber"]), start, end,
                                           with_position=True)
        return tel.add_distance()

    def get_pos_data(self, **_):
        return self.get_telemetry()


class Laps(pd.DataFrame):
    """Ensemble de tours, avec les sélecteurs de FastF1 utilisés par l'app."""

    _metadata = ["_session"]

    @property
    def _constructor(self):
        return Laps

    @property
    def _constructor_sliced(self):
        return Lap

    def _keep_session(self, out):
        out._session = getattr(self, "_session", None)
        return out

    def pick_drivers(self, drv):
        """Filtre par code pilote (VER) ou numéro. Accepte une liste."""
        wanted = [drv] if isinstance(drv, (str, int, np.integer)) else list(drv)
        wanted = [str(w) for w in wanted]
        mask = self["Driver"].astype(str).isin(wanted) \
            | self["DriverNumber"].astype(str).isin(wanted)
        return self._keep_session(self[mask].copy())

    # Alias historiques de FastF1
    pick_driver = pick_drivers

    def pick_fastest(self):
        """Tour le plus rapide, ou None si aucun tour chronométré."""
        timed = self[self["LapTime"].notna()]
        if timed.empty:
            return None
        lap = timed.loc[timed["LapTime"].idxmin()].copy()
        lap._session = getattr(self, "_session", None)
        return lap

    def pick_quicklaps(self, threshold=1.07):
        timed = self[self["LapTime"].notna()]
        if timed.empty:
            return self._keep_session(self.copy())
        limit = timed["LapTime"].min() * threshold
        return self._keep_session(timed[timed["LapTime"] <= limit].copy())

    def pick_accurate(self):
        if "IsAccurate" not in self.columns:
            return self._keep_session(self.copy())
        return self._keep_session(self[self["IsAccurate"]].copy())


# ============== SESSION ==============
class CircuitInfo:
    """Position des virages, format FastF1 (`corners` avec X/Y/Number/Letter)."""

    def __init__(self, corners, rotation=0.0):
        self.corners = corners
        self.rotation = rotation
        self.marshal_lights = pd.DataFrame()
        self.marshal_sectors = pd.DataFrame()


class Session:
    """Session F1 servie par OpenF1, exposant l'interface FastF1 utilisée par l'app."""

    def __init__(self, year, gp, session_type):
        self.year = int(year)
        self.name = session_type
        self._gp = gp
        self._meeting_key = _find_meeting(year, gp)
        info = _find_session_key(self._meeting_key, session_type)
        self.session_key = int(info["session_key"])
        self.session_info = info
        self._laps = None
        self._drivers = None
        self._results = None
        self._weather = None
        self._rcm = None
        self._tel_cache = {}
        sched = get_event_schedule(year, include_testing=True)
        row = sched[sched["_meeting_key"] == self._meeting_key]
        self.event = (row.iloc[0] if len(row) else pd.Series(
            {"EventName": gp, "Country": info.get("country_name", ""),
             "Location": info.get("location", ""),
             "EventDate": pd.to_datetime(info.get("date_start")), "RoundNumber": 0}))

    # --- chargement (l'app appelle load(), tout est paresseux ici) ---
    def load(self, laps=True, **_):
        """`laps=False` évite de rapatrier tous les tours quand seuls les
        résultats sont voulus (calcul des points de championnat)."""
        if laps:
            _ = self.laps  # déclenche la récupération et remonte l'erreur tôt
        return self

    @property
    def team_radio(self):
        """Clips radio publiés, avec le tour approximatif du message."""
        try:
            recs = _get("team_radio", session_key=self.session_key)
        except OpenF1Error:
            return pd.DataFrame()
        df = _df(recs, dates=("date",))
        if df.empty:
            return df
        df["Pilote"] = [self._code(n) for n in df["driver_number"]]
        df = df.rename(columns={"date": "utc", "recording_url": "url"})
        laps = self.laps
        lap_no = []
        for _, r in df.iterrows():
            ld = laps[(laps["Driver"] == r["Pilote"]) & laps["LapStartDate"].notna()]
            before = ld[ld["LapStartDate"] <= r["utc"]]
            lap_no.append(int(before["LapNumber"].iloc[-1]) if len(before) else np.nan)
        df["Lap"] = lap_no
        return df[["Pilote", "Lap", "utc", "url"]].sort_values("utc").reset_index(drop=True)

    # --- pilotes ---
    @property
    def drivers_info(self):
        if self._drivers is None:
            recs = _get("drivers", session_key=self.session_key)
            if not recs:
                raise OpenF1Error("liste des pilotes vide")
            df = _df(recs).drop_duplicates("driver_number")
            df["driver_number"] = df["driver_number"].astype(int)
            self._drivers = df.set_index("driver_number")
        return self._drivers

    def _code(self, number):
        try:
            return str(self.drivers_info.loc[int(number), "name_acronym"])
        except Exception:
            return str(number)

    def get_driver(self, ident):
        """Infos pilote au format FastF1 (FullName, TeamName, Abbreviation…)."""
        info = self.drivers_info
        row = None
        for num, r in info.iterrows():
            if str(ident) in (str(num), str(r.get("name_acronym", ""))):
                row = r
                break
        if row is None:
            raise KeyError(ident)
        colour = str(row.get("team_colour") or "").lstrip("#")
        return pd.Series({
            "Abbreviation": row.get("name_acronym", str(ident)),
            "FullName": row.get("full_name") or row.get("broadcast_name") or str(ident),
            "FirstName": row.get("first_name", ""),
            "LastName": row.get("last_name", ""),
            "TeamName": row.get("team_name", "—"),
            "TeamColor": colour,
            "DriverNumber": str(row.name),
            "HeadshotUrl": row.get("headshot_url", ""),
            "CountryCode": row.get("country_code", ""),
        })

    # --- tours ---
    @property
    def laps(self):
        if self._laps is None:
            self._laps = self._build_laps()
        return self._laps

    def _build_laps(self):
        recs = _get("laps", session_key=self.session_key)
        if not recs:
            raise OpenF1Error("aucun tour disponible pour cette session")
        raw = _df(recs, dates=("date_start",))
        raw["driver_number"] = raw["driver_number"].astype(int)

        def _td(col):
            return pd.to_timedelta(raw[col], unit="s") if col in raw.columns \
                else pd.Series(pd.NaT, index=raw.index)

        laps = pd.DataFrame({
            "Driver": [self._code(n) for n in raw["driver_number"]],
            "DriverNumber": raw["driver_number"].astype(str),
            "LapNumber": raw["lap_number"].astype(float),
            "LapStartDate": raw["date_start"],
            "LapTime": _td("lap_duration"),
            "Sector1Time": _td("duration_sector_1"),
            "Sector2Time": _td("duration_sector_2"),
            "Sector3Time": _td("duration_sector_3"),
            "SpeedI1": raw.get("i1_speed"),
            "SpeedI2": raw.get("i2_speed"),
            "SpeedST": raw.get("st_speed"),
            "SpeedFL": np.nan,
            "IsPitOutLap": raw.get("is_pit_out_lap", False).fillna(False)
            if "is_pit_out_lap" in raw.columns else False,
        })
        # Mini-secteurs : listes de codes par secteur. Inaccessibles via FastF1
        # en post-session (flux live SignalR) — OpenF1 les conserve, ce qui rend
        # possible la comparaison mini-secteur par mini-secteur en qualif.
        for i in (1, 2, 3):
            col = f"segments_sector_{i}"
            laps[f"Segments{i}"] = raw[col] if col in raw.columns else None
        # Temps de passage cumulé depuis le début de session (colonne `Time`)
        t0 = laps["LapStartDate"].min()
        laps["Time"] = (laps["LapStartDate"] - t0) + laps["LapTime"].fillna(pd.Timedelta(0))

        self._add_stints(laps)
        self._add_pits(laps)
        self._add_positions(laps)
        self._add_track_status(laps)

        # Non exposés par OpenF1 : on neutralise proprement plutôt que d'omettre
        # les colonnes (l'app les teste partout).
        laps["Deleted"] = False
        laps["DeletedReason"] = ""
        laps["IsAccurate"] = laps["LapTime"].notna() & ~laps["IsPitOutLap"].astype(bool)

        laps = laps.sort_values(["Driver", "LapNumber"]).reset_index(drop=True)
        out = Laps(laps)
        out._session = self
        return out

    def _add_stints(self, laps):
        """Compound, âge du pneu et numéro de relais, depuis /stints."""
        laps["Compound"] = "UNKNOWN"
        laps["TyreLife"] = np.nan
        laps["Stint"] = np.nan
        laps["FreshTyre"] = True
        try:
            recs = _get("stints", session_key=self.session_key)
        except OpenF1Error:
            return
        for s in recs or []:
            try:
                num, lo, hi = int(s["driver_number"]), int(s["lap_start"]), int(s["lap_end"])
            except (KeyError, TypeError, ValueError):
                continue
            age0 = s.get("tyre_age_at_start") or 0
            m = (laps["DriverNumber"] == str(num)) & \
                (laps["LapNumber"] >= lo) & (laps["LapNumber"] <= hi)
            laps.loc[m, "Compound"] = str(s.get("compound") or "UNKNOWN").upper()
            laps.loc[m, "Stint"] = s.get("stint_number")
            laps.loc[m, "TyreLife"] = laps.loc[m, "LapNumber"] - lo + 1 + float(age0)
            laps.loc[m, "FreshTyre"] = float(age0) <= 0

    def _add_pits(self, laps):
        """PitInTime / PitOutTime au format FastF1 (horodatages, sinon NaT)."""
        laps["PitInTime"] = pd.NaT
        laps["PitOutTime"] = pd.NaT
        # Un tour marqué « sortie des stands » a un PitOutTime renseigné
        if "IsPitOutLap" in laps.columns:
            m = laps["IsPitOutLap"].astype(bool)
            laps.loc[m, "PitOutTime"] = laps.loc[m, "LapStartDate"]
        try:
            recs = _get("pit", session_key=self.session_key)
        except OpenF1Error:
            return
        for p in recs or []:
            try:
                num, ln = int(p["driver_number"]), int(p["lap_number"])
            except (KeyError, TypeError, ValueError):
                continue
            m = (laps["DriverNumber"] == str(num)) & (laps["LapNumber"] == ln)
            if m.any():
                laps.loc[m, "PitInTime"] = pd.to_datetime(p.get("date"), errors="coerce",
                                                          utc=True).tz_localize(None) \
                    if p.get("date") else laps.loc[m, "LapStartDate"]

    def _add_positions(self, laps):
        """Position à la fin de chaque tour, depuis le flux /position."""
        laps["Position"] = np.nan
        try:
            recs = _get("position", session_key=self.session_key)
        except OpenF1Error:
            return
        if not recs:
            return
        pos = _df(recs, dates=("date",)).dropna(subset=["date"])
        pos["driver_number"] = pos["driver_number"].astype(int)
        for num, grp in pos.groupby("driver_number"):
            m = laps["DriverNumber"] == str(num)
            if not m.any():
                continue
            grp = grp.sort_values("date")
            ends = laps.loc[m, "LapStartDate"] + laps.loc[m, "LapTime"].fillna(pd.Timedelta(0))
            merged = pd.merge_asof(
                pd.DataFrame({"date": ends.values}).sort_values("date"),
                grp[["date", "position"]], on="date", direction="backward")
            laps.loc[m, "Position"] = merged["position"].values

    def _add_track_status(self, laps):
        """TrackStatus approximé depuis les messages de direction de course.

        Codes FastF1 : 1 = piste dégagée, 4 = Safety Car, 5 = drapeau rouge,
        6 = VSC. On propage le dernier état connu sur les tours concernés."""
        laps["TrackStatus"] = "1"
        try:
            rcm = self.race_control_messages
        except Exception:
            return
        if rcm is None or rcm.empty:
            return
        events = []
        for _, m in rcm.iterrows():
            # `race_control_messages` renomme déjà les colonnes au format
            # FastF1 (Message/Lap) : on accepte les deux graphies.
            msg = str(m.get("Message") if pd.notna(m.get("Message")) else
                      m.get("message", "")).upper()
            ln = m.get("Lap") if pd.notna(m.get("Lap")) else m.get("lap_number")
            if ln is None or pd.isna(ln):
                continue
            if "RED FLAG" in msg:
                events.append((int(ln), "5"))
            elif "SAFETY CAR" in msg and "VIRTUAL" not in msg:
                events.append((int(ln), "1" if "ENDING" in msg or "IN THIS LAP" in msg else "4"))
            elif "VIRTUAL SAFETY CAR" in msg or "VSC" in msg:
                events.append((int(ln), "1" if "ENDING" in msg else "6"))
            elif "GREEN" in msg or "CLEAR" in msg:
                events.append((int(ln), "1"))
        if not events:
            return
        events.sort()
        for i, (lap_no, code) in enumerate(events):
            end = events[i + 1][0] if i + 1 < len(events) else int(laps["LapNumber"].max()) + 1
            m = (laps["LapNumber"] >= lap_no) & (laps["LapNumber"] < max(end, lap_no + 1))
            laps.loc[m, "TrackStatus"] = code

    # --- télémétrie ---
    def _telemetry_for(self, driver_number, start, end, with_position):
        """Découpe les flux continus sur la fenêtre d'un tour.

        OpenF1 filtre côté serveur via `date>=`/`date<=` : indispensable, un
        flux de course complet pèse des dizaines de Mo par pilote."""
        key = (driver_number, str(start), str(end), with_position)
        if key in self._tel_cache:
            return self._tel_cache[key].copy()
        params = {
            "session_key": self.session_key,
            "driver_number": int(driver_number),
            "date>": pd.Timestamp(start).isoformat(),
            "date<": pd.Timestamp(end).isoformat(),
        }
        car = _df(_get("car_data", **params), dates=("date",))
        if car.empty:
            raise OpenF1Error("télémétrie indisponible pour ce tour")
        car = car.rename(columns={"date": "Date", "speed": "Speed", "throttle": "Throttle",
                                  "n_gear": "nGear", "rpm": "RPM", "drs": "DRS"})
        # OpenF1 code le frein en 0/100 ; l'app attend un booléen/0-1
        car["Brake"] = (pd.to_numeric(car.get("brake"), errors="coerce").fillna(0) > 0)
        car = car.sort_values("Date")
        if with_position:
            loc = _df(_get("location", **params), dates=("date",))
            if not loc.empty:
                loc = loc.rename(columns={"date": "Date"})
            car = _merge_location(car, loc)
        car["Time"] = car["Date"] - pd.Timestamp(start)
        car["SessionTime"] = car["Date"] - self.laps["LapStartDate"].min()
        cols = ["Date", "Time", "SessionTime", "Speed", "Throttle", "Brake", "nGear", "RPM", "DRS"]
        if with_position:
            cols += ["X", "Y", "Z"]
        tel = Telemetry(car[[c for c in cols if c in car.columns]].reset_index(drop=True))
        self._tel_cache[key] = tel.copy()
        return tel

    # --- annexes ---
    @property
    def weather_data(self):
        if self._weather is None:
            try:
                recs = _get("weather", session_key=self.session_key)
            except OpenF1Error:
                recs = []
            df = _df(recs, dates=("date",))
            if not df.empty:
                df = df.rename(columns={"air_temperature": "AirTemp",
                                        "track_temperature": "TrackTemp",
                                        "humidity": "Humidity", "pressure": "Pressure",
                                        "wind_speed": "WindSpeed",
                                        "wind_direction": "WindDirection",
                                        "rainfall": "Rainfall"})
                t0 = self.laps["LapStartDate"].min()
                df["Time"] = df["date"] - t0
            self._weather = df
        return self._weather

    @property
    def race_control_messages(self):
        if self._rcm is None:
            try:
                recs = _get("race_control", session_key=self.session_key)
            except OpenF1Error:
                recs = []
            df = _df(recs, dates=("date",))
            if not df.empty:
                df = df.rename(columns={"category": "Category", "message": "Message",
                                        "flag": "Flag", "scope": "Scope",
                                        "lap_number": "Lap", "date": "Time"})
                df["lap_number"] = df["Lap"]
            self._rcm = df
        return self._rcm

    @property
    def results(self):
        """Classement final. OpenF1 expose `/session_result` selon les
        versions ; à défaut on reconstruit depuis les positions de fin."""
        if self._results is not None:
            return self._results
        rows = []
        try:
            recs = _get("session_result", session_key=self.session_key)
        except OpenF1Error:
            recs = []
        grid = {}
        try:
            for g in _get("starting_grid", session_key=self.session_key) or []:
                grid[int(g["driver_number"])] = g.get("position")
        except (OpenF1Error, KeyError, TypeError, ValueError):
            pass
        if recs:
            for r in recs:
                try:
                    num = int(r["driver_number"])
                except (KeyError, TypeError, ValueError):
                    continue
                info = self.get_driver(num)
                rows.append({
                    "DriverNumber": str(num), "Abbreviation": info["Abbreviation"],
                    "FullName": info["FullName"], "TeamName": info["TeamName"],
                    "Position": r.get("position"), "GridPosition": grid.get(num, np.nan),
                    "Points": r.get("points"), "Status": r.get("status") or "",
                    "Time": pd.NaT, "Q1": pd.NaT, "Q2": pd.NaT, "Q3": pd.NaT,
                })
        else:
            laps = self.laps
            last = laps.sort_values("LapNumber").groupby("Driver").tail(1)
            for _, r in last.iterrows():
                num = int(r["DriverNumber"])
                info = self.get_driver(num)
                rows.append({
                    "DriverNumber": str(num), "Abbreviation": info["Abbreviation"],
                    "FullName": info["FullName"], "TeamName": info["TeamName"],
                    "Position": r.get("Position"), "GridPosition": grid.get(num, np.nan),
                    "Points": np.nan, "Status": "", "Time": pd.NaT,
                    "Q1": pd.NaT, "Q2": pd.NaT, "Q3": pd.NaT,
                })
        self._results = pd.DataFrame(rows)
        return self._results

    @property
    def session_status(self):
        return pd.DataFrame()

    def get_circuit_info(self):
        """Virages via l'API MultiViewer (OpenF1 ne les expose pas)."""
        ck = self.session_info.get("circuit_key")
        if ck is None:
            return None
        r = requests.get(f"{MV_URL}/circuits/{int(ck)}/{self.year}", timeout=TIMEOUT,
                         headers={"User-Agent": "analyse-f1"})
        r.raise_for_status()
        data = r.json()
        corners = data.get("corners") or []
        if not corners:
            return None
        df = pd.DataFrame({
            "Number": [c.get("number") for c in corners],
            "Letter": [c.get("letter") or "" for c in corners],
            "Angle": [c.get("angle") for c in corners],
            "X": [c.get("trackPosition", {}).get("x") for c in corners],
            "Y": [c.get("trackPosition", {}).get("y") for c in corners],
            "Distance": [c.get("distance") for c in corners],
        })
        if df["Distance"].isna().all():
            df["Distance"] = np.nan
        return CircuitInfo(df.sort_values("Number").reset_index(drop=True),
                           float(data.get("rotation") or 0))


def get_session(year, gp, session_type):
    """Point d'entrée équivalent à `fastf1.get_session()`."""
    return Session(year, gp, session_type)
