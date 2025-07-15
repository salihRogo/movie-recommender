// --- Types --- //
export interface MovieSearchResult {
  imdb_id: string;
  title: string;
  year: string;
  actors: string;
  isExactMatch?: boolean;
  imdbVotes?: string;
}

export interface MovieDetail {
  imdb_id: string;
  title: string;
  year: string;
  poster_url?: string | null;
  genres?: string | null;
  plot?: string | null;
  actors?: string | null;
  imdbRating?: string | null;
  imdbVotes?: string | null;
}

export interface ProfileRecommendationResponse {
  recommendations: MovieDetail[];
  message: string;
}

export interface ActionData {
  searchResults?: MovieSearchResult[];
  recommendations?: MovieDetail[];
  error?: string;
  message?: string;
}

export type SortOrder = 'popularity' | 'year';
