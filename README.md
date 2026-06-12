# F1 Style Decoder — Déploiement sur Streamlit Community Cloud

Objectif : rendre l'app accessible depuis n'importe quel navigateur (PC, téléphone), gratuitement.

## Étape 1 — Repo GitHub (5 min)

1. Crée un compte sur github.com si tu n'en as pas.
2. Bouton **New repository** → nom : `f1-style-decoder` → visibilité **Public** → Create.
3. Dans le repo : **Add file → Upload files** → glisse `app.py`, `requirements.txt` et `.gitignore` → **Commit changes**.

Pas besoin de git en ligne de commande, tout se fait depuis le navigateur.

## Étape 2 — Streamlit Community Cloud (5 min)

1. Va sur **share.streamlit.io** → **Continue with GitHub** (autorise l'accès).
2. **Create app** → choisis le repo `f1-style-decoder`, branche `main`, fichier principal `app.py`.
3. **Deploy**. Le premier démarrage prend 3-5 min (installation des dépendances).
4. Ton URL : `https://<nom-choisi>.streamlit.app`

## Étape 3 — Sur le téléphone

1. Ouvre l'URL dans le navigateur.
2. **Ajouter à l'écran d'accueil** (menu partage iOS / menu ⋮ Android).
3. L'icône se comporte comme une app : plein écran, accès direct.

## Limites à connaître (tier gratuit)

- **Cache éphémère** : le serveur redémarre régulièrement et vide `cache_f1/`. Le premier chargement d'une session après redémarrage reprend 1-3 min (re-téléchargement des données FastF1). Les chargements suivants sont rapides.
- **RAM limitée** : si plusieurs grosses sessions (courses complètes) sont chargées en cache, l'app peut redémarrer toute seule. Dans ce cas : menu **Manage app → Reboot**.
- **Mise en veille** : sans visite pendant quelques jours, l'app s'endort. Le premier accès la réveille (~1 min).

## Mises à jour

Modifie `app.py` directement sur GitHub (icône crayon) → Commit. L'app se redéploie automatiquement en ~1 min.
