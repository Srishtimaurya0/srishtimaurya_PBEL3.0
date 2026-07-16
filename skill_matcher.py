import re


def extract_skills(text):
    """
    Extracts skills from the given text using whole-word / whole-phrase
    matching (word boundaries), instead of plain substring matching.

    Plain substring matching (e.g. `"c" in text`) is unreliable because
    a single-letter skill like "c" would match inside words such as
    "certificate", "science", "excel", "communication", etc. Using
    word-boundary based regex matching avoids these false positives.
    """

    skills = [
        "python", "java", "c", "c++", "sql", "html", "css",
        "javascript", "pandas", "numpy", "machine learning",
        "deep learning", "nlp", "tensorflow", "pytorch",
        "opencv", "excel", "power bi", "tableau",
        "communication", "teamwork", "leadership", "git", "github"
    ]

    text = text.lower()

    found_skills = []
    for skill in skills:
        # Match the skill only as a standalone word/phrase.
        # (?<![a-z0-9]) / (?![a-z0-9]) act as boundaries that also work
        # correctly for skills containing symbols like "c++".
        pattern = r'(?<![a-z0-9])' + re.escape(skill) + r'(?![a-z0-9])'
        if re.search(pattern, text):
            found_skills.append(skill)

    return sorted(set(found_skills))


def analyze_resume_strength(resume_text):

    text = resume_text.lower()

    sections = {
        "Education": [
            "education", "b.tech", "btech", "bachelor",
            "master", "degree", "university", "college"
        ],

        "Experience": [
            "experience", "worked", "employment",
            "company", "internship", "intern"
        ],

        "Projects": [
            "project", "projects", "developed",
            "implemented", "built"
        ],

        "Certifications": [
            "certificate", "certification",
            "certified", "coursera", "nptel", "udemy"
        ],

        "Skills": [
            "skills", "python", "java", "sql",
            "machine learning", "excel", "power bi"
        ]
    }

    found = []
    missing = []

    for section, keywords in sections.items():

        if any(keyword in text for keyword in keywords):
            found.append(section)
        else:
            missing.append(section)

    return found, missing