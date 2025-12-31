// js/map_data.js
import { rigIcon, rigMainColor, wellColor } from "./icons.js";

export async function loadMapData(map) {
  const wellsByName = {};

  // Load wells
  try {
    const wells = await fetch('data/sodirdata.json').then(r=>r.json());
    wells.forEach(w => {
      if(w.lat == null || w.lon == null) return;
      wellsByName[w.wellbore_name] = w;
      L.circleMarker([w.lat, w.lon], {
        radius: 6,
        fillColor: wellColor(w),
        color: "white",
        weight: 1,
        fillOpacity: 0.8
      }).bindPopup(`
        <b>Well:</b> ${w.wellbore_name}<br>
        <b>Rig:</b> ${w.rig_name}<br>
        <b>Status:</b> ${w.status}<br>
        <b>Entry date:</b> ${w.entryDate||"—"}<br>
        <b>Operator:</b> ${w.operator}<br>
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
          <b>Rig:</b> ${rig.mmsi}<br>
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
