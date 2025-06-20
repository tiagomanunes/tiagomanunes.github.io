---
layout: default
title: Articles
excerpt: Miscellaneous InfoSec content hopefully worth a read, still neon-lit.
permalink: /articles/
---

# Articles
{% assign articles = site.articles | reverse %}
{% for article in articles %}
    <li><a href="{{ article.url }}">{{ article.date | date: "%Y-%m-%d" }} - {{ article.title }}</a></li>
{% endfor %}
