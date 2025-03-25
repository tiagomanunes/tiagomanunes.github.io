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

## Latest

{% assign latest_writeup = site.writeups | where: 'layout', 'post' | sort: 'date' | reverse | first %}

### {{ latest_writeup.title }}
{{ latest_writeup.content | remove: '#' | truncate: 200 }}

[Read more]({{ latest_writeup.url }})

---

## All the write-ups

<ul>
  {% for writeup in site.writeups %}
    {% if writeup.url != "/writeups/" %}
      <li><a href="{{ writeup.url }}">{{ writeup.date }} - {{ writeup.title }}</a></li>
    {% endif %}
  {% endfor %}
</ul>

