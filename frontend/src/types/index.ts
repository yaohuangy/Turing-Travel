export interface Location {
  lng: number;
  lat: number;
}

export interface WeatherInfo {
  date: string;
  condition: string;
  temp_high: number;
  temp_low: number;
  wind: string;
}

export interface SpotItem {
  name: string;
  address: string;
  location: Location | null;
  visit_duration: string;
  description: string;
  image_url: string | null;
  poi_id: string | null;
}

export interface MealItem {
  type: "breakfast" | "lunch" | "dinner";
  name: string;
  description: string;
}

export interface HotelItem {
  name: string;
  location: string;
  estimated_price: number;
}

export interface RouteEstimate {
  distance_km: number;
  duration_min: number;
}

export interface DayPlan {
  day_index: number;
  date: string;
  weather: WeatherInfo | null;
  spots: SpotItem[];
  meals: MealItem[];
  hotel: HotelItem | null;
  route_estimate: RouteEstimate | null;
}

export interface Budget {
  total: number;
  transportation: number;
  accommodation: number;
  meals: number;
  tickets: number;
  other: number;
}

export interface Itinerary {
  destination: string;
  start_date: string;
  end_date: string;
  days: DayPlan[];
  budget: Budget;
}

export interface TripRequest {
  destination: string;
  start_date: string;
  end_date: string;
  budget_level: "economy" | "comfort" | "luxury";
  travelers: number;
  preferences: string[];
  extra_requirements: string | null;
}

export interface GenerateResponse {
  itinerary: Itinerary;
  raw: string | null;
}

export interface SaveRequest {
  name: string;
  destination: string;
  start_date: string;
  end_date: string;
  itinerary: Itinerary;
}

export interface TripSummary {
  trip_id: string;
  name: string;
  destination: string;
  start_date: string;
  end_date: string;
  total_budget: number;
  saved_at: string;
}
