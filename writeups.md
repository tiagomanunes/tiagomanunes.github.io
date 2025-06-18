---
layout: default
title: Honest Write-ups
excerpt: Reading a write-up of a box can make us feel like we're miles behind. Not here. I'll tell you how it really went down.
permalink: /writeups/
---

# Honest Write-ups

Photographers take thousands of pictures, but only show us the top 0.1%.

Reading a write-up of a box can also make us feel like we are miles behind.

Not here. I'll tell you where I got stuck, how I got unstuck (even if it was with a hint), and what I learned. If I didn't learn anything, I won't write about it.

Hopefully that makes this yet-another-writeup-blog worth reading!

---

{% assign writeups = site.writeups | reverse %}
{% assign latest_retired_writeup = writeups | where: "retired", true | first %}

## Latest: {{ latest_retired_writeup.title }}

{{ latest_retired_writeup.excerpt | replace: "h2", "h3" }}

[Read more]({{ latest_retired_writeup.url }})

---
<div class="feed">
  <h2>All the honesty</h2>
  <div class="rss-icon">
    <a href="{{ "/feed.xml" | relative_url }}"><i class="fas fa-rss"></i></a>
  </div>
  <ul>
    {% for writeup in writeups %}
      <li><a href="{{ writeup.url }}">{% if writeup.retired == false %}active box{% else %}{{ writeup.date | date: "%Y-%m-%d" }}{% endif %} - {{ writeup.title }}</a></li>
    {% endfor %}
  </ul>
</div>
