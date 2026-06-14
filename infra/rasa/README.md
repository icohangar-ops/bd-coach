# BD Coach — Rasa NLU

Minimal Rasa 3.6 project for the BD Coach assistant (intent routing for pipeline/deal queries).
Topic intents from `config/topics` are mounted read-only at `/app/topics` in the container.

**First run must train a model** (the compose `command` runs `rasa run`, which needs a model):

```bash
docker compose run --rm rasa train
docker compose up -d rasa
```
