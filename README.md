---
title: Analyse F1
emoji: 🏎️
colorFrom: red
colorTo: gray
sdk: streamlit
app_file: app.py
pinned: false
short_description: Analyse télémétrique des styles de pilotage en Formule 1
---

# 🏎️ Analyse F1

Lecture télémétrique des styles de pilotage en Formule 1, basée sur
[FastF1](https://docs.fastf1.dev/). Application Streamlit mono-fichier (`app.py`).

## ⚠️ Où l'héberger : la F1 filtre les hébergeurs

C'est **le** point à connaître avant de déployer. Les serveurs de données F1
(`livetiming.formula1.com`) renvoient **HTTP 403 aux adresses IP de datacenter**.
Diagnostiqué en production sur Streamlit Community Cloud : le calendrier se
charge (il vient d'un autre serveur) mais **aucune session** ne passe.

Vérifié sur place, sans ambiguïté :

| Test | Résultat |
| --- | --- |
| Serveur F1, identité FastF1 (`BestHTTP`) | 403 |
| Serveur F1, identité navigateur | 403 |
| Serveur F1, identité `curl` | 403 |
| Miroir FastF1, session récente | 404 |
| Miroir FastF1, session de la saison précédente | 404 |

Le blocage vise donc l'**IP**, pas la signature du client : aucun réglage de
l'app ne le contourne, et le miroir communautaire ne sert pas les flux de
session. En cas d'échec, l'app affiche un panneau **🩺 Diagnostic** qui rejoue
ces tests et conclut par un verdict — c'est lui qu'il faut lire en premier.

**Hébergements qui fonctionnent** : en local (connexion personnelle), ou tout
hébergeur dont les adresses ne sont pas filtrées.

## Déploiement sur Hugging Face Spaces

Le tier gratuit offre 16 Go de RAM (contre 1 Go sur Streamlit Cloud), ce qui
tient largement plusieurs sessions en cache.

1. Crée un compte sur [huggingface.co](https://huggingface.co).
2. **New** → **Space**. Nom au choix, **SDK : Streamlit**, hardware *CPU basic*
   (gratuit), visibilité *Public*.
3. Envoie les fichiers `app.py`, `requirements.txt` et `README.md` — onglet
   **Files** → **Add file** → *Upload files*, ou en ligne de commande :

   ```bash
   git remote add hf https://huggingface.co/spaces/<compte>/<espace>
   git push hf main
   ```

   L'en-tête YAML en haut de ce README est lu par Hugging Face pour configurer
   l'espace (titre, icône, SDK) : le conserver.
4. Le premier démarrage prend 3-5 min (installation des dépendances).
   URL finale : `https://<compte>-<espace>.hf.space`

Si le chargement d'une session échoue, ouvre le panneau **🩺 Diagnostic** : il
dira immédiatement si les adresses de cet hébergeur sont filtrées elles aussi.

## En local

```bash
pip install -r requirements.txt
streamlit run app.py          # http://localhost:8501
```

C'est le mode le plus fiable : la connexion personnelle n'est pas filtrée.
Pour y accéder depuis un téléphone, exposer le port via un tunnel privé
(Tailscale, par exemple) plutôt que d'ouvrir la machine sur Internet.

## Sur le téléphone

Ouvre l'URL, puis **Ajouter à l'écran d'accueil** (menu partage iOS / menu ⋮
Android) : l'icône se comporte comme une app native. Le **mode compact** de
l'app se déclenche automatiquement (détection par user-agent, forçable dans la
barre latérale).

## Limites des tiers gratuits

- **Cache éphémère** : le conteneur redémarre régulièrement et vide `cache_f1/`.
  Le premier chargement d'une session reprend alors 1-3 min ; les suivants sont
  rapides.
- **Mise en veille** : sans visite pendant plusieurs jours, l'espace s'endort.
  Le premier accès le réveille (~1 min).
- **RAM** : le cache de sessions est plafonné à 3 entrées (`max_entries=3`) —
  une session complète pèse plusieurs centaines de Mo.

## Développement

Voir `CLAUDE.md` : architecture, commandes de test et pièges FastF1/Streamlit
déjà rencontrés (à lire avant de modifier `app.py`). Le changelog est maintenu
à la main dans le docstring en tête de `app.py`.
