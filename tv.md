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
        <img src="{{ site.baseurl }}{{ post.image }}" alt="{{ post.title }}">
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