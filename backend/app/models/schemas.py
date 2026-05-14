from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Location(BaseModel):
    lng: float
    lat: float


class WeatherInfo(BaseModel):
    date: date
    condition: str
    temp_high: float
    temp_low: float
    wind: str = ""


class SpotItem(BaseModel):
    name: str
    address: str = ""
    location: Optional[Location] = None
    visit_duration: str = "1小时"
    description: str = ""
    image_url: Optional[str] = None
    poi_id: Optional[str] = None


class MealItem(BaseModel):
    type: Literal["breakfast", "lunch", "dinner"]
    name: str
    description: str = ""


class HotelItem(BaseModel):
    name: str
    location: str = ""
    estimated_price: float = 0


class RouteEstimate(BaseModel):
    distance_km: float
    duration_min: int


class DayPlan(BaseModel):
    day_index: int
    date: date
    weather: Optional[WeatherInfo] = None
    spots: List[SpotItem] = []
    meals: List[MealItem] = []
    hotel: Optional[HotelItem] = None
    route_estimate: Optional[RouteEstimate] = None


class Budget(BaseModel):
    total: float = 0
    transportation: float = 0
    accommodation: float = 0
    meals: float = 0
    tickets: float = 0
    other: float = 0


class Itinerary(BaseModel):
    destination: str
    start_date: date
    end_date: date
    days: List[DayPlan] = []
    budget: Budget = Budget()


class TripRequest(BaseModel):
    destination: str = Field(..., min_length=1)
    start_date: date
    end_date: date
    budget_level: Literal["economy", "comfort", "luxury"] = "comfort"
    travelers: int = Field(default=1, ge=1, le=20)
    preferences: List[str] = Field(default_factory=list)
    extra_requirements: Optional[str] = None


class EditRequest(BaseModel):
    trip_id: str
    day_index: int = Field(ge=0)
    edit_instruction: str = Field(..., min_length=1)


class SaveRequest(BaseModel):
    name: str
    destination: str
    start_date: date
    end_date: date
    itinerary: dict


class GenerateResponse(BaseModel):
    itinerary: Itinerary
    raw: Optional[str] = None
