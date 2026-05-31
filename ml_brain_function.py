import pandas as pd
import numpy as np
from sklearn.preprocessing import MultiLabelBinarizer, MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from mysql_connect import get_connection

#   LOAD DATA... from MySQL
conn = get_connection()
df   = pd.read_sql("SELECT * FROM movies", conn)


#    BUILD FEATURE MATRIX 
# Converts every movie into a row of numbers using:
# genre, mood, category, watch_type, rating

def build_feature_matrix():

    # split compound genres like "Crime Thriller" → ["Crime", "Thriller"]
    genre_list = df['genre'].apply(
        lambda x: [g.strip() for g in x.replace('-', ' ').split()]
    )
    mood_list  = df['mood'].apply(lambda x: [x.strip()])
    cat_list   = df['category'].apply(lambda x: [x.strip()])
    wt_list    = df['watch_type'].apply(lambda x: [x.strip()])

    genre_mat = MultiLabelBinarizer().fit_transform(genre_list)
    mood_mat  = MultiLabelBinarizer().fit_transform(mood_list)
    cat_mat   = MultiLabelBinarizer().fit_transform(cat_list)
    wt_mat    = MultiLabelBinarizer().fit_transform(wt_list)

    # normalize rating to 0-1
    rating_mat = MinMaxScaler().fit_transform(df[['rating']])

    # combine with weights — genre matters most
    matrix = np.hstack([
        genre_mat  * 2.0,
        mood_mat   * 1.5,
        cat_mat    * 1.0,
        wt_mat     * 1.0,
        rating_mat * 0.5,
    ])

    return matrix


# ── TRAIN SVD (COLLABORATIVE) ─────────────────────────────
# Simulates 200 users with realistic rating patterns
# SVD finds hidden taste patterns across users

def build_svd_model(feature_matrix):

    np.random.seed(42)
    n_users  = 200
    n_movies = len(df)

    # simulate ratings based on real IMDb ratings + random noise
    ratings = np.zeros((n_users, n_movies))
    for u in range(n_users):
        rated_ids = np.random.choice(n_movies, np.random.randint(10, 30), replace=False)
        for mid in rated_ids:
            base  = df.iloc[mid]['rating'] / 10.0
            noise = np.random.normal(0, 0.15)
            ratings[u, mid] = min(5, max(1, round((base + noise) * 5)))

    svd = TruncatedSVD(n_components=10, random_state=42)
    U   = svd.fit_transform(ratings)
    Vt  = svd.components_

    # predicted rating matrix (all users × all movies)
    predicted = np.dot(U, Vt)

    return predicted, ratings


# ── BUILD MODELS AT STARTUP ───────────────────────────────

feature_matrix         = build_feature_matrix()
similarity_matrix      = cosine_similarity(feature_matrix)
predicted_ratings, ratings_matrix = build_svd_model(feature_matrix)


# ── CONTENT BASED SCORE ───────────────────────────────────
# Builds user taste vector from preferences + behavior
# then finds movies closest to that vector

def content_score(preferences, behavior):

    taste = np.zeros(feature_matrix.shape[1])

    pref_genres = preferences.get('genres', [])
    pref_moods  = preferences.get('moods', [])
    pref_cats   = preferences.get('categories', [])

    # add weight from preferences
    for i, row in df.iterrows():
        row_genres = [g.strip() for g in row['genre'].replace('-', ' ').split()]
        score = 0
        if any(g in pref_genres for g in row_genres): score += 2.0
        if row['mood'].strip() in pref_moods:         score += 1.5
        if row['category'].strip() in pref_cats:      score += 1.0
        if score > 0:
            taste += feature_matrix[i] * score

    # add/subtract weight from liked and disliked behavior
    for b in behavior:
        idx = df[df['id'] == b['movie_id']].index
        if len(idx) > 0:
            taste += feature_matrix[idx[0]] * b['weight']

    # if no taste signal at all — return equal scores
    if np.linalg.norm(taste) == 0:
        return list(range(len(df)))

    scores = cosine_similarity(taste.reshape(1, -1), feature_matrix)[0]
    ranked = np.argsort(scores)[::-1].tolist()
    return ranked  # list of movie indices ordered by similarity


# ── COLLABORATIVE SCORE ───────────────────────────────────
# Uses SVD predicted ratings to rank movies
# picks a simulated user whose behavior matches real user

def collab_score(behavior):

    n_movies   = len(df)
    user_vec   = np.zeros(n_movies)

    for b in behavior:
        idx = df[df['id'] == b['movie_id']].index
        if len(idx) > 0:
            # convert weight to 1-5 scale
            rating = 5 if b['weight'] > 0 else 1
            user_vec[idx[0]] = rating

    # find most similar simulated user
    if user_vec.sum() == 0:
        sim_user = 0  # default to first user
    else:
        sims     = cosine_similarity([user_vec], ratings_matrix)[0]
        sim_user = int(np.argmax(sims))

    scores = predicted_ratings[sim_user]
    ranked = np.argsort(scores)[::-1].tolist()
    return ranked  # list of movie indices ordered by predicted rating


# ── HYBRID RECOMMEND ──────────────────────────────────────
# Combines content + collaborative scores
# filters by content_type, ott, watch_type if given
# removes already liked/disliked movies from results

def hybrid_recommend(preferences, behavior, filters):

    content_type = filters.get('content_type', '')
    ott          = filters.get('ott', '')
    watch_type   = filters.get('watch_type', '')
    category     = filters.get('category', '')
    genre        = filters.get('genre', '')

    # decide weights based on how much behavior data we have
    if len(behavior) >= 5:
        # enough behavior — trust collaborative more
        content_weight = 0.5
        collab_weight  = 0.5
    else:
        # new user — trust content based more
        content_weight = 0.7
        collab_weight  = 0.3

    content_ranked = content_score(preferences, behavior)
    collab_ranked  = collab_score(behavior)

    n = len(df)

    # combine into hybrid score
    hybrid = {}
    for pos, idx in enumerate(content_ranked):
        hybrid[idx] = hybrid.get(idx, 0) + (n - pos) * content_weight
    for pos, idx in enumerate(collab_ranked):
        hybrid[idx] = hybrid.get(idx, 0) + (n - pos) * collab_weight

    # sort by hybrid score
    final_ranked = sorted(hybrid, key=hybrid.get, reverse=True)

    # ids to skip — already interacted
    liked_ids    = {b['movie_id'] for b in behavior if b['weight'] > 0}
    disliked_ids = {b['movie_id'] for b in behavior if b['weight'] < 0}
    skip_ids     = liked_ids | disliked_ids

    results = []

    for idx in final_ranked:
        row = df.iloc[idx]

        # skip already interacted movies
        if row['id'] in skip_ids:
            continue

        # apply filters if user selected them
        if content_type and row['content_type'] != content_type:
            continue
        if ott and row['ott_platform'] != ott:
            continue
        if watch_type and row['watch_type'] != watch_type:
            continue
        if category and row['category'] != category:
            continue
        if genre and genre.lower() not in row['genre'].lower():
            continue

        results.append(row.to_dict())

        if len(results) == 20:
            break

    return results


conn.close()  # close connection of sql file 