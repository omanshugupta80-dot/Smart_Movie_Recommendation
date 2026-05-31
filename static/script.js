
 
// CURRENT SELECTED TYPE
 
let selectedType = "Movie";
 
 
// NEW - USER ID CHECK ON PAGE LOAD
 
window.onload = function() {
    let userId = localStorage.getItem("user_id");
    if (!userId) {
        userId = "u_" + Math.random().toString(36).substr(2, 8);
        localStorage.setItem("user_id", userId);
        document.getElementById("preferencePopup").style.display = "flex";
    } else {
        fetch("/load_user", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: userId })
        });
    }
};
 
 
// NEW - PREFERENCE POPUP CHIP TOGGLE
 
let selectedGenres     = [];
let selectedMoods      = [];
let selectedCategories = [];
 
function toggleChip(chip, type) {
    chip.classList.toggle("chip-active");
    const value = chip.innerText.replace(/[^\w\s-]/g, "").trim();
    if (type === "genre") {
        selectedGenres = updateList(selectedGenres, value);
    } else if (type === "mood") {
        selectedMoods = updateList(selectedMoods, value);
    } else if (type === "category") {
        selectedCategories = updateList(selectedCategories, value);
    }
}
 
function updateList(arr, value) {
    return arr.includes(value)
        ? arr.filter(v => v !== value)
        : [...arr, value];
}
 
 
// NEW - SAVE PREFERENCES
 
function savePreferences() {
    const userId = localStorage.getItem("user_id");
    const preferences = {
        genres:     selectedGenres,
        moods:      selectedMoods,
        categories: selectedCategories
    };
    localStorage.setItem("preferences", JSON.stringify(preferences));
 
    fetch("/save_user", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, preferences: preferences })
    })
    .then(() => {
        document.getElementById("preferencePopup").style.display = "none";
    });
}
 
 
// DISPLAY MOVIES / SERIES
 
function displayMovies(movies) {
    let movieResults = document.getElementById("movieResults");
    movieResults.innerHTML = "";
 
    if (movies.length === 0) {
        movieResults.innerHTML = "<h2>No Content Found!</h2>";
        return;
    }
 
    movies.forEach(movie => {
        movieResults.innerHTML += `
            <div class="movie-card">
                <img src="/static/images/${movie.poster_url}"
                     alt="${movie.movie_name}"
                     onclick="openTrailer('${movie.trailer_url}')">
 
                <h3>${movie.movie_name}</h3>
 
                <p><strong>Type:</strong> ${movie.content_type}</p>
                <p><strong>Category:</strong> ${movie.category}</p>
                <p><strong>Genre:</strong> ${movie.genre}</p>
                <p><strong>Duration:</strong> ${movie.duration_display}</p>
                <p><strong>Watch Type:</strong> ${movie.watch_type}</p>
                <p><strong>IMDb:</strong> ${movie.rating}</p>
                <p><strong>OTT:</strong> ${movie.ott_platform}</p>
                <p><strong>Actor:</strong> ${movie.actor}</p>
 
                <div class="like-dislike">
                    <button class="btn-like"
                        onclick="trackBehavior(${movie.id}, 'liked')">
                        👍 Like
                    </button>
                    <button class="btn-dislike"
                        onclick="trackBehavior(${movie.id}, 'disliked')">
                        👎 Dislike
                    </button>
                </div>
            </div>
        `;
    });
}
 
 
// NEW - TRACK BEHAVIOR (like / dislike)
 
function trackBehavior(movieId, action) {
    const userId = localStorage.getItem("user_id");
    const weight = action === "liked" ? 5 : -5;
 
    fetch("/track_behavior", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_id:  userId,
            movie_id: movieId,
            action:   action,
            weight:   weight
        })
    });
 
    const btn = event.target;
    btn.style.opacity = "0.5";
    btn.disabled = true;
}
 
 
// SEARCH BY MOVIE NAME
 
function searchMovie() {
    let movieName = document.getElementById("searchBar").value;
 
    fetch("/search", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            movie_name: movieName,
            content_type: selectedType
        })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("resultTitle").innerText =
            "Your Movie Matches";
 
        displayMovies(data);
 
        document.getElementById("movieResults")
            .scrollIntoView({
                behavior: "smooth"
            });
    });
}
 
 
 
// SEARCH BY ACTOR
 
function searchByActor() {
    let actorName = document.getElementById("actorSearch").value;
 
    fetch("/search_actor", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            actor: actorName,
            content_type: selectedType
        })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("resultTitle").innerText =
            "🎭 Your Actor Movies Available ";
 
        displayMovies(data);
 
        document.getElementById("movieResults")
            .scrollIntoView({
                behavior: "smooth"
            });
    });
}
 
 
 
// FILTER RECOMMENDATION
 
function recommendMovie() {
    let category  = document.getElementById("category").value;
    let genre     = document.getElementById("genre").value;
    
    let userId    = localStorage.getItem("user_id");
    let preferences = JSON.parse(localStorage.getItem("preferences") || "{}");
 
    fetch("/recommend", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            category:     category,
            genre:        genre,
            
            content_type: selectedType,
            user_id:      userId,        // send user id for ML
            preferences:  preferences   // sends saved preferences for ML
        })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("resultTitle").innerText =
            "Movies Recommended ";
 
        displayMovies(data);
 
        document.getElementById("movieResults")
            .scrollIntoView({
                behavior: "smooth"
            });
    });
}
 
 
 
// MOOD BASED PICKS
 
 
function getMoodMovies(moodName) {
    fetch(`/mood/${moodName}/${selectedType}`)
    .then(response => response.json())
    .then(data => {
        document.getElementById("resultTitle").innerText =
            "😊 Movie Matches Based on Your Mood";
 
        displayMovies(data);
 
        document.getElementById("movieResults")
            .scrollIntoView({
                behavior: "smooth"
            });
    });
}
 
 
 
// MOVIES / WEB SERIES SWITCH
 
 
function selectContentType(type, clickedButton) {
    selectedType = type;
 
    document.querySelectorAll(".content-switch button")
        .forEach(btn => btn.classList.remove("active"));
 
    clickedButton.classList.add("active");
 
    fetch(`/content/${type}`)
    .then(response => response.json())
    .then(data => {
        if (type === "Movie") {
            document.getElementById("resultTitle").innerText =
                "Movie More To Explore";
        } else {
            document.getElementById("resultTitle").innerText =
                " Web Series More To Explore";
        }
 
        displayMovies(data);
 
        document.getElementById("movieResults")
            .scrollIntoView({
                behavior: "smooth"
            });
    });
}
 
 
 
// SLIDER BUTTONS
 
 
function slideMovies(sectionId, amount) {
    const slider = document.getElementById(sectionId);
    slider.scrollLeft += amount;
}
// trailer
function openTrailer(url) {
    if (url && url !== "null") {
        window.open(url, "_blank");
    } else {
        alert("Trailer not available");
    }
}