import { useState, useEffect } from "react";
import type { ActionFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { useActionData, Form } from "@remix-run/react";

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
      const backendUrl = `http://localhost:8000/movies/search?title=${encodeURIComponent(query)}`;
      const response = await fetch(backendUrl);
      if (!response.ok) {
        return json<ActionData>({ error: "Failed to search for movies." }, { status: 500 });
      }
      const rawData = await response.json();
      console.log('Backend search response (raw):', rawData); // Log the raw response

      let processedSearchResults: MovieSearchResult[] = [];
      if (rawData.results && Array.isArray(rawData.results)) {
        processedSearchResults = rawData.results.map((movie: BackendMovieData) => ({
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
      const backendUrl = `http://localhost:8000/recommendations/by_profile`;
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
      
      let recommendations: RecommendedMovie[] = [];
      if (rawData.recommendations && Array.isArray(rawData.recommendations)) {
        recommendations = rawData.recommendations.map((movie: BackendMovieData) => ({
          imdb_id: movie.imdb_id || movie.imdbID!,
          title: movie.title || movie.Title!,
          year: movie.year || movie.Year!,
          poster_url: movie.poster_url || movie.Poster,
          genres: movie.genres || movie.Genre,
          plot: movie.plot || movie.Plot
        }));
      }

      return json<ActionData>({ 
        recommendations,
        message: `Here are ${recommendations.length} recommendations based on your liked movies:`
      });

    } catch (error) {
      console.error("Recommendation action error:", error);
      return json<ActionData>({ error: "Could not connect to the backend for recommendations." }, { status: 500 });
    }
  }

  return json<ActionData>({ error: "Invalid intent." }, { status: 400 });
};


// --- Frontend Component --- //
export default function Index() {
  const actionData = useActionData<ActionData>();
  const [selectedMovies, setSelectedMovies] = useState<MovieSearchResult[]>([]);
  const [searchResults, setSearchResults] = useState<MovieSearchResult[]>([]);
  const [searchQuery, setSearchQuery] = useState("");

  // Effect to update local search results when actionData changes from the server
  useEffect(() => {
    if (actionData?.searchResults) {
      setSearchResults(actionData.searchResults);
    }
    // Clear search results on navigation or when the component unmounts without new results
    if (actionData?.recommendations) {
        setSearchResults([]);
        setSearchQuery("");
    }
  }, [actionData]);

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
        <Form method="post" className="flex gap-2 my-6 max-w-lg mx-auto">
          <input type="hidden" name="intent" value="search" />
          <input 
            type="text" 
            name="query" 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search for a movie..." 
            className="flex-grow p-2 border rounded-lg"
          />
          <button 
            type="submit" 
            className="bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700"
          >
            Search
          </button>
        </Form>
      </div>

      {actionData?.error && <p className="text-red-500 my-4">{actionData.error}</p>}

      <div className="w-full grid grid-cols-1 md:grid-cols-3 gap-8">
        
        {/* --- Left Column: Selected Movies --- */}
        <div className="md:col-span-1">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Your Liked Movies ({selectedMovies.length})</h2>
            {selectedMovies.length > 0 && (
              <button 
                onClick={() => setSelectedMovies([])} 
                className="text-sm text-blue-600 hover:underline"
              >
                Clear All
              </button>
            )}
          </div>
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
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Search Results</h2>
            {searchResults.length > 0 && (
              <button 
                onClick={() => { setSearchResults([]); setSearchQuery(""); }} 
                className="text-sm text-blue-600 hover:underline"
              >
                Clear Results
              </button>
            )}
          </div>
          
          <div className="flex flex-col gap-3">
            {searchResults.map(movie => (
              <div key={movie.imdb_id} className="bg-white p-3 rounded-lg shadow flex justify-between items-center">
                <p className="text-blue-700 font-medium">{movie.title} ({movie.year})</p>
                <button onClick={() => addMovie(movie)} className="bg-green-500 text-white py-1 px-3 rounded-full hover:bg-green-600">Add</button>
              </div>
            ))}
            {searchResults.length === 0 && actionData?.searchResults === undefined && <p className="text-gray-500">Search for movies to see results.</p>}
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
