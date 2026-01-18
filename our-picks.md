---
layout: default
title: Our Picks
permalink: /our-picks/
---

<div class="container">
  <!-- <div class="section-header">
    <h1>Our Picks</h1>
  </div> -->
  <h1 class="page-heading" style="margin-bottom: 0px;">Our Picks</h1>
  <p style="margin-top: 0px; margin-bottom: 30px;">The books we simply couldn't put down.</p>

  <div class="grid-container">
    {% assign featured = site.posts | where: "featured", true %}
    {% for post in featured %}
    
    <div class="card">
      <a href="{{ site.baseurl }}{{ post.url }}">
        <img src="{{ site.baseurl }}{{ post.image }}" alt="{{ post.title }}">
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
            {{ post.description }}
          </p>

        </div>
      </a>
    </div>
    {% endfor %}
  </div>
</div>