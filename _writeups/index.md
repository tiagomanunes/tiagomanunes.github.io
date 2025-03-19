---
layout: default
title: Honest Write-ups
permalink: /writeups/
---

# Honest Write-ups

Photographers take thousands of pictures, but only show us the top 0.1%.

Reading a regular write-up of a box can also give you the impression that you are miles behind.

Not here. I'll tell you where I got stuck, how I got unstuck (even if it was with a hint), and what I learned. If I didn't learn anything, I probably won't write about it.

Hopefully that makes this yet-another-writeup-blog worth reading!

---

## Latest

{% assign latest_writeup = site.writeups | sort: 'date' | reverse | first %}

### {{ latest_writeup.title }}
{{ latest_writeup.content | slice: 0, 200 }}...

[Read more]({{ latest_writeup.url }})

---

## All the write-ups

<ul>
  {% for writeup in site.writeups %}
    {% if writeup.url != "/writeups/" %}
      <li><a href="{{ writeup.url }}">{{ writeup.title }}</a></li>
    {% endif %}
  {% endfor %}
</ul>

