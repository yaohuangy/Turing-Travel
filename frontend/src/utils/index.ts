import type { SpotItem } from "../types";

export function spotHasCoords(spot: SpotItem): boolean {
  return !!(
    spot.location &&
    typeof spot.location.lng === "number" &&
    typeof spot.location.lat === "number" &&
    !(spot.location.lng === 0 && spot.location.lat === 0)
  );
}
