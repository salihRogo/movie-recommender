import { json, type ActionFunctionArgs, type MetaFunction } from "@remix-run/node";
import { Form, useActionData, useNavigation } from "@remix-run/react";
import { useState, useMemo } from "react";

import type { MovieSearchResult, MovieDetail, SortOrder } from '~/types';
// eslint-disable-next-line import/no-unresolved
import SelectedMovies from '~/components/SelectedMovies';
// eslint-disable-next-line import/no-unresolved
import SearchResults from '~/components/SearchResults';
// eslint-disable-next-line import/no-unresolved
import RecommendationCard from '~/components/RecommendationCard';
// eslint-disable-next-line import/no-unresolved
import { searchMovies, getRecommendations } from '~/services/api.server';

// --- Remix Loader & Action --- //

export const meta: MetaFunction = () => {
  return [
    { title: "Movie Recommender" },
    { name: "description", content: "Get movie recommendations based on your favorites!" },
  ];
};



export const action = async ({ request }: ActionFunctionArgs) => {
  const formData = await request.formData();
  const intent = formData.get('intent');

  switch (intent) {
    case 'search': {
      const query = formData.get('search_query') as string;
      if (!query) {
        return json({ searchResults: [], error: 'Search query cannot be empty.' }, { status: 400 });
      }
      const searchResults = await searchMovies(query);
      return json({ searchResults });
    }

    case 'clear_search': {
      return json({ searchResults: [], cleared: true });
    }

    case 'recommend': {
      const selectedMoviesJSON = formData.get('selected_movies') as string;
      if (!selectedMoviesJSON) {
        return json({ recommendations: [], message: 'Please select at least one movie.' }, { status: 400 });
      }
      try {
        const likedMovieIds: string[] = JSON.parse(selectedMoviesJSON);
        if (!Array.isArray(likedMovieIds) || likedMovieIds.length === 0) {
          return json({ recommendations: [], message: 'Invalid selection.' }, { status: 400 });
        }
        const result = await getRecommendations(likedMovieIds);
        return json(result);
      } catch (error) {
        console.error('Error parsing selected movies JSON:', error);
        return json({ recommendations: [], message: 'An error occurred.' }, { status: 500 });
      }
    }

    default: {
      return json({ error: 'Invalid intent' }, { status: 400 });
    }
  }
};

// --- React Component --- //

export default function Index() {
  const actionData = useActionData<typeof action>();
  const navigation = useNavigation();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMovies, setSelectedMovies] = useState<MovieSearchResult[]>([]);
  const [sortOrder, setSortOrder] = useState<SortOrder>('popularity');

  const isSearching = navigation.state === 'submitting' && navigation.formData?.get('intent') === 'search';

  const searchResults = useMemo(() => 
    (actionData && 'searchResults' in actionData && Array.isArray(actionData.searchResults)) 
      ? actionData.searchResults 
      : [],
    [actionData]
  );
  
  const recommendations: MovieDetail[] = (actionData && 'recommendations' in actionData && actionData.recommendations as MovieDetail[]) || [];

  const hasSearched = useMemo(() => {
    if (!actionData) return false;
    // Don't show 'No results' after explicitly clearing.
    if ('cleared' in actionData && actionData.cleared) return false;
    return 'searchResults' in actionData || 'error' in actionData;
  }, [actionData]);

  const sortedSearchResults: MovieSearchResult[] = useMemo(() => {
    if (!searchResults) return [];

    const lowerCaseQuery = searchQuery.toLowerCase();

    const processedResults: MovieSearchResult[] = searchResults.map(movie => ({
      ...movie,
      actors: movie.actors || 'N/A',
      isExactMatch: movie.title.toLowerCase() === lowerCaseQuery,
      // The backend needs to provide imdbVotes for this to work
      imdbVotes: movie.imdbVotes || '0',
    }));

    return processedResults.sort((a, b) => {
      // Prioritize exact matches
      if (a.isExactMatch && !b.isExactMatch) return -1;
      if (!a.isExactMatch && b.isExactMatch) return 1;

      // Then sort by the chosen order
      if (sortOrder === 'year') {
        return b.year.localeCompare(a.year);
      }

      // Default to popularity sort
      const votesA = parseInt((a.imdbVotes || '0').replace(/,/g, ''), 10);
      const votesB = parseInt((b.imdbVotes || '0').replace(/,/g, ''), 10);
      return votesB - votesA;
    });
  }, [searchResults, sortOrder, searchQuery]);

  

  const addMovie = (movie: MovieSearchResult) => {
    // Ensure we don't add duplicates
    if (!selectedMovies.some(m => m.imdb_id === movie.imdb_id)) {
      // The `movie` object is already a `MovieSearchResult`, so it can be added directly.
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
            {recommendations.map((movie: MovieDetail) => (
              <RecommendationCard key={movie.imdb_id} movie={movie} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
