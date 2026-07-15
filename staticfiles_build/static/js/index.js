/* ================= MAP SETUP ================= */
const map = L.map("map").setView([-0.0917, 34.768], 12);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

/* ================= ICONS ================= */
const mentalIcon = L.icon({
  iconUrl:
    "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const rehabIcon = L.icon({
  iconUrl:
    "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const youAreHereIcon = L.icon({
  iconUrl:
    "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

/* ================= GLOBALS ================= */
let allFacilities = [];
let markers = [];
let routeControls = [];
let userLocation = null;

/* ================= HELPERS ================= */
function getDistanceKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2;
  return R * (2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
}

function clearMarkers() {
  markers.forEach((m) => map.removeLayer(m));
  markers = [];
}

function clearRoutes() {
  routeControls.forEach((r) => r.remove());
  routeControls = [];
}

/* ================= RENDER FACILITIES ================= */
function renderFacilities(facilities) {
  clearMarkers();
  clearRoutes();

  facilities.forEach((f) => {
    const icon = f.type === "rehab" ? rehabIcon : mentalIcon;

    const marker = L.marker([f.lat, f.lng], { icon })
      .bindPopup(() => {
        let html = `
          <div style="font-family: Arial; line-height:1.5">
            <strong style="font-size:16px">${f.name}</strong><br>
            <strong>Operating Time:</strong> ${f.operating_time}<br>
            <strong>Patient Care:</strong> ${f.patient_care_setting}<br>
            <strong>Payment:</strong> ${f.modes_of_payment}<br>
            <strong>Insurance:</strong> ${f.insurance_accepted}<br>
            <strong>Days:</strong> ${f.operating_days}<br>
        `;

        if (userLocation) {
          const d = getDistanceKm(
            userLocation.lat,
            userLocation.lng,
            f.lat,
            f.lng,
          ).toFixed(2);
          html += `<em>${d} km away</em>`;
        }

        html += `</div>`;
        return html;
      })
      .addTo(map);

    markers.push(marker);
  });
}

/* ================= FETCH FROM DJANGO ================= */
async function loadFacilities() {
  try {
    const res = await fetch("/api/facilities/");
    const data = await res.json();

    allFacilities = data.map((f) => ({
      id: f.id,
      name: f.name,
      lat: f.lat,
      lng: f.lng,
      type: f.type === "mental_health" ? "mental" : "rehab",
      ward: f.ward || "N/A",
      operating_time: f.operating_time || "N/A",
      patient_care_setting: f.patient_care_setting || "N/A",
      modes_of_payment: f.modes_of_payment || "N/A",
      insurance_accepted: f.insurance_accepted || "N/A",
      operating_days: f.operating_days || "N/A",
    }));

    renderFacilities(allFacilities);

    if (userLocation) drawRouteToNearest();
  } catch (err) {
    console.error("Error loading facilities:", err);
  }
}

/* ================= ROUTE TO NEAREST ================= */
function drawRouteToNearest() {
  if (!userLocation || !allFacilities.length) return;

  clearRoutes();

  const nearest = [...allFacilities]
    .map((f) => ({
      ...f,
      distance: getDistanceKm(userLocation.lat, userLocation.lng, f.lat, f.lng),
    }))
    .sort((a, b) => a.distance - b.distance)[0];

  if (!nearest) return;

  const rc = L.Routing.control({
    waypoints: [
      L.latLng(userLocation.lat, userLocation.lng),
      L.latLng(nearest.lat, nearest.lng),
    ],
    addWaypoints: false,
    draggableWaypoints: false,
    routeWhileDragging: false,

    // 🔥 THESE TWO LINES REMOVE THE SIDEPANE
    show: false,
    collapsible: false,

    createMarker: () => null,
  }).addTo(map);

  routeControls.push(rc);
}

/* ================= GEOLOCATION ================= */
function onLocationSuccess(pos) {
  userLocation = {
    lat: pos.coords.latitude,
    lng: pos.coords.longitude,
  };

  L.marker([userLocation.lat, userLocation.lng], { icon: youAreHereIcon })
    .addTo(map)
    .bindPopup("You are here")
    .openPopup();

  map.setView([userLocation.lat, userLocation.lng], 13);

  renderFacilities(allFacilities);
  drawRouteToNearest();
}

/* ================= INIT ================= */
loadFacilities();

if (navigator.geolocation) {
  navigator.geolocation.getCurrentPosition(onLocationSuccess);
}
