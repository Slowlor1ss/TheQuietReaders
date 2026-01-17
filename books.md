---
layout: default
title: Book Reviews
permalink: /books/
---

<h1 class="page-heading">Book Reviews</h1>

<div class="grid-container">
  {% assign book_posts = site.posts | where: "category", "Book" %}
  {% for post in book_posts %}
    <div class="card">
      <a href="{{ site.baseurl }}{{ post.url }}">
        <img src="{{ post.image }}" alt="{{ post.title }}">
        <div class="card-content">
          {% for genre in post.genre %}
            <span class="genre-tag">{{ genre }}</span>
          {% endfor %}
          <h3>{{ post.title }}</h3>
          <div class="stars">
             {% assign rating_int = post.rating | floor %}
             {% for i in (1..rating_int) %}★{% endfor %}
             {% if post.rating contains '.5' %}½{% endif %}
          </div>
        </div>
      </a>
    </div>
  {% endfor %}
</div>