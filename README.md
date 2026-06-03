# NearBite

NearBite is a Streamlit app for NYC restaurant discovery, saved places, user profiles, and personalized recommendations.

Live app: https://nearbite-2glis.ondigitalocean.app/

## Features

- Natural-language restaurant search
- Advanced filters for cuisine, price, borough, rating, and travel radius
- Map view with restaurant pins
- Save, like, review, and comment interactions
- Signup/login with MongoDB persistence
- Onboarding questionnaire for taste preferences
- Fast search mode for small hosted containers, with optional semantic search mode

## Project Structure

- `app.py`: Streamlit entrypoint
- `frontend/`: pages, UI components, auth state, app styling, and display adapters
- `integration/`: search API, MongoDB repositories, user profiles, and wrapped summaries
- `recommendation/`: ranking and scoring utilities
- `embeddings/`: query parser, vector helpers, and offline embedding/index tooling
- `data/`: restaurant dataset and optional semantic retrieval assets
- `testing/`: evaluation fixtures and reports
- `Dockerfile`: DigitalOcean deployment image

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

## Environment Variables

```bash
MONGO_URI=<MongoDB connection string>
MONGO_DBNAME=NearBite
MONGO_TIMEOUT_MS=2000
NEARBITE_SEARCH_MODE=fast
NEARBITE_LOCAL_DB_PATH=data/local_db.json
```

`NEARBITE_SEARCH_MODE=fast` is recommended for DigitalOcean's smaller containers. Use `NEARBITE_SEARCH_MODE=semantic` only when the container has enough RAM/CPU for the SentenceTransformer model.

## DigitalOcean Deployment

Use the root `Dockerfile` as a single web service.

Health check path:

```text
/_stcore/health
```

Recommended production environment variables:

```bash
MONGO_URI=<your MongoDB Atlas or DigitalOcean Mongo connection string>
MONGO_DBNAME=NearBite
MONGO_TIMEOUT_MS=2000
NEARBITE_SEARCH_MODE=fast
```

After deployment, test signup/login, search, map loading, save/like/review, comments, and questionnaire persistence.

## Useful Commands

```bash
python -m compileall -q frontend integration recommendation
python testing/run_evaluation.py
```
