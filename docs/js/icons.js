/* =========================
   Rig & Well icon helpers
========================= */

/**
 * Decide main rig color based on movement state
 */
export function rigMainColor(rig) {
  if (rig.rig_moving === true) return "#FFD200";   // yellow = moving
  if (rig.rig_moving === false) return "#2C7BE5";  // blue = stationary
  return "#B0B0B0";                                // gray = unknown
}

/**
 * SVG-based rig icon with dynamic color
 */
export function rigIcon(color) {
  return L.divIcon({
    className: "",
    html: `
      <svg width="27" height="31"
           viewBox="0 0 27 31"
           xmlns="http://www.w3.org/2000/svg">

        <!-- Main body (dynamic color) -->
        <path fill-rule="evenodd" clip-rule="evenodd"
              d="M16.7 14 15 1h-3l-1.7 13H5v4H1v3h4v9h5.4v-9h6.2v9H22v-9h4v-3h-4v-4h-5.3Z"
              fill="${color}"/>

        <!-- Frame / outline -->
        <path fill-rule="evenodd" clip-rule="evenodd"
              d="m15.8 0 1.8 13H23v4h4v5h-4v9h-7.4v-9h-4.2v9H4v-9H0v-5h4v-4h5.4L11 0h4.8Z"
              fill="#191919"/>

        <!-- Legs -->
        <path d="M10.4 16v14H5V16h5.4Z" fill="${color}"/>
        <path d="M22 16v14h-5.4V16H22Z" fill="${color}"/>

        <!-- Deck -->
        <path d="M22 14v7H5v-7h17Z" fill="${color}"/>

        <!-- Base -->
        <path d="M1 18h25v3H1v-3Z" fill="${color}"/>

        <!-- Mast -->
        <path d="m15 1 2 15h-7l1.9-15h3Z" fill="${color}"/>

        <!-- Detail line -->
        <path d="M23 18H4.5v-1H23v1Z" fill="#191919"/>
      </svg>
    `,
    iconSize: [27, 31],
    iconAnchor: [13.5, 31]
  });
}

/**
 * Well color based on entry status
 */
export function wellColor(well) {
  return well.entryDate && well.entryDate !== "" ? "green" : "gray";
}
