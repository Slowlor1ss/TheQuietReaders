---
layout: default
title: All Book & Film & Article Reviews
permalink: /archive/
---
<div class="container">
    <div class="archive-container" style="max-width: 800px; margin: 0 auto; padding: 20px">
        <h1>Archive</h1>
        <p>Browse our complete catalog of reviews chronologically:</p>

        <ul style="line-height: 1.8; font-size: 1.1rem;">
            {% for post in site.posts %}
            <li>
                <span style="color: #888888; font-size: 0.9rem;">{{ post.date | date: "%Y-%m-%d" }}</span> - 
                <a href="{{ post.url | relative_url }}" style="font-weight: bold; color: #8e44ad;">
                {{ post.title }}
                </a>
                {% if post.genre %}
                <small style="color: #666666;">({{ post.genre | join: ', ' }})</small>
                {% endif %}
            </li>
            {% endfor %}
        </ul>
    </div>
</div>