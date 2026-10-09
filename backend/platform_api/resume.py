import re
from io import BytesIO

from docx import Document
from pypdf import PdfReader


MAX_RESUME_BYTES = 5 * 1024 * 1024
SKILLS = [
    "Python", "Java", "C++", "C", "JavaScript", "TypeScript", "HTML", "CSS",
    "React", "Node.js", "Flask", "Django", "SQL", "MySQL", "MongoDB",
    "Firebase", "Git", "GitHub", "Docker", "AWS", "Machine Learning",
    "Deep Learning", "Pandas", "NumPy", "Scikit-learn", "Power BI", "Tableau",
    "UI/UX", "Kotlin", "Android", "Cybersecurity",
]
DOMAIN_TERMS = {
    "AI / ML": ["machine learning", "deep learning", "artificial intelligence", "scikit-learn"],
    "Data Science": ["data science", "data analysis", "power bi", "tableau", "pandas"],
    "Web Development": ["web development", "react", "javascript", "html", "css"],
    "Mobile Development": ["android", "kotlin", "flutter", "mobile app"],
    "Backend Development": ["backend", "api", "flask", "django", "node.js"],
    "Cybersecurity": ["cybersecurity", "security", "penetration testing", "network security"],
}


def extract_resume(upload):
    filename = (getattr(upload, "filename", None) or getattr(upload, "name", "")).casefold()
    if not filename.endswith((".pdf", ".docx")):
        raise ValueError("Upload a PDF or DOCX resume.")
    data = upload.read(MAX_RESUME_BYTES + 1)
    if len(data) > MAX_RESUME_BYTES:
        raise ValueError("Resume must be 5 MB or smaller.")
    try:
        if filename.endswith(".pdf"):
            text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(data)).pages)
        else:
            text = "\n".join(paragraph.text for paragraph in Document(BytesIO(data)).paragraphs)
    except Exception as error:
        raise ValueError("We could not read that resume. Try a text-based PDF or DOCX file.") from error
    if len(text.strip()) < 20:
        raise ValueError("No readable text was found. Scanned image PDFs need OCR before they can be used.")

    lower = re.sub(r"\s+", " ", text).casefold()
    skills = [
        skill for skill in SKILLS
        if re.search(r"(?<![\w+])" + re.escape(skill.casefold()) + r"(?![\w+])", lower)
    ]
    domain_scores = {domain: sum(term in lower for term in terms) for domain, terms in DOMAIN_TERMS.items()}
    domain = max(domain_scores, key=domain_scores.get) if max(domain_scores.values()) else ""

    name = ""
    for line in text.splitlines()[:6]:
        candidate = re.sub(r"[^A-Za-z .-]", "", line).strip()
        if 2 <= len(candidate.split()) <= 5 and not any(
            term in candidate.casefold() for term in ("resume", "curriculum", "profile")
        ):
            name = candidate
            break

    year_match = re.search(
        r"(?i)\b(?:academic\s+)?year\s*[:\-]?\s*([1-4])\b|\b([1-4])(?:st|nd|rd|th)\s+year\b",
        text,
    )
    branch_match = re.search(
        r"(?im)^\s*(?:branch|department|major)\s*[:\-]\s*(.{2,80}?)\s*$", text
    )
    phone_match = re.search(r"(?<!\d)(?:\+?91[- ]?)?[6-9]\d{9}(?!\d)", text)
    github_match = re.search(r"https?://(?:www\.)?github\.com/[A-Za-z0-9_.-]+", text, re.I)
    interests = [
        label for label, terms in {
            "AI": ["artificial intelligence", "machine learning"],
            "Analytics": ["analytics", "data analysis", "power bi"],
            "Research": ["research"],
            "Open Source": ["open source"],
            "UI/UX": ["ui/ux", "user experience"],
            "Cybersecurity": ["cybersecurity", "security"],
        }.items()
        if any(term in lower for term in terms)
    ]
    project_type = {
        "AI / ML": "AI/ML Application", "Data Science": "Data Analysis",
        "Web Development": "Web Application", "Mobile Development": "Mobile Application",
        "Backend Development": "Backend Service", "Cybersecurity": "Security Tool",
    }.get(domain, "")
    experience = (
        "Advanced" if re.search(r"(?i)\b(?:[2-9]|two|three)\+?\s*years?\b", lower)
        else "Intermediate" if any(term in lower for term in ("internship", "intern", "freelance"))
        else ""
    )
    return {
        "name": name,
        "branch": branch_match.group(1).strip().title() if branch_match else "",
        "academic_year": next((part for part in year_match.groups() if part), "") if year_match else "",
        "skills": skills,
        "interests": interests,
        "domain": domain,
        "experience": experience,
        "preferred_project_type": project_type,
        "city": "",
        "phone": phone_match.group(0) if phone_match else "",
        "github": github_match.group(0) if github_match else "",
    }