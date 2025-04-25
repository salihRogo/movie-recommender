import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors
import os

class MovieRecommender:
    def __init__(self):
        self.ratings = None
        self.movies = None
        self.X = None
        self.user_mapper = None
        self.movie_mapper = None
        self.user_inv_mapper = None
        self.movie_inv_mapper = None
        self.movie_titles = None
        
    def load_data(self, ratings_path, movies_path):
        """Load movie and ratings data from CSV files"""
        self.ratings = pd.read_csv(ratings_path)
        self.movies = pd.read_csv(movies_path)
        self.movie_titles = dict(zip(self.movies['movieId'], self.movies['title']))
        print(f"Loaded {len(self.ratings)} ratings and {len(self.movies)} movies")
        
    def create_matrix(self):
        """Create user-item matrix using scipy csr matrix"""
        N = len(self.ratings['userId'].unique())
        M = len(self.ratings['movieId'].unique())

        # Map Ids to indices
        self.user_mapper = dict(zip(np.unique(self.ratings["userId"]), list(range(N))))
        self.movie_mapper = dict(zip(np.unique(self.ratings["movieId"]), list(range(M))))

        # Map indices to IDs
        self.user_inv_mapper = dict(zip(list(range(N)), np.unique(self.ratings["userId"])))
        self.movie_inv_mapper = dict(zip(list(range(M)), np.unique(self.ratings["movieId"])))

        user_index = [self.user_mapper[i] for i in self.ratings['userId']]
        movie_index = [self.movie_mapper[i] for i in self.ratings['movieId']]

        self.X = csr_matrix((self.ratings["rating"], (movie_index, user_index)), shape=(M, N))
        print("Matrix created successfully")
        
    def find_similar_movies(self, movie_id, k=10, metric='cosine'):
        """Find similar movies using KNN"""
        neighbour_ids = []

        if movie_id not in self.movie_mapper:
            print(f"Movie ID {movie_id} not found!")
            return []

        movie_ind = self.movie_mapper[movie_id]
        movie_vec = self.X[movie_ind]
        k += 1  # Including the movie itself in the result
        kNN = NearestNeighbors(n_neighbors=k, algorithm="brute", metric=metric)
        kNN.fit(self.X)
        movie_vec = movie_vec.reshape(1, -1)
        neighbour = kNN.kneighbors(movie_vec, return_distance=False)
        
        for i in range(0, k):
            n = neighbour[0][i]
            neighbour_ids.append(self.movie_inv_mapper[n])

        neighbour_ids.pop(0)  # Remove the movie itself from the list
        return neighbour_ids
    
    def get_recommendations(self, movie_id, k=10):
        """Get movie recommendations based on a movie ID"""
        if not isinstance(movie_id, int):
            try:
                movie_id = int(movie_id)
            except:
                return []
        
        if movie_id not in self.movie_titles:
            return []
            
        similar_ids = self.find_similar_movies(movie_id, k)
        recommendations = []
        
        for movie_id in similar_ids:
            if movie_id in self.movie_titles:
                movie = {
                    "id": int(movie_id),
                    "title": self.movie_titles[movie_id]
                }
                if movie_id in self.movies.movieId.values:
                    movie_row = self.movies[self.movies.movieId == movie_id].iloc[0]
                    if 'genres' in movie_row:
                        movie["genres"] = movie_row.genres
                recommendations.append(movie)
                
        return recommendations
    
    def get_movie_by_title(self, title):
        """Find a movie by title (partial match)"""
        matches = self.movies[self.movies['title'].str.contains(title, case=False)]
        return matches.to_dict('records')
    
    def recommend_movies_for_user(self, user_id, k=10):
        """Recommend movies for a specific user"""
        df1 = self.ratings[self.ratings['userId'] == user_id]
        
        if df1.empty:
            return []
            
        # Find the movie with the highest rating for the user
        movie_id = df1[df1['rating'] == max(df1['rating'])]['movieId'].iloc[0]
        
        # Find similar movies using the movie ID
        return self.get_recommendations(movie_id, k)
    
    def get_popular_movies(self, n=10):
        """Get the most popular movies based on number of ratings"""
        movie_stats = self.ratings.groupby('movieId').agg(
            count=('rating', 'count'),
            mean=('rating', 'mean')
        ).reset_index()
        
        # Filter movies with at least 50 ratings
        popular = movie_stats[movie_stats['count'] > 50].sort_values('mean', ascending=False).head(n)
        
        recommendations = []
        for _, row in popular.iterrows():
            movie_id = row['movieId']
            if movie_id in self.movie_titles:
                movie = {
                    "id": int(movie_id),
                    "title": self.movie_titles[movie_id],
                    "rating": round(row['mean'], 1),
                    "count": int(row['count'])
                }
                if movie_id in self.movies.movieId.values:
                    movie_row = self.movies[self.movies.movieId == movie_id].iloc[0]
                    if 'genres' in movie_row:
                        movie["genres"] = movie_row.genres
                recommendations.append(movie)
                
        return recommendations
    
    def initialize(self, ratings_path, movies_path):
        """Initialize the recommender system"""
        self.load_data(ratings_path, movies_path)
        self.create_matrix()
        return True

# Example usage:
if __name__ == "__main__":
    recommender = MovieRecommender()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, "data")
    
    recommender.initialize(
        os.path.join(data_dir, "ratings.csv"),
        os.path.join(data_dir, "movies.csv")
    )
    
    # Test with movie ID 1 (Toy Story)
    # recommendations = recommender.get_recommendations(16, k=5)
    # print("Recommendations for Casino:")
    # for movie in recommendations:
    #     print(f" - {movie['title']}")

    # Test recommend_movies_for_user method for all users from id=1 to id=1000
    for user_id in range(1, 1001):  # Loop through user IDs from 1 to 1000
        user_recommendations = recommender.recommend_movies_for_user(user_id, k=5)
        if user_recommendations:  # Only print if recommendations exist
            print(f"\nRecommendations for User {user_id}:")
            for movie in user_recommendations:
                print(f" - {movie['title']}")
        else:
            print(f"\nNo recommendations found for User {user_id}")