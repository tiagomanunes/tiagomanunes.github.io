---
layout: default
title: Honest Write-ups
permalink: /writeups/
---

# Honest Write-ups

Photographers take thousands of pictures, but only show us the top 0.1%.

Reading a write-up of a box can also make us feel like we are miles behind.

Not here. I'll tell you where I got stuck, how I got unstuck (even if it was with a hint), and what I learned. If I didn't learn anything, I won't write about it.

Hopefully that makes this yet-another-writeup-blog worth reading!

---

{% assign writeups = site.writeups | reverse %}
{% assign latest_writeup = writeups | first %}

## Latest: {{ latest_writeup.title }}

{{ latest_writeup.excerpt | replace: "h2", "h3" }}

[Read more]({{ latest_writeup.url }})

---

## All the honesty

<ul>
  {% for writeup in writeups %}
    <li><a href="{{ writeup.url }}">{% if writeup.categories contains 'placeholder' %}active box{% else %}{{ writeup.date | date: "%Y-%m-%d" }}{% endif %} - {{ writeup.title }}</a></li>
  {% endfor %}
</ul>
