const map = L.map("map").setView([-0.0236, 37.9062], 6); // Default center (Kenya)

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "© OpenStreetMap contributors",
}).addTo(map);

// Simulated facility locations (You will replace with backend API later)
const facilities = [
  { name: "Kisumu MH Center", lat: -0.1022, lon: 34.7617, county: "Kisumu" },
  {
    name: "Eldoret MH Clinic",
    lat: 0.5167,
    lon: 35.2833,
    county: "Uasin Gishu",
  },
  {
    name: "Kericho Mental Wellness",
    lat: -0.3676,
    lon: 35.2831,
    county: "Kericho",
  },
];

// Ask for user location
if (navigator.geolocation) {
  navigator.geolocation.getCurrentPosition(
    (position) => {
      const userLat = position.coords.latitude;
      const userLon = position.coords.longitude;

      map.setView([userLat, userLon], 10);
      L.marker([userLat, userLon])
        .addTo(map)
        .bindPopup("You are here")
        .openPopup();

      showNearbyFacilities(userLat, userLon);
    },
    () => {
      showAllFacilities(); // Permission denied
    }
  );
} else {
  showAllFacilities(); // Geolocation not supported
}

// Display all facilities
function showAllFacilities() {
  facilities.forEach((f) => {
    L.marker([f.lat, f.lon])
      .addTo(map)
      .bindPopup(`<b>${f.name}</b><br>${f.county}`);
  });
}

// Display facilities near user (within 50km)
function showNearbyFacilities(userLat, userLon) {
  facilities.forEach((f) => {
    const distance = getDistanceFromLatLonInKm(userLat, userLon, f.lat, f.lon);
    if (distance <= 50) {
      L.marker([f.lat, f.lon])
        .addTo(map)
        .bindPopup(
          `<b>${f.name}</b><br>${f.county} (${distance.toFixed(1)} km away)`
        );
    }
  });
}

// Helper: Haversine Formula
function getDistanceFromLatLonInKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = deg2rad(lat2 - lat1);
  const dLon = deg2rad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(deg2rad(lat1)) *
      Math.cos(deg2rad(lat2)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function deg2rad(deg) {
  return deg * (Math.PI / 180);
}
