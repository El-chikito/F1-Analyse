"""Tests de l'adaptateur OpenF1, sur réponses simulées.

Pourquoi des données simulées : l'API n'est pas joignable depuis
l'environnement de développement (cf. CLAUDE.md), et surtout ces tests
figent le **contrat** attendu — colonnes, types, unités. Ils ont déjà
attrapé deux bugs qui auraient cassé en production :
  1. le mélange de précisions d'horodatage d'OpenF1 (moitié des points en NaT) ;
  2. les colonnes de la direction de course lues sous leur nom d'origine
     alors qu'elles venaient d'être renommées au format FastF1.

Lancer :  python3 test_openf1_source.py
"""
import numpy as np
import pandas as pd

import openf1_source as of1

T0 = pd.Timestamp("2026-08-23T13:00:00")


def _iso(ts, fractional=True):
    """Horodatage OpenF1. `fractional=False` reproduit la précision variable
    réellement observée dans leurs flux."""
    ts = pd.Timestamp(ts)
    if not fractional:
        return ts.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00"
    return ts.isoformat() + "+00:00"


def build_fixtures():
    fake = {
        "meetings": [
            {"meeting_key": 1250, "meeting_name": "Dutch Grand Prix",
             "country_name": "Netherlands", "location": "Zandvoort",
             "date_start": _iso("2026-08-21T09:00:00"), "circuit_key": 55},
            {"meeting_key": 1240, "meeting_name": "Belgian Grand Prix",
             "country_name": "Belgium", "location": "Spa",
             "date_start": _iso("2026-07-17T09:00:00"), "circuit_key": 7},
        ],
        "sessions": [{"session_key": 9999, "session_name": "Race", "circuit_key": 55,
                      "country_name": "Netherlands", "location": "Zandvoort",
                      "date_start": _iso(T0)}],
        "drivers": [
            {"driver_number": 1, "name_acronym": "VER", "full_name": "Max VERSTAPPEN",
             "team_name": "Red Bull Racing", "team_colour": "3671C6",
             "headshot_url": "http://x/1.png"},
            {"driver_number": 16, "name_acronym": "LEC", "full_name": "Charles LECLERC",
             "team_name": "Ferrari", "team_colour": "E8002D",
             "headshot_url": "http://x/16.png"},
        ],
        "laps": [], "stints": [], "pit": [], "position": [],
        "car_data": [], "location": [], "starting_grid": [],
        # `/session_result` ne porte pas de champ `status` mais trois booléens.
        # VER voit l'arrivée, LEC abandonne : c'est ce que le graphe des
        # positions par course doit pouvoir distinguer.
        "session_result": [
            {"driver_number": 1, "position": 1, "points": 25,
             "dnf": False, "dns": False, "dsq": False},
            {"driver_number": 16, "position": 18, "points": 0,
             "dnf": True, "dns": False, "dsq": False},
        ],
        "weather": [{"date": _iso(T0), "air_temperature": 24.0, "track_temperature": 41.0,
                     "humidity": 50, "wind_speed": 3.2, "rainfall": 0}],
        "race_control": [
            {"date": _iso(T0 + pd.Timedelta(seconds=80)), "lap_number": 2,
             "category": "SafetyCar", "message": "SAFETY CAR DEPLOYED",
             "flag": "", "scope": "Track"},
            {"date": _iso(T0 + pd.Timedelta(seconds=150)), "lap_number": 3,
             "category": "Flag", "message": "GREEN LIGHT - PIT EXIT OPEN",
             "flag": "GREEN", "scope": "Track"},
        ],
    }
    for num in (1, 16):
        for lap in (1, 2, 3):
            fake["laps"].append({
                "driver_number": num, "lap_number": lap,
                "date_start": _iso(T0 + pd.Timedelta(seconds=(lap - 1) * 75)),
                "lap_duration": 74.5 + lap * 0.3 + (0.2 if num == 16 else 0),
                "duration_sector_1": 24.1, "duration_sector_2": 25.2,
                "duration_sector_3": 25.2, "i1_speed": 300, "i2_speed": 280,
                "st_speed": 320, "is_pit_out_lap": (lap == 1),
            })
        fake["stints"].append({"driver_number": num, "lap_start": 1, "lap_end": 3,
                               "compound": "SOFT", "stint_number": 1,
                               "tyre_age_at_start": 0})
        fake["pit"].append({"driver_number": num, "lap_number": 3,
                            "date": _iso(T0 + pd.Timedelta(seconds=225)),
                            "pit_duration": 22.1})
        for lap in (1, 2, 3):
            fake["position"].append({"driver_number": num,
                                     "position": 1 if num == 1 else 2,
                                     "date": _iso(T0 + pd.Timedelta(seconds=lap * 75 - 1))})
    # Télémétrie du tour 2 de VER, ~4 Hz. Une date sur deux est écrite sans
    # fraction de seconde : c'est le piège réel de l'API.
    for i in range(40):
        ts = T0 + pd.Timedelta(seconds=75 + i * 0.25)
        fake["car_data"].append({
            "driver_number": 1, "date": _iso(ts, fractional=(i % 2 == 0)),
            "speed": 200 + 60 * np.sin(i / 6), "throttle": 80,
            "brake": 100 if 10 <= i < 15 else 0, "n_gear": 6, "rpm": 11000,
            "drs": 12 if i > 30 else 0,
        })
        fake["location"].append({"driver_number": 1, "date": _iso(ts, fractional=(i % 3 == 0)),
                                 "x": 1000 + i * 25, "y": 500 - i * 10, "z": 0})
    return fake


def main():
    fake = build_fixtures()
    of1._get = lambda endpoint, **p: fake.get(endpoint, [])
    of1.vider_cache()  # isolation : le cache mémoire survit d'un test à l'autre

    # 1. Horodatages à précision mixte — la régression la plus vicieuse
    car = of1._df(fake["car_data"], dates=("date",))
    assert car["date"].isna().sum() == 0, "des dates perdues (format ISO mixte)"
    print("1) dates précision mixte :", len(car), "points, 0 perdu ✓")

    # 2. Calendrier, trié chronologiquement et numéroté
    sched = of1.get_event_schedule(2026)
    assert list(sched["EventName"]) == ["Belgian Grand Prix", "Dutch Grand Prix"]
    assert list(sched["RoundNumber"]) == [1, 2]
    print("2) calendrier            :", len(sched), "manches ✓")

    # 3. Session et pilotes
    s = of1.get_session(2026, "Dutch Grand Prix", "R")
    d = s.get_driver("VER")
    assert d["FullName"] == "Max VERSTAPPEN" and d["TeamName"] == "Red Bull Racing"
    assert d["HeadshotUrl"].endswith("1.png")
    print("3) pilotes               :", d["Abbreviation"], "/", d["TeamName"], "✓")

    # 4. Contrat de colonnes attendu par app.py
    laps = s.laps
    attendu = ("Driver", "DriverNumber", "LapNumber", "LapTime", "Sector1Time",
               "Sector2Time", "Sector3Time", "Compound", "TyreLife", "Stint",
               "PitInTime", "PitOutTime", "Position", "TrackStatus", "Deleted",
               "DeletedReason", "IsAccurate", "FreshTyre", "SpeedST", "SpeedI1",
               "SpeedI2", "Time", "LapStartDate")
    manquantes = [c for c in attendu if c not in laps.columns]
    assert not manquantes, f"colonnes manquantes : {manquantes}"
    assert laps["LapTime"].dtype.kind == "m", "LapTime doit être un timedelta"
    assert len(laps) == 6
    print("4) tours                 :", len(laps), "tours,", len(attendu), "colonnes ✓")

    # 5. Sélecteurs FastF1
    ver = laps.pick_drivers("VER")
    assert isinstance(ver, of1.Laps) and len(ver) == 3
    fast = ver.pick_fastest()
    assert fast is not None and int(fast["LapNumber"]) == 1
    assert len(laps.pick_drivers(["VER", "LEC"])) == 6
    assert laps.pick_drivers("XXX").pick_fastest() is None, "doit rendre None, pas planter"
    print("5) pick_drivers/fastest  : OK, None si aucun tour ✓")

    # 6. Pneus et arrêts
    assert (ver["Compound"] == "SOFT").all()
    assert list(ver.sort_values("LapNumber")["TyreLife"]) == [1.0, 2.0, 3.0]
    assert ver[ver["LapNumber"] == 3]["PitInTime"].notna().all()
    assert ver[ver["LapNumber"] == 1]["PitOutTime"].notna().all()
    print("6) pneus & arrêts        : compound, âge, IN/OUT ✓")

    # 7. Statut de piste déduit de la direction de course
    assert ver[ver["LapNumber"] == 2]["TrackStatus"].iloc[0] == "4", "SC non propagé"
    assert ver[ver["LapNumber"] == 3]["TrackStatus"].iloc[0] == "1", "vert non repris"
    print("7) TrackStatus           : SC tour 2, vert tour 3 ✓")

    # 8. Télémétrie : distance reconstruite, X/Y appariés, frein booléen
    lap2 = ver[ver["LapNumber"] == 2].iloc[0]
    tel = lap2.get_telemetry()
    assert "Distance" in tel.columns and "X" in tel.columns
    assert tel["Distance"].is_monotonic_increasing, "distance non croissante"
    assert tel["X"].notna().all(), "positions non appariées"
    assert tel["Brake"].dtype == bool and int(tel["Brake"].sum()) == 5
    ref = np.trapezoid(tel["Speed"].values / 3.6, tel["Time"].dt.total_seconds().values)
    ecart = abs(tel["Distance"].iloc[-1] - ref)
    assert ecart < 1.0, f"intégration imprécise : {ecart:.2f} m"
    print(f"8) télémétrie            : {len(tel)} pts, {tel['Distance'].iloc[-1]:.0f} m "
          f"(écart {ecart:.3f} m) ✓")

    # 9. DRS aux codes F1 (10/12/14 = volet ouvert)
    assert int((tel["DRS"] >= 10).sum()) == 9
    print("9) DRS                   :", int((tel["DRS"] >= 10).sum()), "pts ouverts ✓")

    # 10. Météo, direction de course, résultats
    assert {"AirTemp", "TrackTemp", "Rainfall"} <= set(s.weather_data.columns)
    assert "Message" in s.race_control_messages.columns
    res = s.results
    assert {"Abbreviation", "Position", "GridPosition", "TeamName"} <= set(res.columns)
    assert len(res) == 2
    # Statut d'arrivée : OpenF1 n'a pas de champ `status`, seulement des
    # booléens dnf/dns/dsq. Sans leur traduction, un abandon classé 18e était
    # indiscernable d'une arrivée en fond de peloton.
    statuts = dict(zip(res["Abbreviation"], res["Status"]))
    assert statuts["VER"] == "Finished", statuts
    assert statuts["LEC"] == "Retired", statuts
    print("10) météo/RCM/résultats  : format FastF1, abandon distingué ✓")

    print("\n✅ ADAPTATEUR OPENF1 VALIDÉ (contrat figé pour app.py)")


def test_numerotation_manches():
    """Régression : les essais de pré-saison décalaient la numérotation.

    `season_points_before` parcourt les manches 1..N du calendrier SANS
    essais. Si `_find_meeting` numérotait AVEC les essais, la manche N
    désignait la course N-1, la dernière course n'était jamais atteinte et
    ses points disparaissaient du championnat (86 points manquants
    constatés en production)."""
    def iso(s):
        return pd.Timestamp(s).isoformat() + "+00:00"

    fake = {
        "meetings": [
            {"meeting_key": 1200, "meeting_name": "Pre-Season Testing",
             "country_name": "Bahrain", "location": "Sakhir",
             "date_start": iso("2026-02-11T08:00:00"), "circuit_key": 63},
            {"meeting_key": 1201, "meeting_name": "Australian Grand Prix",
             "country_name": "Australia", "location": "Melbourne",
             "date_start": iso("2026-03-06T06:00:00"), "circuit_key": 10},
            {"meeting_key": 1202, "meeting_name": "Chinese Grand Prix",
             "country_name": "China", "location": "Shanghai",
             "date_start": iso("2026-03-20T07:00:00"), "circuit_key": 49},
            {"meeting_key": 1203, "meeting_name": "Japanese Grand Prix",
             "country_name": "Japan", "location": "Suzuka",
             "date_start": iso("2026-04-03T05:00:00"), "circuit_key": 46},
        ],
        # Les essais n'ont que des séances « Day N » : aucune course.
        "sessions": [
            {"meeting_key": 1200, "session_name": "Day 1", "session_key": 1},
            {"meeting_key": 1201, "session_name": "Race", "session_key": 2},
            {"meeting_key": 1202, "session_name": "Sprint", "session_key": 3},
            {"meeting_key": 1202, "session_name": "Race", "session_key": 4},
            {"meeting_key": 1203, "session_name": "Race", "session_key": 5},
        ],
    }
    of1._get = lambda endpoint, **p: fake.get(endpoint, [])
    of1.vider_cache()  # isolation : sinon le calendrier du test précédent ressort

    gps = of1.get_event_schedule(2026, include_testing=False)
    assert list(gps["EventName"]) == ["Australian Grand Prix", "Chinese Grand Prix",
                                      "Japanese Grand Prix"], "essais non exclus"
    assert list(gps["RoundNumber"]) == [1, 2, 3]

    # Chaque numéro de manche doit résoudre la bonne course
    for rnd, attendu in ((1, 1201), (2, 1202), (3, 1203)):
        assert of1._find_meeting(2026, rnd) == attendu, f"manche {rnd} mal résolue"

    # Le week-end sprint doit être reconnu, sinon ses points sont perdus
    fmt = dict(zip(gps["EventName"], gps["EventFormat"]))
    assert fmt["Chinese Grand Prix"] == "sprint_qualifying"
    assert fmt["Australian Grand Prix"] == "conventional"

    # Un meeting d'essais reste résoluble par son nom (mais hors championnat)
    assert of1._find_meeting(2026, "Pre-Season Testing") == 1200
    print("11) numérotation manches : essais exclus, sprint détecté, "
          "dernière manche atteignable ✓")



def test_trafic_reseau():
    """Régression : le calcul du championnat saturait le quota d'OpenF1.

    Sans cache, chaque manche retéléchargeait le calendrier complet — plus
    de 100 requêtes en rafale pour une saison, et 9 manches refusées par le
    serveur (donc absentes du championnat, silencieusement)."""
    from collections import Counter

    fake = {"meetings": [], "sessions": []}
    for i in range(1, 12):
        mk = 1200 + i
        fake["meetings"].append({
            "meeting_key": mk, "meeting_name": f"GP {i}", "country_name": "X",
            "location": "Y", "circuit_key": 10,
            "date_start": pd.Timestamp(f"2026-{i:02d}-01T12:00:00").isoformat() + "+00:00"})
        fake["sessions"].append({"meeting_key": mk, "session_key": mk * 10,
                                 "session_name": "Race"})
        if i in (6, 7, 11):  # week-ends sprint
            fake["sessions"].append({"meeting_key": mk, "session_key": mk * 10 + 1,
                                     "session_name": "Sprint"})

    appels = []
    of1._get = lambda endpoint, **p: (appels.append(endpoint), fake.get(endpoint, []))[1]
    of1.vider_cache()

    sched = of1.get_event_schedule(2026)
    fmt = dict(zip(sched["RoundNumber"], sched["EventFormat"]))
    charge = 0
    for rnd in sched["RoundNumber"]:
        for ses in (["S", "R"] if fmt[rnd] == "sprint_qualifying" else ["R"]):
            of1.get_session(2026, int(rnd), ses)
            charge += 1

    assert charge == 14, charge
    assert len(appels) <= 3, f"{len(appels)} requêtes : le cache ne fonctionne plus"
    # Le cache ne doit pas fausser la résolution des sessions
    assert of1.get_session(2026, 6, "S").session_key == 12061
    assert of1.get_session(2026, 6, "R").session_key == 12060
    print(f"12) trafic réseau        : {charge} sessions en {len(appels)} requêtes "
          f"{dict(Counter(appels))} ✓")


def test_seances_du_weekend():
    """Session1..Session5 : le programme réel de chaque week-end.

    L'app s'en sert pour ne proposer que les séances existantes — un week-end
    sprint n'a qu'un essai libre, en proposer trois mène droit à une erreur de
    chargement. Les colonnes doivent porter les MÊMES libellés que FastF1, en
    ordre chronologique, et rester à None si OpenF1 ne date pas les séances
    (l'app retombe alors sur le programme type du format)."""
    def iso(s):
        return pd.Timestamp(s).isoformat() + "+00:00"

    fake = {
        "meetings": [
            {"meeting_key": 1301, "meeting_name": "Dutch Grand Prix",
             "country_name": "Netherlands", "location": "Zandvoort",
             "date_start": iso("2026-08-21T09:30:00"), "circuit_key": 55},
            {"meeting_key": 1302, "meeting_name": "Chinese Grand Prix",
             "country_name": "China", "location": "Shanghai",
             "date_start": iso("2026-03-20T03:30:00"), "circuit_key": 49},
        ],
        # Volontairement dans le désordre : le tri est fait par l'adaptateur.
        "sessions": [
            {"meeting_key": 1301, "session_name": "Race", "session_key": 20,
             "date_start": iso("2026-08-23T13:00:00")},
            {"meeting_key": 1301, "session_name": "Practice 1", "session_key": 21,
             "date_start": iso("2026-08-21T09:30:00")},
            {"meeting_key": 1301, "session_name": "Qualifying", "session_key": 22,
             "date_start": iso("2026-08-22T13:00:00")},
            {"meeting_key": 1301, "session_name": "Practice 3", "session_key": 23,
             "date_start": iso("2026-08-22T10:30:00")},
            {"meeting_key": 1301, "session_name": "Practice 2", "session_key": 24,
             "date_start": iso("2026-08-21T13:00:00")},
            # Week-end sprint : un seul essai libre, plus SQ et Sprint
            {"meeting_key": 1302, "session_name": "Practice 1", "session_key": 30,
             "date_start": iso("2026-03-20T03:30:00")},
            {"meeting_key": 1302, "session_name": "Sprint Qualifying", "session_key": 31,
             "date_start": iso("2026-03-20T07:30:00")},
            {"meeting_key": 1302, "session_name": "Sprint", "session_key": 32,
             "date_start": iso("2026-03-21T03:00:00")},
            {"meeting_key": 1302, "session_name": "Qualifying", "session_key": 33,
             "date_start": iso("2026-03-21T07:00:00")},
            {"meeting_key": 1302, "session_name": "Race", "session_key": 34,
             "date_start": iso("2026-03-22T07:00:00")},
        ],
    }
    of1._get = lambda endpoint, **p: fake.get(endpoint, [])
    of1.vider_cache()

    sched = of1.get_event_schedule(2026, include_testing=False)
    prog = {r["EventName"]: [r[f"Session{i}"] for i in range(1, 6)]
            for _, r in sched.iterrows()}

    assert prog["Dutch Grand Prix"] == ["Practice 1", "Practice 2", "Practice 3",
                                        "Qualifying", "Race"], prog["Dutch Grand Prix"]
    assert prog["Chinese Grand Prix"] == ["Practice 1", "Sprint Qualifying", "Sprint",
                                          "Qualifying", "Race"], prog["Chinese Grand Prix"]
    # Un sprint ne doit JAMAIS annoncer d'essais 2 ou 3
    assert "Practice 2" not in prog["Chinese Grand Prix"]
    assert "Practice 3" not in prog["Chinese Grand Prix"]

    # Sans date_start, les colonnes restent vides plutôt que d'inventer un
    # programme : l'app bascule alors sur le repli par format.
    fake["sessions"] = [{"meeting_key": 1301, "session_name": "Race", "session_key": 20}]
    of1.vider_cache()
    sched2 = of1.get_event_schedule(2026, include_testing=False)
    assert sched2.loc[0, "Session1"] is None, sched2.loc[0, "Session1"]

    print("13) séances du week-end  : Session1..5 chronologiques, sprint sans FP2/FP3 ✓")


def test_tour_sans_horodatage():
    """Un tour sans date de départ ne doit pas faire échouer la session.

    Régression constatée en production, le jour du GP : `_add_positions`
    passait `LapStartDate` à `merge_asof`, qui refuse une clé nulle
    (« Merge keys contain null values on left side »). OpenF1 ne date pas
    toujours le départ d'un tour — et un seul tour non daté suffisait à rendre
    la session entière inchargeable, l'app renvoyant alors vers un diagnostic
    réseau qui n'avait rien à voir."""
    t0 = pd.Timestamp("2026-08-22T14:00:00")
    laps = pd.DataFrame({
        "DriverNumber": ["1", "1", "1"],
        "LapNumber": [1, 2, 3],
        "LapStartDate": [pd.NaT,                                # non daté
                         t0 + pd.Timedelta(seconds=90),
                         t0 + pd.Timedelta(seconds=180)],
        "LapTime": [pd.Timedelta(seconds=90)] * 3,
    })
    of1._get = lambda endpoint, **p: ([
        {"driver_number": 1, "position": 1,
         "date": (t0 + pd.Timedelta(seconds=100)).isoformat() + "+00:00"},
        {"driver_number": 1, "position": 2,
         "date": (t0 + pd.Timedelta(seconds=200)).isoformat() + "+00:00"},
    ] if endpoint == "position" else [])

    faux = type("S", (), {})()
    faux.session_key = 1
    of1.Session._add_positions(faux, laps)          # ne doit pas lever

    # Les tours datés gardent la bonne position, malgré le tri interne par date
    assert laps.loc[1, "Position"] == 1, laps["Position"].tolist()
    assert laps.loc[2, "Position"] == 2, laps["Position"].tolist()
    # Le tour non daté reste sans position, sans décaler les autres
    assert pd.isna(laps.loc[0, "Position"])

    # Aucun tour daté du tout : tableau sans position, session chargeable
    vierge = laps.copy()
    vierge["LapStartDate"] = pd.NaT
    vierge["Position"] = np.nan
    of1.Session._add_positions(faux, vierge)
    assert vierge["Position"].isna().all()

    # Flux de positions vide ou non daté : pas d'exception non plus
    for recs in ([], [{"driver_number": 1, "date": None, "position": 1}]):
        of1._get = lambda endpoint, _r=recs, **p: _r if endpoint == "position" else []
        of1.Session._add_positions(faux, laps.copy())

    print("16) tour sans horodatage : session chargeable, positions non décalées ✓")


def test_positions_interpolees():
    """Positions X/Y : interpolation temporelle, pas d'appariement au plus proche.

    Régression : `merge_asof` recopiait la dernière position connue. Le flux
    `location` étant plus lâche que `car_data`, des points de télémétrie
    consécutifs sortaient aux MÊMES coordonnées — la carte du circuit se
    réduisait à une poignée de marqueurs empilés au lieu d'un tracé continu.
    Contrepartie à préserver : ne rien inventer là où le flux s'est tu."""
    t0 = pd.Timestamp("2026-08-23T13:00:00")
    n = 60
    car = pd.DataFrame({"Date": [t0 + pd.Timedelta(milliseconds=270 * i) for i in range(n)],
                        "Speed": np.linspace(100, 300, n)})
    # `location` quatre fois plus lâche, avec un long silence au milieu
    idx = [i for i in range(0, n, 4) if not (20 < i < 44)]
    loc = pd.DataFrame({"Date": [car["Date"].iloc[i] for i in idx],
                        "x": [float(i) for i in idx],
                        "y": [float(2 * i) for i in idx],
                        "z": [0.0] * len(idx)})

    out = of1._merge_location(car.copy(), loc)
    X = out["X"].to_numpy()

    # 1. Plus d'escalier : la position suit le temps au lieu de stagner. Les
    #    positions valent i par construction, donc X[i] == i si l'on interpole.
    assert np.allclose(X[:20], np.arange(20.0), atol=1e-5), X[:20]

    # 2. Le silence est comblé jusqu'à 2 s, pas au-delà — vérifié contre la
    #    règle elle-même plutôt que sur des index en dur.
    ns_pos = pd.DatetimeIndex(loc["Date"]).to_numpy(dtype="int64")
    ns_car = pd.DatetimeIndex(car["Date"]).to_numpy(dtype="int64")
    ecart = np.abs(ns_car[:, None] - ns_pos[None, :]).min(axis=1)
    trop_loin = ecart > of1._POS_TROU_MAX.value
    # Hors de la plage couverte par `location`, il n'y a rien à interpoler :
    # extrapoler inventerait une position, on laisse le trou.
    dedans = (ns_car >= ns_pos.min()) & (ns_car <= ns_pos.max())
    assert trop_loin.any() and not trop_loin.all(), "le cas de test doit couvrir les deux"
    assert (~dedans).any(), "le cas de test doit aussi couvrir les bords"
    assert np.isnan(X[trop_loin]).all(), "silence long comblé à tort"
    assert np.isnan(X[~dedans]).all(), "extrapolation hors des relevés connus"
    calculable = ~trop_loin & dedans
    assert not np.isnan(X[calculable]).any(), "position perdue alors qu'elle est calculable"

    # 3. Le premier relevé est repris tel quel, sans décalage
    assert X[0] == 0.0

    # 4. Horodatages dupliqués côté location : pas d'exception
    of1._merge_location(car.copy(), pd.concat([loc, loc.iloc[:3]], ignore_index=True))

    # 5. Aucune position du tout : colonnes vides, pas d'exception
    assert of1._merge_location(car.copy(), pd.DataFrame())["X"].isna().all()

    comble = int((~np.isnan(X)).sum())
    print(f"14) positions X/Y        : {comble}/{n} points positionnés, "
          f"escalier supprimé, silence long préservé ✓")


def test_tracé_lisse():
    """La géométrie du circuit ne doit pas ressortir en POLYGONE.

    Régression : les positions étaient interpolées linéairement entre les
    relevés de `location`, bien plus lâches que `car_data`. Le tracé affiché
    devenait une suite de segments droits reliés par des angles vifs, là où le
    circuit tourne. Une spline cubique passe par les mêmes points en
    arrondissant — et aucun lissage côté app ne peut rattraper ça, des points
    posés sur une corde y restant alignés."""
    t0 = pd.Timestamp("2026-08-23T13:00:00")
    n = 300
    dates = [t0 + pd.Timedelta(milliseconds=270 * i) for i in range(n)]
    th = np.linspace(0, 2 * np.pi, n)
    rayon = 1000.0
    car = pd.DataFrame({"Date": dates, "Speed": np.full(n, 200.0)})

    # `location` cinq fois plus lâche que la télémétrie : le cas qui polygonait
    idx = list(range(0, n, 15))
    loc = pd.DataFrame({"Date": [dates[i] for i in idx],
                        "x": rayon * np.cos(th[idx]), "y": rayon * np.sin(th[idx]),
                        "z": np.zeros(len(idx))})

    out = of1._merge_location(car.copy(), loc)
    ecart_spline = np.nanmax(np.abs(np.hypot(out["X"], out["Y"]) - rayon))

    # Référence : ce que donnait l'interpolation linéaire (les cordes)
    ns = np.array([d.value for d in dates], dtype="float64")
    ns_loc = np.array([dates[i].value for i in idx], dtype="float64")
    lin = np.hypot(np.interp(ns, ns_loc, rayon * np.cos(th[idx])),
                   np.interp(ns, ns_loc, rayon * np.sin(th[idx])))
    ecart_lineaire = np.max(np.abs(lin - rayon))

    assert ecart_spline < ecart_lineaire / 5, (
        f"lissage insuffisant : {ecart_spline:.1f} m contre {ecart_lineaire:.1f} m "
        "en linéaire")
    # Pas d'oscillation : la spline reste dans l'emprise des positions connues
    assert out["X"].max() <= loc["x"].max() + 1.0
    assert out["X"].min() >= loc["x"].min() - 1.0

    # Un relevé incomplet ne doit pas désactiver le lissage du tour entier :
    # la condition « colonne entièrement valide » y suffisait, et une seule
    # valeur manquante suffisait donc à faire ressortir le polygone.
    troue = loc.copy()
    troue.loc[3, "x"] = np.nan
    out_troue = of1._merge_location(car.copy(), troue)
    ecart_troue = np.nanmax(np.abs(np.hypot(out_troue["X"], out_troue["Y"]) - rayon))
    assert ecart_troue < ecart_lineaire / 5, (
        f"une valeur manquante a désactivé le lissage : {ecart_troue:.1f} m")

    # Une colonne z absente ne doit pas dégrader x/y
    sans_z = loc.copy()
    sans_z["z"] = np.nan
    out_z = of1._merge_location(car.copy(), sans_z)
    assert np.nanmax(np.abs(np.hypot(out_z["X"], out_z["Y"]) - rayon)) < ecart_lineaire / 5

    # Moins de 4 relevés : repli linéaire, sans exception
    assert of1._merge_location(car.copy(), loc.iloc[:3])["X"].notna().any()
    # Un seul relevé : rien à interpoler, mais pas d'exception non plus
    assert of1._merge_location(car.copy(), loc.iloc[:1])["X"].isna().all()

    print(f"15) tracé lissé          : écart au circuit réel {ecart_spline:.1f} m "
          f"contre {ecart_lineaire:.1f} m en linéaire, "
          f"{ecart_troue:.1f} m avec un relevé incomplet ✓")


if __name__ == "__main__":
    main()
    test_numerotation_manches()
    test_trafic_reseau()
    test_seances_du_weekend()
    test_positions_interpolees()
    test_tracé_lisse()
    test_tour_sans_horodatage()
