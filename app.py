from flask import Flask, render_template, request, jsonify
from mysql_connect import get_connection
import json
from ml_brain_function import hybrid_recommend

app = Flask(__name__)

# MYSQL CONNECTION

conn = get_connection()
cursor = conn.cursor(dictionary=True)


# HOME PAGE

@app.route('/')
def home():

    # ALL MOVIES + WEB SERIES
    cursor.execute("""
        SELECT
            movie_name,
            content_type,
            category,
            genre,
            duration_display,
            watch_type,
            rating,
            release_year,
            poster_url,
            mood,
            ott_platform,
            actor,trailer_url,
            is_trending
        FROM movies
        ORDER BY rating DESC
    """)
    movies = cursor.fetchall()

    # TOP TRENDING
    # recent + trending + rating > 8.5
    cursor.execute("""
        SELECT
            movie_name,
            content_type,
            category,
            genre,
            duration_display,
            watch_type,
            rating,
            release_year,
            poster_url,
            mood,
            ott_platform,
            actor,
            trailer_url,
            is_trending
        FROM movies
        WHERE is_trending = 'yes'
          AND rating >= 8.9
        ORDER BY rating DESC
        LIMIT 15
    """)
    trending_movies = cursor.fetchall()

    return render_template(
        "index.html",
        movies=movies,
        trending_movies=trending_movies
    )


# SEARCH BY MOVIE NAME
# (MOVIE / SERIES BASED)

@app.route('/search', methods=['POST'])
def search_movie():
    data = request.json

    movie_name = data['movie_name']
    content_type = data['content_type']

    query = """
        SELECT *
        FROM movies
        WHERE movie_name LIKE %s
          AND content_type = %s
    """

    values = (
        "%" + movie_name + "%",
        content_type
    )

    cursor.execute(query, values)
    result = cursor.fetchall()

    return jsonify(result)


# SEARCH BY ACTOR

@app.route('/search_actor', methods=['POST'])
def search_actor():
    data = request.json

    actor_name = data['actor']
    content_type = data['content_type']

    query = """
        SELECT *
        FROM movies
        WHERE actor LIKE %s
          AND content_type = %s
    """

    values = (
        "%" + actor_name + "%",
        content_type
    )

    cursor.execute(query, values)
    result = cursor.fetchall()

    return jsonify(result)


# FILTER RECOMMENDATION
# now calls ML hybrid_recommend instead of plain SQL

@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.json

    preferences  = data.get('preferences', {})
    behavior     = data.get('behavior', [])

    filters = {
        'category':     data.get('category', ''),
        'genre':        data.get('genre', ''),
        'content_type': data.get('content_type', ''),
    }

    # NEW - fetch real behavior from MySQL if user_id provided
    user_id = data.get('user_id', '')
    if user_id:
        cursor.execute("""
            SELECT movie_id, action, weight
            FROM user_behavior
            WHERE user_id = %s
        """, (user_id,))
        behavior = cursor.fetchall()

    result = hybrid_recommend(preferences, behavior, filters)

    return jsonify(result)


# MOOD BASED PICKS

@app.route('/mood/<mood_name>/<content_type>')
def mood_pick(mood_name, content_type):

    query = """
        SELECT *
        FROM movies
        WHERE mood = %s
          AND content_type = %s
        LIMIT 8
    """

    values = (
        mood_name,
        content_type
    )

    cursor.execute(query, values)
    result = cursor.fetchall()

    return jsonify(result)


# MOVIE / WEB SERIES SWITCH

@app.route('/content/<type>')
def content_type(type):

    query = """
        SELECT *
        FROM movies
        WHERE content_type = %s
    """

    values = (type,)

    cursor.execute(query, values)
    result = cursor.fetchall()

    return jsonify(result)


# NEW - SAVE USER PREFERENCES ON FIRST VISIT

@app.route('/save_user', methods=['POST'])
def save_user():
    data        = request.json
    user_id     = data['user_id']
    preferences = json.dumps(data['preferences'])

    cursor.execute("""
        INSERT INTO users (user_id, preferences)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE preferences = %s
    """, (user_id, preferences, preferences))

    conn.commit()
    return jsonify({'status': 'saved'})


# NEW - LOAD USER ON REVISIT

@app.route('/load_user', methods=['POST'])
def load_user():
    data    = request.json
    user_id = data['user_id']

    cursor.execute("""
        SELECT preferences FROM users
        WHERE user_id = %s
    """, (user_id,))

    user = cursor.fetchone()
    if user:
        return jsonify({
            'found':       True,
            'preferences': json.loads(user['preferences'])
        })

    return jsonify({'found': False})


# NEW - TRACK USER BEHAVIOR (like / dislike)

@app.route('/track_behavior', methods=['POST'])
def track_behavior():
    data     = request.json
    user_id  = data['user_id']
    movie_id = data['movie_id']
    action   = data['action']
    weight   = data['weight']

    cursor.execute("""
        INSERT INTO user_behavior (user_id, movie_id, action, weight)
        VALUES (%s, %s, %s, %s)
    """, (user_id, movie_id, action, weight))

    conn.commit()
    return jsonify({'status': 'tracked'})


# RUN APP

if __name__ == '__main__':
    app.run(debug=True)