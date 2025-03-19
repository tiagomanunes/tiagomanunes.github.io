---
layout: default
title: Honest Write-ups
permalink: /writeups/
---

# Honest Write-ups

Write an intro.

<ul>
  {% for writeup in site.writeups %}
    {% if writeup.url != "/writeups/" %}
      <li><a href="{{ writeup.url }}">{{ writeup.title }}</a></li>
    {% endif %}
  {% endfor %}
</ul>

