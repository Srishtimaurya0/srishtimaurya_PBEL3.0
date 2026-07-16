from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def calculate_similarity(resume, job):

    vectorizer = TfidfVectorizer()

    vectors = vectorizer.fit_transform([resume, job])

    score = cosine_similarity(vectors[0], vectors[1])

    return score[0][0]