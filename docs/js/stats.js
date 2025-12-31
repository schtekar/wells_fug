// js/stats.js
export async function loadKeyStats(topbarId="stats") {
  const el = document.getElementById(topbarId);
  if(!el) return;

  try {
    const stats = await fetch('data/rw_keystats.json').then(r=>r.json());
    el.innerHTML = `
      Rigs: ${stats.num_rigs} |
      Wells: ${stats.num_wells} |
      Entered: ${stats.entered_wells} |
      Not entered: ${stats.not_entered_wells} |
      Moving rigs: ${stats.moving_rigs} |
      Stationary rigs: ${stats.stationary_rigs}
    `;
  } catch(err) {
    console.error("Failed to load key stats:", err);
    el.innerHTML = "Stats unavailable";
  }
}

