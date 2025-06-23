import { Form } from '@remix-run/react';
import type { MovieSearchResult } from '~/types';

interface SelectedMoviesProps {
  selectedMovies: MovieSearchResult[];
  removeMovie: (imdb_id: string) => void;
  clearSelection: () => void;
}

export default function SelectedMovies({ selectedMovies, removeMovie, clearSelection }: SelectedMoviesProps) {
  return (
    <div className="lg:col-span-1 bg-white/70 backdrop-blur-sm rounded-2xl shadow-lg p-6 flex flex-col">
      <div className="flex justify-between items-center mb-5">
        <h2 className="text-2xl font-bold text-slate-800">Your Profile</h2>
        {selectedMovies.length > 0 && (
          <button
            type="button"
            onClick={clearSelection}
            className="text-sm font-semibold text-rose-500 hover:text-rose-700 transition-colors"
          >
            Clear selection
          </button>
        )}
      </div>
      <div className="flex-grow flex flex-col">
        {selectedMovies.length > 0 ? (
          <Form method="post" className="flex flex-col h-full">
            <input type="hidden" name="intent" value="recommend" />
            <div className="space-y-3 pr-2 flex-grow overflow-y-auto pretty-scrollbar">
              {selectedMovies.map(movie => (
                <div key={movie.imdb_id} className="flex items-center justify-between bg-slate-50 rounded-lg p-3 shadow-sm">
                  <span className="font-semibold text-slate-700 truncate pr-2">{movie.title} ({movie.year})</span>
                  <button
                    type="button"
                    onClick={() => removeMovie(movie.imdb_id)}
                    className="bg-rose-500 text-white rounded-full w-8 h-8 flex items-center justify-center hover:bg-rose-600 transition-all duration-200 ease-in-out shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-rose-500 transform hover:scale-110 flex-shrink-0"
                    aria-label={`Remove ${movie.title} from profile`}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M18 12H6" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
            <input type="hidden" name="selected_movies" value={JSON.stringify(selectedMovies.map(m => m.imdb_id))} />
            <button 
              type="submit" 
              className="w-full mt-4 bg-sky-600 text-white font-bold py-3 px-4 rounded-lg hover:bg-sky-700 transition-colors shadow-md disabled:bg-sky-300"
              disabled={selectedMovies.length === 0}
            >
              Get Recommendations
            </button>
          </Form>
        ) : (
          <div className="text-center text-slate-500 flex-grow flex items-center justify-center">
            <p>Your selected movies will appear here.</p>
          </div>
        )}
      </div>
    </div>
  );
}
