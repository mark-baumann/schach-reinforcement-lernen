# schach-reinforcement-lernen

Ein Schachprojekt mit zwei Teilen:

- **App** ([`app.py`](./app.py)): Eine spielbare Streamlit-Web-App gegen eine Schach-KI
  (Minimax mit Alpha-Beta-Suche und handgeschriebener Bewertungsfunktion).
- **Notebooks** ([`notebooks/`](./notebooks)): Google-Colab-fähige Jupyter-Notebooks, die einen
  Schach-Agenten per **Self-Play Reinforcement Learning** trainieren und interaktiv spielbar
  machen.

## App starten

```bash
pip install -r requirements.txt
streamlit run app.py
```

Alternativ per Docker:

```bash
docker build -t schach .
docker run -p 8520:8520 schach
```

## Reinforcement-Learning-Notebooks

| Notebook | Beschreibung | Colab |
| --- | --- | --- |
| [`01_train_chess_rl_agent.ipynb`](./notebooks/01_train_chess_rl_agent.ipynb) | Trainiert ein neuronales Bewertungsnetz per Self-Play, plottet den Lernfortschritt und speichert das Modell. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mark-baumann/schach-reinforcement-lernen/blob/main/notebooks/01_train_chess_rl_agent.ipynb) |
| [`02_play_against_agent.ipynb`](./notebooks/02_play_against_agent.ipynb) | Lädt einen trainierten Checkpoint und lässt dich interaktiv per Texteingabe im Notebook dagegen spielen. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mark-baumann/schach-reinforcement-lernen/blob/main/notebooks/02_play_against_agent.ipynb) |

Beide Notebooks sind eigenständig lauffähig (kein lokales Setup nötig) und installieren ihre
Abhängigkeiten (`python-chess`) selbst; PyTorch ist in Colab vorinstalliert. Details zum
RL-Ansatz (Stellungskodierung, Self-Play, Reward Shaping, Grenzen) stehen jeweils im Notebook
selbst.

Die App und die Notebooks sind aktuell unabhängig voneinander: `app.py` nutzt eine klassische
Minimax-Suche, die Notebooks trainieren ein separates neuronales Netz. Wie man den in den
Notebooks trainierten Agenten in die App einbindet, ist in
[`01_train_chess_rl_agent.ipynb`](./notebooks/01_train_chess_rl_agent.ipynb) unter
"Weiterführende Ideen" skizziert.
