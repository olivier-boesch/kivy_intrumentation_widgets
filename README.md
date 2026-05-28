# Kivy Instrumentation Widgets

Un ensemble de composants d'instrumentation pour Python + Kivy, conçus pour créer des écrans de contrôle, des tableaux de bord et des interfaces de mesure.

# design

Axés sur un fond et les couleurs classiques de kivy. le design est flat pour être simple et fonctionnel.

* Fond : noir ( `#000000FF` )
* Texte : blanc ( `#FFFFFFFF` )
* Éléments graphiques interactif : Bleu kivy ( `[0.2, 0.6, 0.8, 1]` ou `#336699FF`)
* Élémensts graphiques de décor : Bleu kivy avec un alpha plus faible de 0.3 ( `[0.2, 0.6, 0.8, 0.3]` ou `#33669955`)

Palette de couleurs :

<svg width="195" height="60" viewBox="0 0 185 60" xmlns="http://www.w3.org/2000/svg" style="background:#000; display:block;">
  <rect x="10" y="10" width="40" height="40" fill="#000000FF" />
  <rect x="55" y="10" width="40" height="40" fill="#FFFFFFFF" />
  <rect x="100" y="10" width="40" height="40" fill="#336699FF" />
  <rect x="145" y="10" width="40" height="40" fill="#33669955" />
</svg>

## Composants principaux

- **`FlatButton`, `FlatToggleButton`** (`flatbutton.py`)
  - Boutons plats avec effet de surbrillance et support de groupes de basculement.
- **`BorderWrapper`** (`borderwrapper.py`)
  - Conteneur avec bordure arrondie et titre intégré pour structurer les panneaux de contrôle.
- **`CircularGauge`** (`jauge.py`)
  - Jauge circulaire animée avec affichage de la valeur, de l'unité et d'une moyenne mobile.
- **`RollingChart`** (`rollingchart.py`)
  - Graphique en courbe à fenêtre glissante avec auto-échelle verticale et axes unitaires.
- **`CircularTimer`** (`timer.py`)
  - Timer visuel animé montrant le temps restant sous forme d'arc circulaire.
- **`ValidationWidget`** (`validationwidget.py`)
  - Contrôle de validation par glissement et action circulaire activable.
- **`UnitNumberPopup`** (`valuepopup.py`)
  - Popup numérique avec sélection de préfixes SI et d'unités compatibles via Pint.
- **`RotaryEncoderWidget`** (`encoder.py`)
  - Encodeur rotatif interactif pour l'ajustement fin de valeurs et l'affichage d'une unité.

## Dependencies

- Python 3.14+
- Kivy 2.3+
- Pint

Le dépôt contient également un sous-dossier `pint-master/` pour la gestion locale de la dépendance Pint.

## Exemples de démo

Chaque module principal peut être démarré directement pour visualiser son application de test :

```bash
.venv/bin/python flatbutton.py
.venv/bin/python jauge.py
.venv/bin/python rollingchart.py
.venv/bin/python timer.py
.venv/bin/python validationwidget.py
.venv/bin/python valuepopup.py
.venv/bin/python encoder.py
```

## Captures d'écran

Les captures d'écran de démonstration sont générées dans le dossier `screenshots/` :

- `screenshots/flatbutton.png`
- `screenshots/jauge.png`
- `screenshots/rollingchart.png`
- `screenshots/timer.png`
- `screenshots/validationwidget.png`
- `screenshots/valuepopup.png`
- `screenshots/encoder.png`

![FlatButton](screenshots/flatbutton.png)
![Jauge circulaire](screenshots/jauge.png)
![RollingChart](screenshots/rollingchart.png)
![Timer](screenshots/timer.png)
![ValidationWidget](screenshots/validationwidget.png)
![ValuePopup](screenshots/valuepopup.png)
![RotaryEncoder](screenshots/encoder.png)

## Génération des captures d'écran

Un script d'aide est disponible pour recréer les images automatiquement :

```bash
.venv/bin/python generate_screenshots.py <module>.py screenshots/<name>.png
```

Par exemple :

```bash
.venv/bin/python generate_screenshots.py flatbutton.py screenshots/flatbutton.png
```

## Objectif du projet

Ce dépôt vise à fournir des éléments d'interface modernes et réutilisables pour des applications d'instrumentation embarquées ou de monitoring. Chaque widget est pensé pour s'intégrer dans des tableaux de bord Kivy et permet de gérer des unités physiques avec la bibliothèque Pint.
