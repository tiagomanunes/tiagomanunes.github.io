---
layout: default
title: Home
---

# Tiago Nunes
Short bio. Passionate about this, that, and breaking things.

<div class="card">
  <h2>Hack The Box Stats</h2>
  <ul>
    <li># <strong>Rank:</strong> {{ site.data.htb_data.rank }}</li>
    <li># <strong>World Rank:</strong> {{ site.data.htb_data.world_rank }}</li>
    <li># <strong>Country Rank:</strong> {{ site.data.htb_data.country_rank }}</li>
    <li># <strong>Personal Best Rank:</strong> {{ site.data.htb_data.best_rank }}</li>
    <li># <strong>Owned Machines:</strong> {{ site.data.htb_data.owned_user }} user / {{ site.data.htb_data.owned_root }} root</li>
    <li># <strong>Current ProLab:</strong> {{ site.data.htb_data.prolab }} ({{ site.data.htb_data.prolab_progress }}% complete)</li>
  </ul>
  <div class="last-updated">Last retrieved from HTB API: {{ site.data.htb_data.last_updated }}</div>
</div>

