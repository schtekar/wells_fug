// js/icons.js
/* =========================
   Rig & Well Icon Utilities
========================= */

/**
 * Returns the main color for a rig based on its movement status
 * @param {Object} rig - rig object
 * @returns {string} hex color
 */
export function rigMainColor(rig) {
  if (rig.rig_moving === true) return "#FFD200";   // yellow if moving
  if (rig.rig_moving === false) return "#2C7BE5";  // blue if stationary
  return "#B0B0B0";                                // gray unknown
}

/**
 * Returns color for a well based on whether it has been entered
 * @param {Object} well - well object
 * @returns {string} hex color
 */
export function wellColor(well) {
  return well.entryDate && well.entryDate !== "" ? "green" : "gray";
}

/**
 * Returns a Leaflet divIcon for a rig, using dynamic color
 * @param {string} color - fill color for rig
 * @returns {L.DivIcon}
 */
export function rigIcon(color) {
  return L.divIcon({
    className: "",
    html: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 8.2 9.2" fill="none"> 
  <path d="M0.1 5.1 0.1 7.1 h1 v2 h2 v-2 h2 v2 h2 v-2 h1 v-2 h-2 l-1 -5 h-2 l-1 5 h-2 Z" fill="${color}" stroke="#191919" stroke-width="0.5"/>
    </svg>`,
    iconSize: [24, 24],
    iconAnchor: [13.5, 24]
  });
}

/**
 * Creates a Leaflet legend control
 * @returns {L.Control} legend
 */
export function createLegend() {
  const legend = L.control({ position: "bottomright" });
  legend.onAdd = () => {
    const div = L.DomUtil.create("div", "legend");
    div.innerHTML = `
      <b>Legend</b><br>
      ● Green: Entered well<br>
      ● Gray: Not entered well<br>
      🟦 Rig stationary<br>
      🟨 Rig moving<br>
      ── Path to likely well
    `;
    return div;
  };
  return legend;
}
