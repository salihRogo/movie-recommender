import { json, type ActionFunctionArgs, type MetaFunction } from "@remix-run/node";
import { Form, useActionData, useNavigation } from "@remix-run/react";
import { useState, useMemo } from "react";

import type { MovieSearchResult, RecommendedMovie, BackendMovieData } from '~/types';
// eslint-disable-next-line import/no-unresolved
import SelectedMovies from '~/components/SelectedMovies';
// eslint-disable-next-line import/no-unresolved
import SearchResults from '~/components/SearchResults';
// eslint-disable-next-line import/no-unresolved
import RecommendationCard from '~/components/RecommendationCard';

// --- Remix Loader & Action --- //

export const meta: MetaFunction = () => {
  return [
    { title: "Movie Recommender" },
    { name: "description", content: "Get movie recommendations based on your favorites!" },
  ];
};

async function normalizeAndFilter(data: BackendMovieData[], query: string): Promise<MovieSearchResult[]> {
  if (!Array.isArray(data)) {
    console.error("Expected an array from backend, but got:", data);
    return [];
  }

  const lowerCaseQuery = query.toLowerCase();

  const mappedAndTagged = data.map(movie => ({
    imdb_id: movie.imdbID || movie.imdb_id || '',
    title: movie.Title || movie.title || 'Unknown Title',
    year: movie.Year || movie.year || 'Unknown Year',
    actors: movie.Actors || movie.actors || 'N/A',
    isExactMatch: (movie.Title || movie.title || '').toLowerCase() === lowerCaseQuery,
    imdbVotes: movie.imdbVotes || '0',
  })).filter(movie => movie.imdb_id);

  // Return the mapped data without sorting; sorting will be handled on the client.
  return mappedAndTagged;
}

async function normalizeRecommendations(data: BackendMovieData[]): Promise<RecommendedMovie[]> {
  if (!Array.isArray(data)) {
    console.error("Expected an array for recommendations, but got:", data);
    return [];
  }
  return data.map(movie => ({
    imdb_id: movie.imdb_id || movie.imdbID || '',
    title: movie.title || movie.Title || 'Unknown Title',
    year: movie.year || movie.Year || 'Unknown Year',
    poster_url: movie.poster_url || movie.Poster,
    genres: movie.genres || movie.Genre,
    plot: movie.plot || movie.Plot,
    actors: movie.Actors || movie.actors,
    imdbRating: movie.imdbRating,
  })).filter(movie => movie.imdb_id);
}

export const action = async ({ request }: ActionFunctionArgs) => {
  const formData = await request.formData();
  const intent = formData.get("intent");
  const API_URL = process.env.API_URL || 'http://127.0.0.1:8000';

  if (intent === "search") {
    const query = formData.get("search_query") as string;
    if (!query) {
      return json({ searchResults: [], error: "Search query cannot be empty." }, { status: 400 });
    }
    try {
      const response = await fetch(`${API_URL}/search?movie_title=${encodeURIComponent(query)}`);
      if (!response.ok) {
        const errorBody = await response.text();
        console.error(`API Error ${response.status}:`, errorBody);
        return json({ searchResults: [], error: `Failed to fetch from API: ${response.statusText}` }, { status: response.status });
      }
      const data: BackendMovieData[] = await response.json();
      const searchResults = await normalizeAndFilter(data, query);
      return json({ searchResults });
    } catch (error) {
      console.error("Network or parsing error:", error);
      return json({ searchResults: [], error: "An error occurred while searching." }, { status: 500 });
    }
  }

  if (intent === "clear_search") {
    return json({ searchResults: [], cleared: true });
  }

  if (intent === "recommend") {
    const selectedMoviesJSON = formData.get("selected_movies") as string;
    if (!selectedMoviesJSON) {
        return json({ recommendations: [], message: "Please select at least one movie." }, { status: 400 });
    }

    try {
      const likedMovies: string[] = JSON.parse(selectedMoviesJSON);
      if (!Array.isArray(likedMovies) || likedMovies.length === 0) {
        return json({ recommendations: [], message: "Please select at least one movie." }, { status: 400 });
      }

      const response = await fetch(`${API_URL}/recommendations/by_profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ imdb_ids: likedMovies }),
      });
      if (!response.ok) {
        const errorBody = await response.text();
        console.error(`API Error ${response.status}:`, errorBody);
        return json({ recommendations: [], error: `Failed to get recommendations: ${response.statusText}` }, { status: response.status });
      }
      const responseData = await response.json();
      const recommendations = await normalizeRecommendations(responseData.recommendations);
      return json({ 
        recommendations
      });
    } catch (error) {
      console.error("Network or parsing error during recommendation:", error);
      return json({ recommendations: [], error: "An error occurred while getting recommendations." }, { status: 500 });
    }
  }

  return json({ error: "Invalid intent" }, { status: 400 });
};

// --- React Component --- //

export default function Index() {
  const actionData = useActionData<typeof action>();
  const navigation = useNavigation();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMovies, setSelectedMovies] = useState<MovieSearchResult[]>([]);
  const [sortOrder, setSortOrder] = useState<'year' | 'popularity'>('popularity');

  const isSearching = navigation.state === 'submitting' && navigation.formData?.get('intent') === 'search';

  const searchResults = useMemo(() => 
    (actionData && 'searchResults' in actionData && Array.isArray(actionData.searchResults)) 
      ? actionData.searchResults 
      : [],
    [actionData]
  );
  
  const recommendations = useMemo(() => 
    (actionData && 'recommendations' in actionData && Array.isArray(actionData.recommendations)) 
      ? actionData.recommendations 
      : [],
    [actionData]
  );

  const hasSearched = useMemo(() => {
    if (!actionData) return false;
    // Don't show 'No results' after explicitly clearing.
    if ('cleared' in actionData && actionData.cleared) return false;
    return 'searchResults' in actionData || 'error' in actionData;
  }, [actionData]);



  const sortedSearchResults = useMemo(() => {
    return [...searchResults].sort((a, b) => {
      // Prioritize exact matches
      if (a.isExactMatch !== b.isExactMatch) {
        return a.isExactMatch ? -1 : 1;
      }

      // Fallback to user-selected sort order
      if (sortOrder === 'year') {
        return (b.year || '0').localeCompare(a.year || '0');
      } 
      
      // Popularity sort
      const votesA = parseInt((a.imdbVotes || '0').replace(/,/g, ''), 10);
      const votesB = parseInt((b.imdbVotes || '0').replace(/,/g, ''), 10);
      return votesB - votesA;
    });
  }, [searchResults, sortOrder]);

  const addMovie = (movie: MovieSearchResult) => {
    if (!selectedMovies.some(m => m.imdb_id === movie.imdb_id)) {
      setSelectedMovies(prev => [...prev, movie]);
    }
  };

  const removeMovie = (imdb_id: string) => {
    setSelectedMovies(prev => prev.filter(m => m.imdb_id !== imdb_id));
  };

  const clearSelectedMovies = () => {
    setSelectedMovies([]);
  };

  return (
    <div className="min-h-screen bg-slate-100 font-sans text-slate-800 p-4 sm:p-6 lg:p-8">
      <header className="text-center mb-12">
        <h1 className="text-5xl font-extrabold text-slate-900 tracking-tight">Movie Recommender</h1>
        <p className="text-lg text-slate-500 mt-3">Discover your next favorite film.</p>
      </header>

      {/* --- Search Form --- */}
      <Form method="post" className="max-w-xl mx-auto mb-12">
        <input type="hidden" name="intent" value="search" />
        <div className="flex items-center bg-white rounded-full shadow-lg p-2">
          <input
            type="text"
            name="search_query"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search for a movie to add to your profile..."
            className="w-full bg-transparent p-3 text-slate-700 placeholder-slate-400 focus:outline-none"
          />
          <button 
            type="submit"
            disabled={isSearching || !searchQuery.trim()}
            className="bg-sky-600 text-white font-bold p-3 rounded-full hover:bg-sky-700 transition-colors disabled:bg-sky-300 disabled:cursor-not-allowed flex items-center justify-center"
            aria-label="Search"
          >
            {isSearching ? (
              <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            )}
          </button>
        </div>
        {actionData && 'error' in actionData && actionData.error && <p className="text-red-500 text-sm mt-3 text-center font-medium">{actionData.error}</p>}
      </Form>

      {/* --- Main Content Grid --- */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
        <div className="lg:col-span-1">
          <SelectedMovies 
            selectedMovies={selectedMovies} 
            removeMovie={removeMovie} 
            clearSelection={clearSelectedMovies}
          />
        </div>
        <div className="lg:col-span-2">
          <SearchResults 
            searchResults={sortedSearchResults} 
            addMovie={addMovie} 
            hasSearched={hasSearched}
            sortOrder={sortOrder}
            setSortOrder={setSortOrder}
          />
        </div>
      </div>



      {/* --- Recommendations Display --- */}
      {recommendations.length > 0 && (
        <div className="mt-12">
          <h2 className="text-3xl font-bold text-slate-800 mb-6 text-center">Your Recommendations</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-8">
            {recommendations.map((movie) => (
              <RecommendationCard key={movie.imdb_id} movie={movie} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
