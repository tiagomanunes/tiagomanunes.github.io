---
layout: default
title: Home
---

# Tiago Nunes
Short bio. Passionate about this, that, and breaking things.

<div class="card">
  <h2>Hack The Box Stats</h2>
  <ul>
    <li>🏅 <strong>Rank:</strong> {{ site.data.htb.rank }}</li>
    <li>🌍 <strong>World Rank:</strong> {{ site.data.htb.world_rank }}</li>
    <li>🇨🇭 <strong>Country Rank:</strong> {{ site.data.htb.country_rank }}</li>
    <li>📈 <strong>Personal Best Rank:</strong> {{ site.data.htb.best_rank }}</li>
    <li>💀 <strong>Owned Machines:</strong> {{ site.data.htb.owned_user }} user / {{ site.data.htb.owned_root }} root</li>
    <li>🔬 <strong>Current ProLab:</strong> {{ site.data.htb.prolab }} ({{ site.data.htb.prolab_progress }}% complete)</li>
  </ul>
  <div class="last-updated">Last retrieved from HTB API: {{ site.data.htb.last_updated }}</div>
</div>

