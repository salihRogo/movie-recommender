// --- Types --- //
export interface MovieSearchResult {
  imdb_id: string;
  title: string;
  year: string;
  actors: string;
  isExactMatch?: boolean;
  imdbVotes?: string;
}

export interface RecommendedMovie {
  imdb_id: string;
  title: string;
  year: string;
  poster_url?: string;
  genres?: string;
  plot?: string;
  actors?: string;
  imdbRating?: string;
}

// Interface for the backend movie data format which may use different casing
export interface BackendMovieData {
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
  Actors?: string;
  actors?: string;
  imdbVotes?: string;
  imdbRating?: string;
}

export interface ActionData {
  searchResults?: MovieSearchResult[];
  recommendations?: RecommendedMovie[];
  error?: string;
  message?: string;
}
