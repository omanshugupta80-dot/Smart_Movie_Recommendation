# Smart Movie Recommender

ML-powered movie recommendation system using
Hybrid Collaborative + Content Based Filtering

## Tech Stack
- Python Flask
- Machine Learning (scikit-learn)
- MySQL Database
- HTML CSS JavaScript

## Setup

### 1. Clone the repo
git clone your_repo_url
cd Smart_Movie_Recommendation

### 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate

### 3. Install dependencies
pip install all required package

### 4. Setup MySQL
mysql -u root -p < movie_recommender.sql

### 5. Create .env file
DB_PASSWORD=your_mysql_password

### 6. Run
python app.py

### 7. Open browser
http://localhost:5000