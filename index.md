---
layout: default
title: Home
---

# Tiago Nunes
Short bio. Passionate about this, that, and breaking things.

<div class="card">
  <h2>Hack The Box Stats</h2>
  <ul>
    <li># <strong>Rank:</strong> {{ site.data.htb_data.rank_label }}</li>
    <li># <strong>World Rank:</strong> {{ site.data.htb_data.rank_global }}</li>
    <li># <strong>Personal Best:</strong> {{ site.data.htb_data.best_rank }} ({{ site.data.htb_data.best_date }})</li>
    <li># <strong>Country Rank:</strong> {{ site.data.htb_data.rank_country }}</li>
    <li># <strong>Owned Machines:</strong> {{ site.data.htb_data.owns_user }} user / {{ site.data.htb_data.owns_root }} root</li>
    <li># <strong>Current ProLab:</strong> {{ site.data.htb_data.current_prolab }} ({{ site.data.htb_data.prolab_owned_flags }}/{{ site.data.htb_data.prolab_total_flags }} flags)</li>
  </ul>
  <div class="last-updated">Last retrieved from HTB API: {{ site.data.htb_data.last_updated }}</div>
</div>

