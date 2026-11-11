# NearBite

NearBite is a Streamlit app for NYC restaurant discovery, saved places, user profiles, and personalized recommendations.


- Original Repository: [NearBite](https://github.com/JonasChenJusFox/ML_FinalProject)
- Live app: [NearBite on Cloudflare](https://nearbite.jonas-aitherpath.workers.dev/)

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
- `Dockerfile`: Python/Streamlit image for Cloudflare Containers
- `cloudflare/worker.ts`: HTTP/WebSocket proxy and container lifecycle
- `wrangler.jsonc`: Cloudflare Worker, container, and runtime configuration

## Data Sources

| Source | Used For |
| --- | --- |
| [Yelp Fusion API](https://fusion.yelp.com/) | Restaurant metadata such as name, rating, price, categories, hours, and images |
| [Google Places API](https://developers.google.com/maps/documentation/places/web-service/overview) | Review text used for summaries, embeddings, and vibe matching |
| [NYC Open Data - DOHMH Restaurant Inspections](https://data.cityofnewyork.us/Health/DOHMH-New-York-City-Restaurant-Inspection-Results/43nn-pn8j/about_data) | Supplemental official restaurant registry data |
| [TripAdvisor NYC Dataset (Kaggle, 10k+)](https://www.kaggle.com/datasets/rayhan32/trip-advisor-newyork-city-restaurants-dataset-10k) | Review text for vibe tag extraction and NLP training |
| [Yelp Open Dataset (Kaggle)](https://www.kaggle.com/datasets/yelp-dataset/yelp-dataset) | Sentiment analysis and embedding model training on an NYC subset |
| Synthetic user data | Local personalization and interaction-history development |

The Kaggle Yelp NYC dataset is outdated and is not used as the live recommendation source.

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
NEARBITE_REQUIRE_MONGO=false
```

`NEARBITE_SEARCH_MODE=fast` avoids loading the SentenceTransformer model and is the Cloudflare default. Use `semantic` only with enough RAM/CPU and the matching embedding assets. Local development can use the JSON database; Cloudflare always sets `NEARBITE_REQUIRE_MONGO=true` and checks MongoDB before starting Streamlit.

## Cloudflare Deployment

The app runs on [Cloudflare Containers](https://developers.cloudflare.com/containers/get-started/), behind a Worker. Streamlit needs a Python server and WebSockets, so this repository is not a static Cloudflare Pages project.

Prerequisites: Node.js 22 or later, a running Docker engine, a Cloudflare account with the [Workers Paid plan](https://developers.cloudflare.com/containers/platform/pricing/), and an externally hosted MongoDB database. Containers incur usage charges in addition to the plan. Keep the existing MongoDB database and database name when migrating to preserve accounts, profiles, and interactions.

Install deployment tools and authenticate:

```bash
npm ci
npx wrangler login
npx wrangler whoami
npm run check
```

Set the Worker secrets (Wrangler prompts for each value). Use the production MongoDB connection string and a random cookie secret, for example generated with `openssl rand -hex 32`. Keep the cookie secret stable across deployments.

```bash
npx wrangler secret put MONGO_URI
npx wrangler secret put STREAMLIT_SERVER_COOKIE_SECRET
npm run deploy
```

On first setup, accept Wrangler's prompt to create the Worker when adding secrets. Configure `MONGO_DBNAME`, `MONGO_TIMEOUT_MS`, and `NEARBITE_SEARCH_MODE` under `vars` in `wrangler.jsonc`. Secrets are passed into the container at runtime; `.env`, `.dev.vars`, Streamlit secrets, and `data/local_db.json` are excluded from the image. MongoDB must allow connections from the container network; verify the database provider's network access settings before deployment.

Wrangler builds the Linux container, uploads the image, and deploys the Worker. The URL is `https://nearbite.<your-workers-subdomain>.workers.dev`. Initial provisioning can take several minutes:

```bash
npx wrangler containers list
curl --fail https://nearbite.<your-workers-subdomain>.workers.dev/_stcore/health
```

The configuration allows one `standard-1` instance (4 GiB RAM) and sends every request to the same named container so Streamlit sessions and generated media stay together. The runtime stops the container after 10 minutes of inactivity; open connections keep it active. A cold start or deployment can reset in-memory UI sessions. MongoDB retains saved application data. The proxy preserves WebSocket upgrades and leaves Streamlit's CORS/XSRF protection enabled.

For a custom domain, add a Custom Domain to the `nearbite` Worker in Cloudflare's dashboard after the `workers.dev` URL passes validation. Verify signup/login, search, maps, save/like/review, comments, and questionnaire persistence, including after a container restart, before retiring the previous hosting service.

### Local Cloudflare development

Create an ignored `.dev.vars` file with `MONGO_URI` for a development database and `STREAMLIT_SERVER_COOKIE_SECRET`, then run `npm run dev` with Docker running. Use a separate database for local testing. For Python-only development with the local JSON database, use `streamlit run app.py` as above.

## Useful Commands

```bash
python -m compileall -q frontend integration recommendation
python testing/run_evaluation.py
```
