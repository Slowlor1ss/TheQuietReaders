---
layout: default
title: Search Results
permalink: /search/
---

<div class="container">
  
  <div class="search-header">
    <h1>Library Search</h1>
    <p>Search by Author, Title, Genre, Review Author...</p>
    <div class="big-search-wrapper">
      <input type="text" id="page-search-input" placeholder="Type to filter books..." class="big-search-bar">
    </div>
  </div>

  <div id="search-results-container" class="grid-container">
    <p>Loading library...</p>
  </div>
  
</div>

<script>
  const params = new URLSearchParams(window.location.search);
  const initialQuery = params.get('q') || "";

  const container = document.getElementById('search-results-container');
  const inputField = document.getElementById('page-search-input');

  inputField.value = initialQuery;

  // Helper to build Genre Tags
  const getGenres = (genreString) => {
    if (!genreString) return '';
    return genreString.split(', ').map(genre => 
      `<span class="genre-tag">${genre}</span>`
    ).join(' '); 
  };

  fetch('/search.json')
    .then(response => response.json())
    .then(posts => {
      
      const showResults = (searchTerm) => {
        const lowerTerm = searchTerm.toLowerCase();

        const results = posts.filter(post => {
          const content = (post.title + " " + post.author + " " + post.genre).toLowerCase();
          return content.includes(lowerTerm);
        });

        if (results.length > 0) {
          container.innerHTML = results.map(post => `
            <div class="card">
              <a href="${post.url}">
                <img src="${post.image || '/assets/images/social-card.jpg'}" alt="${post.title}">
                <div class="card-content">
                  <div class="genres">
                    ${getGenres(post.genre)}
                  </div>
                  <h3>${post.title}</h3>
                  
                  <div class="stars">
                    ${post.stars_html}
                  </div>
                  
                </div>
              </a>
            </div>
          `).join('');
        } else {
          container.innerHTML = `<p>No books found for "<strong>${searchTerm}</strong>".</p>`;
        }
      };

      showResults(initialQuery);

      inputField.addEventListener('input', (e) => {
        showResults(e.target.value);
      });

    })
    .catch(error => {
      console.error('Error:', error);
      container.innerHTML = '<p>Something went wrong loading the library.</p>';
    });
</script>

<style>
  .search-header {
    text-align: center;
    margin-bottom: 40px;
  }

  .search-header h1 {
    margin-bottom: 0px;
  }
  .search-header p {
    margin-top: 0px;
  }

  .big-search-wrapper {
    max-width: 600px;
    margin: 20px auto;
  }

  .big-search-bar {
    width: 100%;
    padding: 15px 25px;
    font-size: 1.2rem;
    border: 2px solid #eee;
    border-radius: 50px;
    outline: none;
    transition: all 0.3s ease;
    background-color: #fdfbfd;
  }

  .big-search-bar:focus {
    border-color: #8e44ad;
    background-color: #fff;
    box-shadow: 0 4px 12px rgba(142, 68, 173, 0.1);
  }

  .grid-container {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 30px;
  }

  .grid-container p {
    text-align: center;
  }
</style>