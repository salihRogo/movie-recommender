import { useState } from "react";
import type { ActionFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { useActionData, Form } from "@remix-run/react";
// eslint-disable-next-line import/no-unresolved
import SearchBar from "~/components/SearchBar";

// --- Types --- //
interface MovieSearchResult {
  imdb_id: string;
  title: string;
  year: string;
}

interface RecommendedMovie {
  imdb_id: string;
  title: string;
  year: string;
  poster_url?: string;
  genres?: string;
  plot?: string;
}

// Interface for the backend movie data format which may use different casing
interface BackendMovieData {
  imdbID?: string;
  imdb_id?: string;
  Title?: string;
  title?: string;
  Year?: string;
  year?: string;
  Poster?: string;
  poster_url?: string;
  Genre?: string;
  genres?: string;
  Plot?: string;
  plot?: string;
}

interface ActionData {
  searchResults?: MovieSearchResult[];
  recommendations?: RecommendedMovie[];
  error?: string;
  message?: string;
}

// --- Server-Side Action --- //
export const action = async ({ request }: ActionFunctionArgs) => {
  const formData = await request.formData();
  const intent = formData.get("intent");

  // Differentiate between searching for movies and getting recommendations
  if (intent === 'search') {
    const query = formData.get("query");
    if (!query || typeof query !== 'string') {
      return json<ActionData>({ error: "Invalid search query." }, { status: 400 });
    }

    try {
      const backendUrl = `/api/movies/search?title=${encodeURIComponent(query)}`;
      const response = await fetch(backendUrl);
      if (!response.ok) {
        return json<ActionData>({ error: "Failed to search for movies." }, { status: 500 });
      }
      const rawData = await response.json();
      console.log('Backend search response (raw):', rawData); // Log the raw response

      // The backend (FastAPI with Pydantic) should return data in the shape: { results: MovieSearchResult[] }
      // The MovieSearchResult model in backend/app/schemas.py uses aliases for imdbID, Title, Year.
      // So, rawData.results should already be an array of objects like { imdb_id: "...", title: "...", year: "..." }
      
      let processedSearchResults: MovieSearchResult[] = [];
      if (rawData.results && Array.isArray(rawData.results)) {
        processedSearchResults = rawData.results.map((movie: BackendMovieData) => ({
          // Ensure movie.imdbID, movie.Title, movie.Year are used from rawData
          // and mapped to the snake_case fields of MovieSearchResult
          imdb_id: movie.imdbID!,
          title: movie.Title!,
          year: movie.Year!
        }));
      } else {
        console.warn('Backend response did not contain a `results` array or results was not an array. Raw data:', rawData);
      }

      console.log('Processed search results to be returned by action:', processedSearchResults);
      return json<ActionData>({ searchResults: processedSearchResults });
    } catch (error) {
      console.error("Search action error:", error);
      return json<ActionData>({ error: "Could not connect to the backend." }, { status: 500 });
    }
  }

  if (intent === 'recommend') {
    const likedMovies = formData.getAll("likedMovies");
    if (!likedMovies || likedMovies.length === 0) {
      return json<ActionData>({ error: "No movies selected for recommendations." }, { status: 400 });
    }

    try {
      const backendUrl = `/api/recommendations/by_profile`;
      const response = await fetch(backendUrl, {
        method: "POST",
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ imdb_ids: likedMovies })
      });

      if (!response.ok) {
        return json<ActionData>({ error: "Failed to get recommendations." }, { status: 500 });
      }

      const rawData = await response.json();
      console.log('Backend recommendation response:', rawData);
      
      // Parse recommendations from response
      let recommendations: RecommendedMovie[] = [];
      let message = "Here are your recommended movies:";
      
      if (rawData.recommendations && Array.isArray(rawData.recommendations)) {
        // Standard format - backend returns array of objects in recommendations property
        recommendations = rawData.recommendations.map((movie: BackendMovieData) => ({

          imdb_id: movie.imdbID || movie.imdb_id,
          title: movie.Title || movie.title,
          year: movie.Year || movie.year,
          poster_url: movie.Poster || movie.poster_url,
          plot: movie.Plot || movie.plot,
          genres: movie.Genre || movie.genres
        }));
        
        if (rawData.message) {
          message = rawData.message;
        }
        
        console.log('Processed recommendations:', recommendations);
      } else if (Array.isArray(rawData)) {
        // Try to extract movies from complex format
        try {
          // Extract the message if present
          const messageIndex = rawData.indexOf('message');
          if (messageIndex !== -1 && messageIndex + 1 < rawData.length) {
            const potentialMessage = rawData[messageIndex + 1];
            if (typeof potentialMessage === 'string') {
              message = potentialMessage;
            }
          }
          
          // Parse the movie data
          const extractedMovies: RecommendedMovie[] = [];
          
          // Look for Title, imdbID, Year, Poster entries
          for (let i = 0; i < rawData.length; i++) {
            const item = rawData[i];
            if (item === 'Title' && i + 1 < rawData.length) {
              const title = rawData[i + 1];
              
              // Find the corresponding imdbID, Year, Poster for this title
              let imdbId = '';
              let year = '';
              let posterUrl = '';
              let plot = '';
              let genres = '';
              
              const imdbIdIndex = rawData.indexOf('imdbID', i);
              if (imdbIdIndex !== -1 && imdbIdIndex + 1 < rawData.length) {
                imdbId = rawData[imdbIdIndex + 1];
              }
              
              const yearIndex = rawData.indexOf('Year', i);
              if (yearIndex !== -1 && yearIndex + 1 < rawData.length) {
                year = rawData[yearIndex + 1];
              }
              
              const posterIndex = rawData.indexOf('Poster', i);
              if (posterIndex !== -1 && posterIndex + 1 < rawData.length) {
                posterUrl = rawData[posterIndex + 1];
              }
              
              const plotIndex = rawData.indexOf('Plot', i);
              if (plotIndex !== -1 && plotIndex + 1 < rawData.length) {
                plot = rawData[plotIndex + 1];
              }
              
              const genreIndex = rawData.indexOf('Genre', i);
              if (genreIndex !== -1 && genreIndex + 1 < rawData.length) {
                genres = rawData[genreIndex + 1];
              }
              
              // If we found a title and imdbID, add to results
              if (typeof title === 'string' && typeof imdbId === 'string' && imdbId) {
                extractedMovies.push({
                  imdb_id: imdbId,
                  title,
                  year,
                  poster_url: posterUrl,
                  plot,
                  genres
                });
                
                // Skip ahead to avoid re-processing the same movie
                i = Math.max(i, imdbIdIndex, yearIndex, posterIndex, plotIndex, genreIndex);
              }
            }
          }
          
          if (extractedMovies.length > 0) {
            recommendations = extractedMovies;
            console.log('Extracted recommendations:', recommendations);
          }
        } catch (parseError) {
          console.error('Error parsing recommendation data:', parseError);
        }
      }
      
      return json<ActionData>({ 
        message, 
        recommendations 
      });
    } catch (error) {
      console.error("Recommendation action error:", error);
      return json<ActionData>({ error: "Could not get recommendations." }, { status: 500 });
    }
  }

  return json<ActionData>({ error: "Invalid action." }, { status: 400 });
};


// --- Frontend Component --- //
export default function Index() {
  const actionData = useActionData<typeof action>();
  const [selectedMovies, setSelectedMovies] = useState<MovieSearchResult[]>([]);

  const addMovie = (movie: MovieSearchResult) => {
    if (!selectedMovies.some(m => m.imdb_id === movie.imdb_id)) {
      setSelectedMovies([...selectedMovies, movie]);
    }
  };

  const removeMovie = (imdb_id: string) => {
    setSelectedMovies(selectedMovies.filter(m => m.imdb_id !== imdb_id));
  };

  return (
    <main className="container mx-auto p-4 md:p-8 flex flex-col items-center gap-8">
      <div className="w-full text-center">
        <h1 className="text-3xl md:text-4xl font-bold text-gray-800">Movie Recommender</h1>
        <p className="text-gray-600 mt-2">Find movies you like to get personalized recommendations.</p>
      </div>
      
      <SearchBar />

      {actionData?.error && <p className="text-red-500 mt-4">{actionData.error}</p>}
      {actionData?.message && <p className="text-blue-500 mt-4">{actionData.message}</p>}

      {/* --- Main Content: Selected Movies and Search Results --- */}
      <div className="w-full grid grid-cols-1 md:grid-cols-3 gap-8">
        
        {/* --- Left Column: Selected Movies --- */}
        <div className="md:col-span-1">
          <h2 className="text-xl font-semibold mb-4">Your Liked Movies ({selectedMovies.length})</h2>
          {selectedMovies.length > 0 ? (
            <Form method="post" className="flex flex-col gap-4">
              <input type="hidden" name="intent" value="recommend" />
              {selectedMovies.map(movie => (
                <div key={movie.imdb_id} className="bg-white p-3 rounded-lg shadow flex justify-between items-center">
                  <input type="hidden" name="likedMovies" value={movie.imdb_id} />
                  <p className="text-blue-700 font-medium">{movie.title} ({movie.year})</p>
                  <button type="button" onClick={() => removeMovie(movie.imdb_id)} className="text-red-500 hover:text-red-700 font-bold">✕</button>
                </div>
              ))}
              <button type="submit" className="mt-4 w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:bg-gray-400">
                Get Recommendations
              </button>
            </Form>
          ) : (
            <p className="text-gray-500">Search for movies to add them to your list.</p>
          )}
        </div>

        {/* --- Right Column: Search Results --- */}
        <div className="md:col-span-2">
          <h2 className="text-xl font-semibold mb-4">Search Results</h2>
          
          
          <div className="flex flex-col gap-3">
            {actionData?.searchResults?.map(movie => (
              <div key={movie.imdb_id} className="bg-white p-3 rounded-lg shadow flex justify-between items-center">
                <p className="text-blue-700 font-medium">{movie.title} ({movie.year})</p>
                <button onClick={() => addMovie(movie)} className="bg-green-500 text-white py-1 px-3 rounded-full hover:bg-green-600">Add</button>
              </div>
            ))}
            {actionData?.searchResults?.length === 0 && <p className="text-gray-500">No movies found.</p>}
          </div>
        </div>
      </div>

      {/* --- Recommendations Section --- */}
      {actionData?.recommendations && actionData.recommendations.length > 0 && (
        <div className="mt-12 w-full">
          <h2 className="text-2xl font-semibold mb-6">{actionData.message || "Recommended Movies"}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-6">
            {actionData.recommendations.map(movie => (
              <div key={movie.imdb_id} className="bg-white rounded-lg shadow overflow-hidden flex flex-col h-full">
                {movie.poster_url && movie.poster_url !== 'N/A' ? (
                  <div className="h-64 overflow-hidden">
                    <img 
                      src={movie.poster_url} 
                      alt={`${movie.title} poster`} 
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.src = 'https://via.placeholder.com/300x450?text=No+Poster';
                      }} 
                    />
                  </div>
                ) : (
                  <div className="h-64 bg-gray-200 flex items-center justify-center">
                    <span className="text-gray-500">No poster available</span>
                  </div>
                )}
                <div className="p-4 flex-grow flex flex-col">
                  <h3 className="font-semibold text-blue-700 text-lg">{movie.title}</h3>
                  <p className="text-sm text-gray-600 mb-1">{movie.year}</p>
                  {movie.genres && <p className="text-xs text-gray-500 mb-2">{movie.genres}</p>}
                  {movie.plot && (
                    <p className="text-xs text-gray-700 mt-2 flex-grow line-clamp-3 overflow-hidden">
                      {movie.plot}
                    </p>
                  )}
                  <a 
                    href={`https://www.imdb.com/title/${movie.imdb_id}/`} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="mt-3 text-xs text-blue-600 hover:underline inline-block"
                  >
                    View on IMDb
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}
