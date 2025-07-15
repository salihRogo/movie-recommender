import type { MovieDetail } from '~/types'; 

interface RecommendationCardProps {
  movie: MovieDetail;
}

const formatGenres = (genres: string | undefined) => {
  if (!genres) return null;
  return genres.split(',').map(g => g.trim()).join(' • ');
};

export default function RecommendationCard({ movie }: RecommendationCardProps) {
  return (
    <div className="bg-white rounded-lg shadow-lg overflow-hidden flex flex-col group transition-all duration-300">
      {/* Poster */}
      <div className="bg-slate-200">
        {movie.poster_url ? (
          <img 
            src={movie.poster_url} 
            alt={`Poster for ${movie.title}`} 
            className="w-full object-cover aspect-[2/3]" // Use aspect ratio to control size
          />
        ) : (
          <div className="w-full aspect-[2/3] flex items-center justify-center">
            <span className="text-slate-500">No Poster</span>
          </div>
        )}
      </div>
      
      {/* Details */}
      <div className="p-4 flex flex-col flex-grow">
        <h3 className="text-lg font-bold text-slate-900 truncate" title={movie.title}>{movie.title} ({movie.year})</h3>
        
        {movie.genres && (
          <p className="text-xs text-sky-800 mt-2 font-semibold tracking-wide uppercase">
            {formatGenres(movie.genres)}
          </p>
        )}

        {movie.actors && (
          <p className="text-sm text-slate-600 mt-2">
            <span className="font-semibold text-slate-800">Starring:</span> {movie.actors}
          </p>
        )}

        {movie.plot && (
          <p className="text-sm text-slate-500 mt-3 flex-grow">{movie.plot}</p>
        )}
        
        {movie.imdbRating && (
          <div className="mt-4 pt-3 border-t border-slate-200 flex justify-between items-center">
            <a 
              href={`https://www.imdb.com/title/${movie.imdb_id}/`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-semibold text-sky-600 hover:text-sky-800 transition-colors py-1 rounded-md"
            >
              Visit on IMDb
            </a>
            <p className="text-base font-bold text-slate-800">
              <span className="text-yellow-500 mr-1">★</span> {movie.imdbRating}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
