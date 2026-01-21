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
  // Get the URL query (e.g. ?q=book)
  const params = new URLSearchParams(window.location.search);
  const initialQuery = params.get('q') || "";

  // Get the HTML elements
  const container = document.getElementById('search-results-container');
  const inputField = document.getElementById('page-search-input');
  
  // Get the Jekyll Base URL (Run once by server)
  const BASE_URL = "{{ site.baseurl }}";

  inputField.value = initialQuery;

  // Helper: Build genre HTML tags
  const getGenres = (genreString) => {
    if (!genreString) return '';
    return genreString.split(', ').map(genre => 
      `<span class="genre-tag">${genre}</span>`
    ).join(' '); 
  };

  // Fetch the JSON data
  fetch('/search.json')
    .then(response => response.json())
    .then(posts => {
      
      const showResults = (searchTerm) => {
        const lowerTerm = searchTerm.toLowerCase();

        const results = posts.filter(post => {
          const t = post.title ? post.title : "";
          const a = post.author ? post.author : "";
          const g = post.genre ? post.genre : "";
          const content = (t + " " + a + " " + g).toLowerCase();
          return content.includes(lowerTerm);
        });

        if (results.length > 0) {
          container.innerHTML = results.map(post => {
            
            // --- JAVASCRIPT IMAGE LOGIC (No Liquid Here!) ---
            let imgSrc = "";
            let imgAlt = post.title;

            if (post.image) {
                // Case A: New Format (Object)
                if (typeof post.image === 'object' && post.image.path) {
                    imgSrc = post.image.path;
                    if (post.image.alt) imgAlt = post.image.alt;
                } 
                // Case B: Old Format (String)
                else if (typeof post.image === 'string') {
                    imgSrc = post.image;
                }
            }

            // Fix Path: Add baseurl if missing
            if (imgSrc && imgSrc.startsWith('/') && BASE_URL) {
                if (!imgSrc.startsWith(BASE_URL)) {
                    imgSrc = BASE_URL + imgSrc;
                }
            }
            // ------------------------------------------------

            return `
            <div class="card">
              <a href="${post.url}">
                <img 
                    src="${imgSrc}" 
                    alt="${imgAlt}"
                    loading="lazy"
                    decoding="async"
                >
                <div class="card-content">
                  <div class="genres">
                    ${getGenres(post.genre)}
                  </div>
                  <h3>${post.title}</h3>
                  <div class="stars">
                    ${post.stars_html || ''} 
                  </div>
                </div>
              </a>
            </div>
          `}).join('');
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