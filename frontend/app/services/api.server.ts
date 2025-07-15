import type { MovieDetail, ProfileRecommendationResponse } from '~/types';

// Use the environment variable for the API base URL, with a sensible default for development.
const API_BASE_URL = process.env.REMIX_PUBLIC_API_BASE_URL || 'http://localhost:8000';

/**
 * Searches for movies by title by calling the backend API.
 * @param title The movie title to search for.
 * @returns A promise that resolves to an array of movie details.
 */
export async function searchMovies(title: string): Promise<MovieDetail[]> {
  if (!title) return [];

  const searchParams = new URLSearchParams({ movie_title: title });
  const url = `${API_BASE_URL}/search?${searchParams.toString()}`;

  try {
    const response = await fetch(url);
    if (!response.ok) {
      console.error(`API Error searching movies: ${response.status} ${response.statusText}`);
      return [];
    }
    return response.json();
  } catch (error) {
    console.error('Failed to fetch from /search endpoint', error);
    return [];
  }
}

/**
 * Gets movie recommendations based on a user's profile of liked movies.
 * @param imdbIds A list of IMDb IDs for the user's liked movies.
 * @returns A promise that resolves to the recommendation response from the backend.
 */
export async function getRecommendations(
  imdbIds: string[]
): Promise<ProfileRecommendationResponse> {
  const url = `${API_BASE_URL}/recommendations/by_profile`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ imdb_ids: imdbIds }),
    });

    if (!response.ok) {
      console.error(
        `API Error getting recommendations: ${response.status} ${response.statusText}`
      );
      return { recommendations: [], message: 'Failed to get recommendations.' };
    }
    return response.json();
  } catch (error) {
    console.error('Failed to fetch from /recommendations/by_profile endpoint', error);
    return { recommendations: [], message: 'An unexpected error occurred.' };
  }
}
