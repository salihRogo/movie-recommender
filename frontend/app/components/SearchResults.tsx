import { Form } from '@remix-run/react';
import type { MovieSearchResult } from '~/types';

interface SearchResultsProps {
  searchResults: MovieSearchResult[];
  addMovie: (movie: MovieSearchResult) => void;
  hasSearched: boolean;
  sortOrder: 'year' | 'popularity';
  setSortOrder: (order: 'year' | 'popularity') => void;
}

export default function SearchResults({ 
  searchResults, 
  addMovie, 
  hasSearched,
  sortOrder, 
  setSortOrder 
}: SearchResultsProps) {
  return (
    <div className="lg:col-span-2 bg-white/70 backdrop-blur-sm rounded-2xl shadow-lg p-6 flex flex-col">
      <div className="flex justify-between items-center mb-5">
        <h2 className="text-2xl font-bold text-slate-800">Search Results</h2>
        {searchResults.length > 0 && (
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setSortOrder(sortOrder === 'year' ? 'popularity' : 'year')}
              className="text-sm font-semibold text-sky-600 hover:text-sky-800 transition-colors"
              title={`Currently sorting by ${sortOrder}. Click to change.`}
            >
              Sort by {sortOrder === 'year' ? 'Popularity' : 'Year'}
            </button>
            <Form method="post">
              <input type="hidden" name="intent" value="clear_search" />
              <button
                type="submit"
                className="text-sm font-semibold text-rose-500 hover:text-rose-700 transition-colors"
              >
                Clear results
              </button>
            </Form>
          </div>
        )}
      </div>
      <div className="flex-grow overflow-y-auto pr-2 max-h-[50vh] pretty-scrollbar">
        {searchResults.length > 0 ? (
          <div className="space-y-3">
            {searchResults.map(movie => (
              <div key={movie.imdb_id} className={`flex items-center justify-between bg-slate-50 rounded-lg p-3 shadow-sm ${movie.isExactMatch ? 'border-2 border-sky-500' : ''}`}>
                <div>
                  <p className="font-semibold text-slate-800">{movie.title} ({movie.year})</p>
                  <p className="text-sm text-slate-500">{movie.actors}</p>
                </div>
                <button
                  type="button"
                  onClick={() => addMovie(movie)}
                  className="bg-sky-600 text-white rounded-full w-8 h-8 flex items-center justify-center hover:bg-sky-700 transition-all duration-200 ease-in-out shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-sky-600 transform hover:scale-110 flex-shrink-0"
                  aria-label={`Add ${movie.title} to profile`}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        ) : hasSearched ? (
          <div className="text-center text-slate-500 flex-grow flex items-center justify-center">
            <p>No movies found for your search.</p>
          </div>
        ) : (
          <div className="text-center text-slate-500 flex-grow flex items-center justify-center">
            <p>Search results will appear here.</p>
          </div>
        )}
      </div>
    </div>
  );
}
