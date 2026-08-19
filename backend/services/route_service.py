import requests


class RouteService:

    BASE_URL = "https://router.project-osrm.org/route/v1/driving"

    def get_route(self, start_lat, start_lon, end_lat, end_lon):

        url = (
            f"{self.BASE_URL}/"
            f"{start_lon},{start_lat};"
            f"{end_lon},{end_lat}"
        )

        try:

            response = requests.get(
                url,
                params={"overview": "false"},
                timeout=10,
                verify=True
            )

            response.raise_for_status()

            data = response.json()

            if not data.get("routes"):
                return None

            route = data["routes"][0]

            return {
                "distance_km": round(route["distance"] / 1000, 2),
                "duration_min": round(route["duration"] / 60)
            }

        except requests.exceptions.RequestException as e:

            print("OSRM Route Error:", e)

            return {
                "distance_km": "N/A",
                "duration_min": "N/A"
            }


route_service = RouteService()


def calculate_route(start_lat, start_lon, end_lat, end_lon):

    return route_service.get_route(
        start_lat,
        start_lon,
        end_lat,
        end_lon
    )