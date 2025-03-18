---
layout: default
title: Honest Write-ups
permalink: /writeups/
---

# Honest Write-ups

<ul>
  {% for writeup in site.writeups %}
    {% if writeup.name != "index.html" %}
      <li><a href="{{ writeup.url }}">{{ writeup.title }}</a></li>
    {% endif %}
  {% endfor %}
</ul>

