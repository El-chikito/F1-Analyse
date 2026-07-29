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
        "car_data": [], "location": [], "session_result": [], "starting_grid": [],
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
    print("10) météo/RCM/résultats  : format FastF1 ✓")

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


if __name__ == "__main__":
    main()
    test_numerotation_manches()
