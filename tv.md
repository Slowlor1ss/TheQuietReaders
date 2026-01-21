---
layout: default
title: Movies & TV
permalink: /tv/
---

<h1 class="page-heading">Movies & TV Reviews</h1>

<div class="grid-container">
  {% assign tv_posts = site.posts | where: "category", "TV" %}
  {% for post in tv_posts %}
    <div class="card">
      <a href="{{ site.baseurl }}{{ post.url }}">
        {% if post.image.path %}
          <img 
            src="{{ post.image.path | relative_url }}" 
            alt="{{ post.image.alt | default: post.title }}"
            loading="lazy"
            decoding="async"
            height="280"
          >
        {% else %}
          <img 
            src="{{ post.image | relative_url }}" 
            alt="{{ post.title }}"
            loading="lazy"
            decoding="async"
          >
        {% endif %}
        <div class="card-content">
          <h3>{{ post.title }}</h3>
          <div class="stars">
             {% include stars.html rating=post.rating %}
          </div>
        </div>
      </a>
    </div>
  {% endfor %}
</div>