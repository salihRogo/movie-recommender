# Movie Recommender Backend

This is the backend for the Movie Recommender system, built using FastAPI.

## Steps to Run the Project

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/salihRogo/movie-recommender.git
   cd backend
   ```

2. **Set Up a Virtual Environment**: Create and activate a virtual environment to isolate dependencies.
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3. **Install Dependencies**: Install the required Python packages listed in `requirements.txt.`
    ```bash
    pip install -r requirements.txt
    ```

4. **Prepare the Data**: Ensure the `data/` folder contains the `movies.csv` and `ratings.csv` files. These files should already be included in the repository.

5. **Run the Application**: Use uvicorn to start the FastAPI application.
    ```bash
    uvicorn app.main:app --host
    ```

## Steps to Test the Routes on Postman

1. **Start the Application**:
   Make sure the application is running by following the steps above.

2. **Open Postman**:
   Download and install [Postman](https://www.postman.com/) if you don’t already have it.

3. **Test the API Endpoints**:
   Use the following endpoints to test the application:

   - **Root Endpoint**:
     - URL: `http://127.0.0.1:8000/`
     - Method: `GET`
     - Response: `{"message": "Movie Recommender API is running"}`

   - **Search Movies by Title**:
     - URL: `http://127.0.0.1:8000/movies/search/{title}`
     - Method: `GET`
     - Example: `http://127.0.0.1:8000/movies/search/toy`
     - Response: A list of movies matching the title.

   - **Get Popular Movies**:
     - URL: `http://127.0.0.1:8000/movies/popular`
     - Method: `GET`
     - Query Parameter: `limit` (optional, default is 10)
     - Example: `http://127.0.0.1:8000/movies/popular?limit=5`
     - Response: A list of popular movies.

   - **Get Recommendations by Movie ID**:
     - URL: `http://127.0.0.1:8000/recommendations/movie/{movie_id}`
     - Method: `GET`
     - Example: `http://127.0.0.1:8000/recommendations/movie/1`
     - Response: A list of recommended movies based on the given movie ID.

   - **Get Recommendations for a User**:
     - URL: `http://127.0.0.1:8000/recommendations/user/{user_id}`
     - Method: `GET`
     - Example: `http://127.0.0.1:8000/recommendations/user/1`
     - Response: A list of recommended movies for the given user ID.