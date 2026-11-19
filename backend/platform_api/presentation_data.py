"""Five curated fictional profiles for presentations, never training/evaluation observations."""

from datetime import timedelta
from hashlib import sha256
from bson import ObjectId
from .common import now
from .serializers import ProfileSerializer, ProjectSerializer, EventSerializer

SOURCE = "presentation_v1"


def fixture_id(key):
    return ObjectId(sha256(("connect-presentation-v1:" + key).encode()).hexdigest()[:24])


PEOPLE = [
    {
        "key": "aarav",
        "name": "Aarav Sharma",
        "city": "Delhi",
        "domain": "AI / ML",
        "skills": ["Python", "Machine Learning", "Pandas", "Scikit-learn", "SQL", "Django"],
        "interests": ["AI", "Research", "Data Science", "Open Source", "Sustainability"],
        "bio": "I enjoy turning research ideas into useful Python applications. Looking for teammates to build practical AI tools. Fictional presentation profile.",
    },
    {
        "key": "priya",
        "name": "Priya Verma",
        "city": "Delhi",
        "domain": "AI / ML",
        "skills": ["Python", "Machine Learning", "Pandas", "Scikit-learn", "SQL", "NumPy"],
        "interests": ["AI", "Research", "Data Science", "Open Source", "Education"],
        "bio": "Interested in machine learning, learning tools and explainable recommendations. Fictional presentation profile.",
    },
    {
        "key": "rohan",
        "name": "Rohan Mehta",
        "city": "Delhi",
        "domain": "AI / ML",
        "skills": ["Python", "Machine Learning", "Pandas", "Scikit-learn", "SQL", "Git"],
        "interests": ["AI", "Research", "Data Science", "Open Source", "Community Service"],
        "bio": "I like analysing datasets and building clear, useful dashboards. Happy to collaborate on an AI project. Fictional presentation profile.",
    },
    {
        "key": "ananya",
        "name": "Ananya Iyer",
        "city": "Delhi",
        "domain": "Web Development",
        "skills": ["JavaScript", "React", "HTML", "CSS", "Git"],
        "interests": [
            "UI/UX",
            "Web Development",
            "Accessibility",
            "Gardening",
            "Environmental Conservation",
            "Sustainability",
        ],
        "preferred_project_type": "Web Application",
        "organization_name": "Green Together Club",
        "bio": "Frontend developer interested in accessible design and greener neighbourhoods. Fictional presentation profile.",
    },
    {
        "key": "kabir",
        "name": "Kabir Singh",
        "city": "Delhi",
        "domain": "Backend Development",
        "skills": ["Python", "Django", "REST API", "SQL", "Git"],
        "interests": [
            "Backend",
            "Open Source",
            "Cloud",
            "Community Service",
            "Food Donation",
            "Volunteering",
        ],
        "preferred_project_type": "Web Application",
        "bio": "Building reliable APIs and helping people coordinate local volunteering. Fictional presentation profile.",
    },
]

PROJECTS = [
    {
        "key": "study-buddy",
        "owner": "priya",
        "title": "StudyCircle AI",
        "description": "Build a study assistant that organises notes, suggests revision topics and explains its recommendations. Looking for Python and ML collaborators.",
        "required_skills": ["Python", "Machine Learning", "Pandas"],
        "required_interests": ["AI", "Research", "Education"],
    },
    {
        "key": "resume-insights",
        "owner": "aarav",
        "title": "Resume Insights",
        "description": "Create a tool that extracts skills from resumes and helps people discover relevant learning and collaboration opportunities.",
        "required_skills": ["Python", "Machine Learning", "Scikit-learn"],
        "required_interests": ["AI", "Research", "Open Source"],
    },
    {
        "key": "data-explorer",
        "owner": "rohan",
        "title": "Open Data Explorer",
        "description": "Make public datasets easier to explore with clean visualisations and reproducible ML experiments. Start with education and community datasets.",
        "required_skills": ["Python", "Pandas", "SQL"],
        "required_interests": ["Data Science", "Research", "Open Source"],
    },
    {
        "key": "green-together",
        "owner": "ananya",
        "title": "Green Together",
        "description": "Build an accessible website where neighbours organise plantation drives and share progress on their community gardens.",
        "required_skills": ["React", "HTML", "CSS"],
        "required_interests": ["Accessibility", "Web Development", "Sustainability"],
        "domain": "Web Development",
        "project_type": "Web Application",
    },
    {
        "key": "foodshare",
        "owner": "kabir",
        "title": "FoodShare Connect",
        "description": "Develop a Django API for food donation drives, volunteer sign-ups and collection schedules. Focus on clear workflows and reliable permissions.",
        "required_skills": ["Python", "Django", "REST API"],
        "required_interests": ["Backend", "Open Source", "Community Service"],
        "domain": "Backend Development",
        "project_type": "Web Application",
    },
]


def validated(serializer, values):
    result = serializer(data=values)
    result.is_valid(raise_exception=True)
    return dict(result.validated_data)


def build_fixtures():
    # Fictional UI fixtures only. Never read by the survey training pipeline.
    technology = {
        "aarav": {"languages": ["Python", "SQL"], "databases": ["PostgreSQL", "MongoDB"], "frameworks": ["Django"], "platforms": [], "wanted_languages": ["JavaScript", "Python"], "years_code": 3},
        "priya": {"languages": ["JavaScript", "HTML/CSS"], "databases": ["MongoDB"], "frameworks": ["React", "Node.js"], "platforms": [], "wanted_languages": ["Python", "JavaScript"], "years_code": 3},
        "rohan": {"languages": ["Python", "JavaScript", "SQL"], "databases": ["PostgreSQL"], "frameworks": ["Django", "React"], "platforms": [], "wanted_languages": ["Python", "JavaScript"], "years_code": None},
        "ananya": {"languages": ["JavaScript", "TypeScript", "HTML/CSS"], "databases": [], "frameworks": ["React"], "platforms": [], "wanted_languages": ["Python", "TypeScript"], "years_code": 2},
        "kabir": {"languages": ["Python", "SQL"], "databases": ["PostgreSQL"], "frameworks": ["Django"], "platforms": ["Amazon Web Services (AWS)"], "wanted_languages": ["Rust", "Go"], "years_code": 4},
    }
    people = []
    for person in PEOPLE:
        profile = validated(
            ProfileSerializer,
            {
                "branch": "Computer Science",
                "academic_year": 4,
                "experience": "Intermediate",
                "preferred_project_type": "AI/ML Application",
                "availability_hours": 8,
                "projects_completed": 2,
                **person,
                **technology[person["key"]],
                "community_interests": person["interests"],
            },
        )
        people.append(
            {"key": person["key"], "email": person["key"] + "@connect.example", "profile": profile}
        )
    projects = []
    for project in PROJECTS:
        values = validated(
            ProjectSerializer,
            {
                "domain": "AI / ML",
                "project_type": "AI/ML Application",
                "team_size": 4,
                "required_experience": "Intermediate",
                "expected_hours": 6,
                "deadline": now() + timedelta(days=45),
                **project,
            },
        )
        projects.append({"key": project["key"], "owner": project["owner"], "values": values})
    activities = [
        {
            "key": "plantation",
            "owner": "ananya",
            "values": validated(
                EventSerializer,
                {
                    "title": "Green Neighbourhood Plantation",
                    "description": "Join a community plantation and garden-care morning. Beginners welcome; bring water and comfortable shoes. Fictional presentation activity.",
                    "category": "Volunteer drive",
                    "interest_tags": ["Gardening", "Environmental Conservation", "Sustainability"],
                    "organization_name": "Green Together Club",
                    "city": "Delhi",
                    "location": "Community park, north gate",
                    "starts_at": now() + timedelta(days=4),
                    "participant_limit": 30,
                },
            ),
        },
        {
            "key": "food-drive",
            "owner": "kabir",
            "values": validated(
                EventSerializer,
                {
                    "title": "Neighbourhood Ration Drive",
                    "description": "Help pack and distribute ration kits with local volunteers. No organisation membership or special skills required. Fictional presentation activity.",
                    "category": "Volunteer drive",
                    "interest_tags": ["Community Service", "Food Donation", "Volunteering"],
                    "city": "Delhi",
                    "location": "Community centre, main entrance",
                    "starts_at": now() + timedelta(days=5),
                    "participant_limit": 20,
                },
            ),
        },
    ]
    return people, projects, activities
