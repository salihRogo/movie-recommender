import type { ActionData } from '~/types';

interface RecommendationsProps {
  actionData: ActionData | undefined;
}

export default function Recommendations({ actionData }: RecommendationsProps) {
  if (!actionData?.recommendations || actionData.recommendations.length === 0) {
    return null;
  }

  return (
    <div className="mt-16 w-full col-span-full">
      <h2 className="text-3xl font-bold text-center mb-8 text-slate-800">Top Picks For You</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-8">
        {actionData.recommendations.map(movie => (
          <div key={movie.imdb_id} className="bg-white rounded-2xl shadow-lg overflow-hidden flex flex-col h-full group transition-all duration-300 ease-in-out transform hover:-translate-y-2 hover:shadow-2xl">
            <div className="relative h-72 overflow-hidden">
              <img
                src={movie.poster_url && movie.poster_url !== 'N/A' ? movie.poster_url : 'https://via.placeholder.com/400x600?text=No+Poster'}
                alt={`${movie.title} poster`}
                className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500 ease-in-out"
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.src = 'https://via.placeholder.com/400x600?text=No+Poster';
                }}
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent"></div>
              <a
                href={`https://www.imdb.com/title/${movie.imdb_id}/`}
                target="_blank"
                rel="noopener noreferrer"
                className="absolute top-3 right-3 h-8 w-8 bg-amber-400 rounded-full flex items-center justify-center text-black font-bold text-xs opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                title="View on IMDb"
              >
                IMDb
              </a>
            </div>
            <div className="p-4 flex-grow flex flex-col">
              <h3 className="font-bold text-slate-800 text-lg leading-tight truncate">{movie.title}</h3>
              <p className="text-sm text-slate-500 mb-2">{movie.year}</p>
              {movie.imdbRating && movie.imdbRating !== 'N/A' && (
                <div className="flex items-center mb-2">
                  <svg className="w-4 h-4 text-amber-400 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  <span className="text-sm font-bold text-slate-700">{movie.imdbRating}</span>
                </div>
              )}
              {movie.genres && <p className="text-xs text-slate-600 mb-1 font-medium truncate"><span className="font-bold">Genres:</span> {movie.genres.split(',').join(' • ')}</p>}
              {movie.actors && <p className="text-xs text-slate-600 mb-3 font-medium truncate"><span className="font-bold">Actors:</span> {movie.actors}</p>}
              {movie.plot && (
                <p className="text-sm text-slate-700 flex-grow line-clamp-4 mt-2">
                  {movie.plot}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
