---
layout: default
title: Book Reviews
seo_title: "Romance & Fantasy Book Review Collection"
permalink: /books/
description: "Browse our complete library of honest book reviews. Filter by name, genre, and author to find your perfect next read."
image: /assets/images/icons/LogoWhiteBorder.png # Image shown when sharing this specific link
---

<h1 class="page-heading">Book Reviews</h1>

<div class="grid-container">
  {% assign book_posts = site.posts | where: "category", "Book" %}
  {% for post in book_posts %}
    <!-- <div class="card">
      <a href="{{ site.baseurl }}{{ post.url }}">
        <img src="{{ site.baseurl }}{{ post.image }}" alt="{{ post.title }}">
        <div class="card-content">
          {% for genre in post.genre %}
            <span class="genre-tag">{{ genre }}</span>
          {% endfor %}
          <h3>{{ post.title }}</h3>
          <div class="stars">
             {% include stars.html rating=post.rating %}
          </div>
        </div>
      </a>
    </div> -->
    <div class="card">
      <a href="{{ site.baseurl }}{{ post.url }}">
          <img 
            src="{{ post.image | relative_url }}" 
            alt="{{ post.title }} book cover"
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