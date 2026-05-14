export interface CityInfo {
  name: string;
  lng: number;
  lat: number;
}

export const CITIES: CityInfo[] = [
  { name: "大理", lng: 100.226, lat: 25.591 },
  { name: "杭州", lng: 120.155, lat: 30.274 },
  { name: "成都", lng: 104.066, lat: 30.573 },
  { name: "三亚", lng: 109.508, lat: 18.248 },
  { name: "西安", lng: 108.940, lat: 34.260 },
  { name: "厦门", lng: 118.089, lat: 24.480 },
  { name: "丽江", lng: 100.230, lat: 26.872 },
  { name: "重庆", lng: 106.551, lat: 29.563 },
  { name: "拉萨", lng: 91.172, lat: 29.650 },
  { name: "桂林", lng: 110.290, lat: 25.274 },
  { name: "青岛", lng: 120.382, lat: 36.067 },
  { name: "苏州", lng: 120.585, lat: 31.299 },
];

export function getCityCoords(cityName: string): [number, number] | null {
  const city = CITIES.find((c) => c.name === cityName);
  return city ? [city.lng, city.lat] : null;
}
