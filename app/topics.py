"""Topic bank for stage 01. Six categories x three difficulties (all original motions)."""
import random

CATEGORIES = {
    "technology":  ("💻", "Technology"),
    "education":   ("🎓", "Education"),
    "politics":    ("🏛️", "Politics"),
    "science":     ("🔬", "Science"),
    "environment": ("🌿", "Environment"),
    "society":     ("🤝", "Society"),
}
DIFFICULTIES = {
    "beginner":     "Short motions with everyday evidence.",
    "intermediate": "Needs a warrant and a qualified claim.",
    "advanced":     "Competing values; expect hard rebuttals.",
}

TOPICS = {
 "technology": {
  "beginner": ["Smartphones should be banned in school classrooms.",
               "Social media does more harm than good for teenagers."],
  "intermediate": ["Governments should require human review of AI decisions about people.",
                   "Remote work should become the default for office jobs."],
  "advanced": ["Open-sourcing powerful AI models does more good than harm.",
               "Platforms, not users, should be liable for algorithmic amplification."]},
 "education": {
  "beginner": ["Homework should be abolished in primary schools.",
               "School uniforms should be compulsory."],
  "intermediate": ["University education should be free for all citizens.",
                   "Exams should be replaced by continuous assessment."],
  "advanced": ["Standardised testing entrenches inequality more than it measures merit.",
               "AI tutors should replace the lecture as the main mode of teaching."]},
 "politics": {
  "beginner": ["Voting should be compulsory.",
               "The voting age should be lowered to 16."],
  "intermediate": ["Term limits should apply to all elected legislators.",
                   "Public broadcasters deserve public funding."],
  "advanced": ["Majority rule is an insufficient basis for legitimate government.",
               "Wealthy states owe climate reparations to poorer ones."]},
 "science": {
  "beginner": ["Space exploration is worth its cost.",
               "Zoos do more good than harm for wildlife."],
  "intermediate": ["Animal testing should be phased out where alternatives exist.",
                   "Gene editing of human embryos should be permitted for serious disease."],
  "advanced": ["Scientific research should be steered by public need rather than curiosity.",
               "Preprints should replace journal peer review."]},
 "environment": {
  "beginner": ["Plastic bags should be banned.",
               "Cities should ban cars from their centres."],
  "intermediate": ["A carbon tax is the best tool against climate change.",
                   "Nuclear power should be expanded."],
  "advanced": ["Economic growth is incompatible with environmental sustainability.",
               "Individuals' lifestyle changes matter more than industrial regulation."]},
 "society": {
  "beginner": ["Everyone should do a year of national service.",
               "Celebrities have a duty to be role models."],
  "intermediate": ["A universal basic income would improve social welfare.",
                   "Anonymous speech online should be restricted."],
  "advanced": ["Privacy is a luxury a connected society can no longer afford.",
               "Meritocracy is a myth that justifies inequality."]},
}


def pick(category: str, difficulty: str, rng=None, exclude=()):
    """Return a topic; avoids `exclude` (recent topics) when possible."""
    rng = rng or random
    pool = TOPICS[category][difficulty]
    fresh = [t for t in pool if t not in exclude] or pool
    return rng.choice(fresh)


def validate(category: str, difficulty: str):
    if category not in TOPICS or difficulty not in DIFFICULTIES:
        raise ValueError("unknown category or difficulty")