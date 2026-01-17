// Shrink Header on Scroll
window.onscroll = function() {scrollFunction()};

function scrollFunction() {
  const header = document.getElementById("site-header");
  const backToTop = document.getElementById("back-to-top");

  if (document.body.scrollTop > 50 || document.documentElement.scrollTop > 50) {
    header.classList.add("shrink");
    backToTop.style.display = "block";
  } else {
    header.classList.remove("shrink");
    backToTop.style.display = "none";
  }
}

// Scroll to Top
function scrollToTop() {
  window.scrollTo({top: 0, behavior: 'smooth'});
}