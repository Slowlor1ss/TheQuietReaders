---
layout: default
title: Game Reviews
permalink: /games/
---

<h1 class="page-heading">Game Reviews</h1>

<div class="grid-container">
  {% assign game_posts = site.posts | where: "category", "Game" %}
  {% for post in game_posts %}
    <div class="card">
      <a href="{{ site.baseurl }}{{ post.url }}">
          <img 
            src="{{ post.image | relative_url }}" 
            alt="{{ post.title }} book cover"
            loading="lazy"
            decoding="async"
          >
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