# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Projet et utilisateur francophones — réponds en français, commente en français.

## Ce que c'est

« Analyse F1 » : app Streamlit mono-fichier (`app.py`, ~3000 lignes) d'analyse
télémétrique F1 basée sur FastF1, déployée sur Streamlit Community Cloud depuis
`main` (chaque push sur `main` redéploie l'app du user — voir README.md pour le
setup). Le user la consulte surtout **sur téléphone**.

## Commandes

```bash
pip install -r requirements.txt        # + playwright pour les tests navigateur
streamlit run app.py                   # http://localhost:8501

python3 -m py_compile app.py           # check syntaxe minimal

# Test de démarrage sans navigateur (attrape les exceptions au boot) :
python3 -c "
from streamlit.testing.v1 import AppTest
at = AppTest.from_file('app.py', default_timeout=120); at.run()
assert not at.exception, at.exception[0].value"

# Test rendu réel : Playwright + chromium préinstallé (/opt/pw-browsers/chromium),
# contexte mobile (UA iPhone + is_mobile) pour tester le mode compact.
```

⚠️ Dans l'environnement sandbox Claude, le réseau vers `livetiming.formula1.com`
et l'API FastF1 est **bloqué** : impossible de charger une vraie session. On ne
teste donc que le boot (écran de bienvenue) + la logique pure en standalone.
`s.load()` FastF1 n'échoue PAS quand l'API est injoignable — il rend une session
vide (d'où la garde dans `load_session` qui vérifie `s.laps`).

## Architecture (mono-fichier, ordre d'exécution = structure)

`app.py` s'exécute de haut en bas à chaque interaction (modèle Streamlit) :

1. **Docstring** = changelog maintenu à la main. Ajouter une entrée à chaque
   changement notable (convention du repo).
2. Constantes : `TEAM_COLORS` (palette 2026 + équipes historiques),
   `COMPOUND_COLORS`, `CIRCUITS_INFO` (briefings circuits écrits main, dont les
   zones alimentent les presets de l'onglet Zoom).
3. Helpers purs (formatage, `_chan`, analyse virages, diagramme g-g).
4. **Loaders cachés** : `load_session` (`st.cache_resource`, `max_entries=3` —
   une session pèse des centaines de Mo, le Cloud a 1 Go), `load_schedule`,
   `season_points_before` (points pilotes + constructeurs + countback),
   `compute_race_gaps`, `field_corner_profile`, `load_team_radio`
   (`st.cache_data`). Les loaders cachés ne doivent PAS émettre de `st.*`
   (rejoués à chaque hit de cache → warnings dupliqués).
5. Sidebar (saison/GP/session) + **écran de bienvenue** (mêmes widgets, clés
   `home_*`) → `st.session_state.session_loaded` ; les paramètres ne
   s'appliquent qu'au clic sur « Charger la session ».
6. Chargement session + `circuit_info`/`corners_df`/`TRACK_ROTATION` (globals
   utilisés par les pages) + en-tête commun (météo, durée).
7. Deux pages via `st.navigation` : `page_timing` (« Overview session »,
   défaut) et `page_style` (comparaison 2 pilotes, ~14 onglets).

**Mode mobile** : global `MOBILE` (toggle sidebar, auto-détecté par user-agent).
Tout passe par les wrappers `plot()` (dragmode off, modebar cachée) et
`show_table()` (HTML natif au lieu de `st.dataframe` — canvas flou sur Retina).
Toujours utiliser ces wrappers, jamais `st.plotly_chart`/`st.dataframe` direct
pour du contenu principal.

## Pièges durement acquis (ne pas re-payer)

- **`Deleted`/`DeletedReason` ne sont remplis que si `messages=True`** dans
  `session.load()`. Idem : la météo exige `weather=True`.
- **X/Y FastF1 sont en 1/10 de mètre** → diviser par 10 pour le g-g. Les
  virages (`corners_df["X"/"Y"]`) partagent le repère des télémétries ;
  `_rotate_xy` applique la rotation TV officielle à TOUTES les cartes.
- **`delta_time()` renvoie du car data SANS X/Y** → projeter via `np.interp`
  sur la télémétrie complète.
- **`pick_fastest()` peut renvoyer `None`** (aucun tour personal-best) →
  toujours garder.
- **`TrackStatus`** = concaténation de codes : 4=SC, 5=rouge, 6/7=VSC
  (`_is_neutralized`).
- **Streamlit ≥ 1.59 : selectbox = react-aria** (`input[role="combobox"]` dans
  `[data-testid="stSelectbox"]`), plus BaseWeb. Le patch anti-clavier mobile
  (bloc `components.html` sous `if MOBILE:`) cible les deux générations ; si le
  clavier réapparaît sur téléphone, c'est que le DOM Streamlit a encore changé —
  inspecter avec Playwright mobile et adapter `SEL`.
- **`d1 == d2` interdit** (index dupliqué) — gardé après les selectbox pilotes.
- **Résultats Sprint** : colonnes `Points`/`Time` vides côté FastF1 → fallback
  barème officiel (`points_from_results`) et écarts reconstruits depuis les laps.
- **F1 renvoie HTTP 403 aux IP de datacenter** — constaté en prod sur Streamlit
  Cloud : `livetiming.formula1.com` refuse TOUS les flux, la session se charge
  vide. D'où `select_data_host()` (sonde les deux serveurs au boot, cache 1 h,
  bascule `fastf1._api.base_url` sur le miroir `livetiming-mirror.fastf1.dev`).
  Symptôme distinctif : le **calendrier** se charge (autre hôte) mais **aucune
  session** ne passe. Ne pas confondre avec « session pas encore publiée ».
- **Repli miroir FastF1 incomplet** : `fetch_page` (`fastf1._api`) ne bascule
  sur le miroir que si le serveur répond HTTP >= 400. Une *exception* de
  connexion (timeout, reset) court-circuite le repli → d'où aussi
  `_patch_fastf1_mirror_fallback()`. Les deux correctifs sont complémentaires.
  Le parcours d'échec expose un panneau 🩺 Diagnostic (`_capture_fastf1_logs`
  + `_network_diagnostic`, qui sonde un VRAI fichier de données, pas la racine
  du site) : c'est LUI qu'il faut lire avant de supposer une cause — c'est ce
  qui a permis d'identifier le 403 sans pouvoir joindre les serveurs F1.
- **Radios** : flux `TeamRadio.json` non documenté sur
  `livetiming.formula1.com/static/` + `session.api_path` ; miroir
  `livetiming-mirror.fastf1.dev` en secours ; JSON encodé `utf-8-sig`.
- `width="stretch"` partout (pas `use_container_width`, déprécié).

## Workflow git de ce repo

Branche de travail `claude/code-review-improvements-ccaz9o` → commit → push →
**fast-forward `main`** (`git checkout main && git merge --ff-only <branche> &&
git push`) : le user a validé ce flux, `main` déclenche le déploiement.
Messages de commit en français, détaillés (voir `git log`).
