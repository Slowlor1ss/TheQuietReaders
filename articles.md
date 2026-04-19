---
layout: default
title: Articles & Essays
permalink: /articles/
---

<div class="page-header">
    <h1>Articles & Analysis</h1>
    <p>Deep dives, book trends, and reading guides.</p>
</div>

<div class="grid-container">
    {% assign articles = site.posts | where: "category", "Article" %}
    
    {% for post in articles %}
    <div class="card">
        <a href="{{ site.baseurl }}{{ post.url }}">
            <img 
                src="{{ post.image | relative_url }}" 
                alt="{{ post.title }} cover image"
                loading="lazy"
                decoding="async"
            >
            <div class="card-content">
                <div class="tags-container">
                    {% for genre in post.genre %}
                    <span class="genre-tag">{{ genre }}</span>
                    {% endfor %}
                </div>

                <h3>{{ post.title }}</h3>

                <p>
                    {{ post.customdesc | default: post.description }}
                </p>
            </div>
        </a>
    </div>
    {% else %}
    <p>No articles published yet.<br>Check back soon!</p>
    {% endfor %}
</div>