---
layout: default
title: Movies & TV
permalink: /tv/
---

<h1 class="page-heading">Movies & TV Reviews</h1>

<div class="grid-container">
  {% assign films = site.posts | where: "category", "Film" %}
  {% assign tv_shows = site.posts | where: "category", "TV" %}
  {% assign tv_and_film = films | concat: tv_shows | sort: "date" | reverse %}
  {% for post in tv_and_film %}
    <div class="card">
      <a href="{{ site.baseurl }}{{ post.url }}">
          <img 
            src="{{ post.image | relative_url }}" 
            {% if post.category == 'TV' %}
            alt="{{ post.title }} Tv cover"
            {% elsif post.category == 'Film' %}
            alt="{{ post.title }} film cover"
            {% endif %}
            loading="lazy"
            decoding="async"
          >
          <div class="card-content">
          
          <div class="tags-container" style="margin-bottom:10px;">
            {% for genre in post.genre %}
              <span class="genre-tag">{{ genre }}</span>
            {% endfor %}
          </div>

          <h3>{{ post.title }}</h3>

          <div class="stars" style="margin-bottom: 10px;">
            {% include stars.html rating=post.rating %}
          </div>

          <p style="font-size: 0.9rem; color: #666; margin-top: 10px;">
            {{ post.customdesc }}
          </p>

        </div>
      </a>
    </div>
  {% endfor %}
</div>