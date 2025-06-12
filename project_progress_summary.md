# Movie Recommender System - Project Progress Summary

**Date:** June 5, 2025
**Project:** MovieLens Recommender System Backend API

## 1. Project Objective

To develop and deploy a backend API for a movie recommendation system. The system uses collaborative filtering on the MovieLens dataset and fetches movie details from the OMDb API. The primary deployment target is Heroku.

## 2. Technology Stack

*   **Backend Framework:** FastAPI (Python)
*   **Recommendation Engine:** `scikit-surprise` (SVD algorithm)
*   **Data Storage (for training & popular movies):** PostgreSQL
*   **Movie Metadata:** OMDb API (via `httpx` for asynchronous requests)
*   **Deployment Platform:** Heroku
*   **Data Handling:** Pandas, SQLAlchemy
*   **Environment Management:** `python-dotenv`, Pydantic settings
*   **Version Control:** Git

## 3. Key Accomplishments & Work Done

### 3.1. Initial Setup & Data Handling

*   **Data Loading Service (`data_loader.py`):** Implemented a service to load and merge MovieLens `ratings.csv` and `links.csv` into a pandas DataFrame, mapping users to IMDb IDs and ratings.
*   **Configuration (`config.py`, `.env`):** Set up centralized configuration for database URLs, API keys, and data paths.

### 3.2. Recommendation Model Development

*   **SVD Model Training (`recommender_service.py`, `train_model_from_db.py`):**
    *   Developed a `RecommenderService` to encapsulate model training, prediction, and movie detail fetching.
    *   Implemented a script to train a Singular Value Decomposition (SVD) model using `scikit-surprise` on data loaded from the PostgreSQL database.
    *   The model, trainset, and IMDb ID mappings are persisted using `joblib` (e.g., `svd_model.joblib`).
*   **Popular Movies Fallback:** Implemented logic to calculate and store popular movies as a fallback for new users or when personalized recommendations cannot be generated.

### 3.3. FastAPI Backend API

*   **API Endpoints (`main.py`):**
    *   Created a `/recommendations/{user_id}` endpoint to provide movie recommendations.
    *   Integrated the `RecommenderService` to generate personalized recommendations.
*   **Asynchronous Operations:** Utilized `async/await` for fetching movie details from the OMDb API to prevent blocking.

### 3.4. OMDb API Integration

*   **Movie Detail Fetching (`recommender_service.py`):**
    *   Implemented `get_movie_details_by_imdb_id` to asynchronously fetch movie details (title, poster, plot, etc.) from OMDb using IMDb IDs.
    *   Handled IMDb ID formatting (ensuring "tt" prefix and correct numeric length).
*   **Enhanced Logging & Error Handling:** Added detailed logging for OMDb API calls, including request URLs (API key redacted), IMDb ID transformations, and API error responses to aid debugging.

### 3.5. Heroku Deployment & Debugging

*   **Initial Deployment Setup:**
    *   Configured `Procfile` for `uvicorn` web server.
    *   Managed dependencies with `requirements.txt`.
    *   Specified Python version using `.python-version` (currently 3.9).
    *   Set up Heroku environment variables for `DATABASE_URL`, `OMDB_API_KEY`, etc.
*   **Troubleshooting Deployment Issues:**
    *   Resolved `ModuleNotFoundError` by adding missing dependencies (e.g., `httpx`) to `requirements.txt`.
    *   Addressed import errors by adjusting to relative imports within the `backend/app` package structure for Heroku compatibility.
*   **Debugging Runtime Errors on Heroku:**
    *   **SQL Query Fixes:** Corrected PostgreSQL query for popular movies by ensuring proper column name casing and quoting (e.g., `l."imdbId"` instead of `l.imdb_id`), resolving `psycopg2.errors.UndefinedColumn`.
    *   **OMDb API Call Errors:** Investigated and improved logic for "Incorrect IMDb ID" errors from OMDb, focusing on ID formatting and logging.
    *   **`NameError: name 'logger' is not defined`:** Fixed by adding `import logging` and initializing the logger instance in `recommender_service.py`.

### 3.6. Custom Domain Configuration

*   **Added Custom Domains to Heroku:**
    *   Successfully added `salihrogo.me` (root domain) and `www.salihrogo.me` (subdomain) to the Heroku application (`movie-recommender-ibu2025`).
*   **DNS Configuration:**
    *   Heroku provided DNS targets for both domains:
        *   `salihrogo.me` -> `endothelial-pineapple-6b17pblou03osp35nrn6bnq5.herokudns.com` (requires `ALIAS`/`ANAME` record at registrar).
        *   `www.salihrogo.me` -> `reticulated-rooster-ng3yl1yo582aphkcw3m6oxj1.herokudns.com` (requires `CNAME` record at registrar).
*   **SSL Certificate Management:**
    *   Enabled Heroku's Automated Certificate Management (ACM).
    *   Successfully issued SSL certificates for both `salihrogo.me` and `www.salihrogo.me` by Let's Encrypt via Heroku.

## 4. Current Status

*   The backend API is deployed on Heroku.
*   The recommendation endpoint `/recommendations/{user_id}` is functional.
*   **`www.salihrogo.me` is correctly pointing to the Heroku app and serving content over HTTPS.**
*   **`salihrogo.me` (root domain) is now correctly pointing to the Heroku app and serving content over HTTPS.**

## 5. Next Steps (Brief)

*   **Near-term:** Consider upgrading Python version from 3.9 (EOL approaching).
*   Monitor OMDb API calls for any persistent "Incorrect IMDb ID" issues and refine if necessary.
*   Continue testing with various user IDs and edge cases.

## 6. Key Learnings & Challenges

*   Navigating Heroku deployment intricacies (buildpacks, environment variables, logging).
*   Debugging issues specific to the production environment (e.g., database differences, pathing).
*   The importance of robust logging for diagnosing external API interaction problems.
*   Complexities of DNS configuration and propagation for custom domains and SSL.
*   Ensuring correct formatting and handling of identifiers (e.g., IMDb IDs) across different services.

---

This summary should provide a good overview for your mentor.
