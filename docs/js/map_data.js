// js/map_data.js
import { rigIcon, rigMainColor, wellColor } from "./icons.js";

export async function loadMapData(map) {
  const wellsByName = {};

  // Load wells
try {
  const wells = await fetch('data/sodirdata.json').then(r => r.json());
  wells.forEach(w => {
    const lat = Number(w.lat);
    const lon = Number(w.lon);
    if (isNaN(lat) || isNaN(lon)) return;
    
    wellsByName[w.wellbore_name] = w;

    L.circleMarker([lat, lon], {
      radius: 6,
      fillColor: wellColor(w),
      color: "white",
      weight: 1,
      fillOpacity: 0.8
    }).bindPopup(`
      <b>Well:</b> ${w.wellbore_name}<br>
      <b>Field:</b> ${w.field}<br>
      <b>Operator:</b> ${w.operator}<br>
      <b>Entry date:</b> ${w.entryDate||"—"}<br>
      <b>Status:</b> ${w.status}<br>
      <b>Assigned Rig:</b> ${w.rig_name}<br>
      <a href="${w.fact_page_url}" target="_blank">Fact page</a>
    `).addTo(map);
  });
} catch(err) {
  console.error("Failed to load wells:", err);
}


  // Load rigs and draw paths to likely wells
  try {
    const data = await fetch('data/rig_well_analysis.json').then(r=>r.json());
    if(!data.rigs) return wellsByName;

    Object.values(data.rigs).forEach(rig => {
      if(rig.lat == null || rig.lon == null) return;
      const marker = L.marker([rig.lat, rig.lon], { icon: rigIcon(rigMainColor(rig)) })
        .bindPopup(`
          <b>Rig:</b> ${rig.rig_name}<br>
          <b>MMSI:</b> ${rig.mmsi}<br>
          <b>Type:</b> ${rig.rig_type}<br>
          <b>Likely target:</b> ${rig.likely_target_well||"—"}<br>
          <b>Moving:</b> ${rig.rig_moving}<br>
          <b>Last seen:</b> ${rig.last_seen}
        `)
        .addTo(map);

      const target = wellsByName[rig.likely_target_well];
      if(target && target.lat != null && target.lon != null){
        L.polyline([[rig.lat, rig.lon],[target.lat,target.lon]],{color:"green",weight:2,dashArray:"4,4"}).addTo(map);
      }
    });
  } catch(err) {
    console.error("Failed to load rigs:", err);
  }

  return wellsByName;
}
