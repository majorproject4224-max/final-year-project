"""End-to-end browser checks run in GitHub Actions, never on the office laptop."""

import json
import os
from io import BytesIO
from docx import Document
from PIL import Image, ImageDraw
from pypdf import PdfWriter
from pathlib import Path
from urllib.request import Request, urlopen
from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:5173"
API = "http://127.0.0.1:8000/api"
PASSWORD = os.environ["E2E_PASSWORD"]
OUT = Path("test-results")
OUT.mkdir(exist_ok=True)
PROFILE = {
    "name": "Dev Tester",
    "branch": "CSE",
    "academic_year": 3,
    "skills": ["Python", "ML", "Django", "React"],
    "interests": ["Research", "AI", "Open Source"],
    "domain": "AI / ML",
    "experience": "Intermediate",
    "preferred_project_type": "AI/ML Application",
    "availability_hours": 8,
}


def request(method, route, payload=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = json.dumps(payload).encode() if payload is not None else None
    with urlopen(
        Request(API + route, data=data, headers=headers, method=method), timeout=30
    ) as response:
        return json.load(response) if response.status != 204 else None


with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 1440, "height": 1050}, reduced_motion="reduce")
    context.tracing.start(screenshots=True, snapshots=True)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        dev = request(
            "POST",
            "/auth/register/",
            {"name": "Dev Tester", "email": "dev@browser.example", "password": PASSWORD},
        )
        token = dev["tokens"]["access"]
        request("PUT", "/profiles/me/", PROFILE, token)
        page.goto(BASE + "/register")
        page.screenshot(path=str(OUT / "register-desktop.png"), full_page=True)
        page.get_by_label("Your name").fill("Maya Tester")
        page.get_by_label("Email", exact=True).fill("maya@browser.example")
        page.get_by_label("Password", exact=True).fill(PASSWORD)
        page.get_by_role("button", name="Create account →", exact=True).click()
        expect(page.get_by_role("heading", name="Welcome, Maya")).to_be_visible(timeout=15000)
        page.get_by_role("link", name="My profile", exact=True).click()
        page.get_by_text("Import from Resume", exact=True).click()
        resume = Document()
        resume.add_paragraph("Maya Tester")
        resume.add_paragraph("Branch: CSE")
        resume.add_paragraph("Year: 3")
        resume.add_paragraph("Skills: Python, Django, React. Machine learning research internship.")
        resume_file = BytesIO()
        resume.save(resume_file)
        page.get_by_label("Choose Resume", exact=True).set_input_files(
            {
                "name": "demo-resume.docx",
                "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "buffer": resume_file.getvalue(),
            }
        )
        expect(page.get_by_role("heading", name="Review suggestions")).to_be_visible()
        page.get_by_role("button", name="Use these suggestions").click()
        expect(page.get_by_label("Skills, separated by commas")).to_have_value(
            "Python, React, Django, Machine Learning"
        )
        page.get_by_text("Import from Resume", exact=True).click()
        page.get_by_label("Skills, separated by commas").fill("Python, Django, ML, React")
        page.get_by_label("Interests, separated by commas").fill("Research, AI, Open Source")
        page.get_by_label("Experience", exact=True).select_option("Intermediate")
        page.get_by_label("Preferred project type").fill("AI/ML Application")
        page.get_by_role("button", name="Save profile", exact=True).click()
        expect(page.get_by_role("status")).to_contain_text("Profile saved")
        page.set_viewport_size({"width": 1280, "height": 720})
        page.evaluate("document.fonts.ready")
        page.get_by_role("button", name="Dismiss notification").click()
        page.evaluate("window.scrollTo(0, 0)")
        page.screenshot(path=str(OUT / "profile-desktop.png"), full_page=True)
        assert page.evaluate("document.fonts.check('14px Inter')"), "Inter font did not load"
        assert page.locator(".sidebar").evaluate("el => el.scrollHeight <= el.clientHeight"), (
            "Desktop sidebar should not need its own scrollbar at this viewport"
        )
        page.set_viewport_size({"width": 1440, "height": 1050})
        page.get_by_role("link", name="Overview", exact=True).click()
        expect(page.locator(".student-card").first).to_be_visible(timeout=15000)
        expect(page.locator(".model-note").first).to_contain_text("synthetic")
        expect(page.locator(".match-details .reasons").first).not_to_be_visible()
        page.locator(".match-details summary").first.click()
        expect(page.locator(".match-details .reasons").first).to_be_visible()
        if page.get_by_role("button", name="Dismiss notification").is_visible():
            page.get_by_role("button", name="Dismiss notification").click()
        page.screenshot(path=str(OUT / "dashboard-desktop.png"), full_page=True)
        page.get_by_role("button", name="Projects", exact=True).click()
        expect(page.locator(".project-card").first).to_be_visible()
        page.get_by_role("link", name="Students", exact=True).click()
        page.get_by_label("Search students").fill("Dev Tester")
        page.get_by_role("button", name="Search", exact=True).click()
        card = page.locator(".student-card").filter(has_text="Dev Tester")
        expect(card).to_be_visible()
        card.get_by_role("button", name="Connect", exact=True).click()
        expect(card.get_by_role("button", name="Request sent")).to_be_visible()
        incoming = request("GET", "/connections/", token=token)["items"][0]
        request("PATCH", "/connections/" + incoming["id"] + "/", {"action": "accept"}, token)
        page.get_by_role("link", name="Projects", exact=True).click()
        page.get_by_role("link", name="Create a project").click()
        page.get_by_label("Project title", exact=True).fill("Campus knowledge assistant")
        page.get_by_label("Description", exact=True).fill(
            "Build a campus assistant with real student collaborators."
        )
        page.get_by_label("Required skills, separated by commas").fill("Python, Django, React")
        page.get_by_label("Related interests, separated by commas").fill("Research, AI")
        page.get_by_label("Domain", exact=True).select_option("AI / ML")
        page.get_by_label("Project type", exact=True).fill("AI/ML Application")
        page.get_by_role("button", name="Create project", exact=True).click()
        expect(
            page.get_by_role("heading", name="Campus knowledge assistant", exact=True)
        ).to_be_visible()
        project_id = page.url.rstrip("/").split("/")[-1]
        request("POST", "/projects/" + project_id + "/applications/", {}, token)
        page.reload()
        applications = page.locator("section.card").filter(
            has=page.get_by_role("heading", name="Applications", exact=True)
        )
        applications.get_by_role("button", name="Accept", exact=True).click()
        expect(page.get_by_role("heading", name="The team 2/4")).to_be_visible()
        page.screenshot(path=str(OUT / "project-team.png"), full_page=True)
        page.get_by_role("link", name="Connections", exact=True).click()
        page.get_by_role("button", name="Message", exact=True).click()
        expect(page.locator(".chat-panel header")).to_contain_text("Live", timeout=15000)
        page.get_by_label("Message", exact=True).fill("Ready to build together?")
        page.get_by_role("button", name="Send", exact=True).click()
        expect(page.locator(".message")).to_contain_text("Ready to build together?")
        conversation = request("GET", "/conversations/", token=token)["items"][0]
        other_context = browser.new_context()
        other_page = other_context.new_page()
        other_page.goto(BASE + "/login")
        other_page.get_by_label("Email", exact=True).fill("dev@browser.example")
        other_page.get_by_label("Password", exact=True).fill(PASSWORD)
        other_page.get_by_role("button", name="Sign in →", exact=True).click()
        expect(other_page.get_by_role("heading", name="Welcome, Dev")).to_be_visible()
        other_page.goto(BASE + "/chat/" + conversation["id"])
        expect(other_page.locator(".chat-panel header")).to_contain_text("Live")
        expect(other_page.locator(".message")).to_contain_text("Ready to build together?")
        expect(page.locator(".message small")).to_contain_text("Read")
        other_page.get_by_label("Message", exact=True).fill("Yes, let's plan the first milestone.")
        other_page.get_by_role("button", name="Send", exact=True).click()
        expect(page.locator(".message").last).to_contain_text("first milestone")
        # Send files through the actual browser, and deliberately lose the HTTP response.
        # A retry must reuse the client identifier without duplicating the saved message.
        sketch = Image.new("RGB", (640, 320), "#eaf5f0")
        drawing = ImageDraw.Draw(sketch)
        drawing.rounded_rectangle((40, 50, 600, 270), radius=20, fill="white", outline="#15795b", width=3)
        drawing.text((75, 85), "CAMPUS KNOWLEDGE ASSISTANT", fill="#173f32", font_size=24)
        drawing.text((75, 140), "Students  >  Shared ideas  >  Project team", fill="#526c62", font_size=18)
        drawing.text((75, 200), "First milestone: design the project dashboard", fill="#526c62", font_size=16)
        sketch_file = BytesIO()
        sketch.save(sketch_file, format="PNG")
        notes = b"Milestone 1: build the dashboard.\nMilestone 2: review together.\n"
        page.get_by_label("Attach files", exact=True).set_input_files([
            {"name": "project-sketch.png", "mimeType": "image/png", "buffer": sketch_file.getvalue()},
            {"name": "project-notes.txt", "mimeType": "text/plain", "buffer": notes},
        ])
        expect(page.get_by_role("list", name="Files to send")).to_contain_text("project-sketch.png")
        expect(page.locator(".draft-attachments img")).to_be_visible()
        page.get_by_role("button", name="Remove project-notes.txt", exact=True).click()
        expect(page.get_by_role("list", name="Files to send")).not_to_contain_text("project-notes.txt")
        page.get_by_label("Attach files", exact=True).set_input_files(
            {"name": "project-notes.txt", "mimeType": "text/plain", "buffer": notes}
        )
        page.get_by_label("Message", exact=True).fill("Here is the project sketch and our notes.")

        def lose_upload_response(route):
            if route.request.method == "POST":
                response = route.fetch()
                assert response.status == 201, response.text()
                route.abort("failed")
            else:
                route.continue_()

        page.route("**/api/conversations/*/messages/", lose_upload_response)
        page.get_by_role("button", name="Send", exact=True).click()
        expect(page.get_by_role("button", name="Send", exact=True)).to_be_enabled()
        expect(page.get_by_role("list", name="Files to send")).to_be_visible()
        page.unroute("**/api/conversations/*/messages/", lose_upload_response)
        page.get_by_role("button", name="Send", exact=True).click()
        expect(page.get_by_role("list", name="Files to send")).to_have_count(0)
        received = other_page.locator(".message").filter(has_text="Here is the project sketch and our notes.")
        expect(received).to_have_count(1)
        expect(page.locator(".message").filter(has_text="Here is the project sketch and our notes.")).to_have_count(1)
        image_preview = received.get_by_role("img", name="project-sketch.png", exact=True)
        expect(image_preview).to_be_visible(timeout=15000)
        expect(image_preview).to_have_js_property("naturalWidth", 640)
        received.get_by_role("button", name="Open image project-sketch.png").click()
        expect(other_page.get_by_role("dialog")).to_be_visible()
        other_page.keyboard.press("Escape")
        expect(other_page.get_by_role("dialog")).to_have_count(0)
        with other_page.expect_download() as download_info:
            received.get_by_role("button", name="Download project-notes.txt").click()
        downloaded = download_info.value
        assert downloaded.suggested_filename == "project-notes.txt"
        assert Path(downloaded.path()).read_bytes() == notes
        pdf = BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=300, height=200)
        writer.write(pdf)
        other_page.get_by_label("Attach files", exact=True).set_input_files(
            {"name": "project-outline.pdf", "mimeType": "application/pdf", "buffer": pdf.getvalue()}
        )
        other_page.get_by_role("button", name="Send", exact=True).click()
        expect(page.locator(".message").last).to_contain_text("project-outline.pdf")
        page.reload()
        expect(page.locator(".chat-panel header")).to_contain_text("Live")
        expect(page.locator(".message").last).to_contain_text("project-outline.pdf")
        page.locator(".message").filter(has_text="Here is the project sketch and our notes.").scroll_into_view_if_needed()
        expect(page.get_by_role("img", name="project-sketch.png", exact=True)).to_be_visible()
        page.screenshot(path=str(OUT / "chat-desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        expect(page.get_by_role("button", name="Add files or images")).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Mobile chat horizontal overflow"
        page.screenshot(path=str(OUT / "chat-mobile.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 1050})
        page.get_by_role("link", name="Events", exact=True).click()
        page.get_by_role("button", name="Create an event").click()
        page.get_by_label("Event title").fill("Campus demo day")
        page.get_by_label("Description", exact=True).fill("Share student projects.")
        page.get_by_label("Location or meeting link").fill("Seminar hall")
        page.get_by_label("Date and time").fill("2030-03-15T14:00")
        page.get_by_role("button", name="Create event", exact=True).click()
        expect(page.get_by_role("heading", name="Campus demo day")).to_be_visible()
        page.get_by_role("button", name="I'll be there", exact=True).click()
        expect(page.locator(".event-card")).to_contain_text("1 attending")
        page.goto(BASE)
        expect(page.locator(".student-card").first).to_be_visible()
        page.set_viewport_size({"width": 390, "height": 844})
        expect(page.get_by_role("button", name="Toggle navigation")).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
            "Mobile horizontal overflow"
        )
        page.screenshot(path=str(OUT / "dashboard-mobile.png"), full_page=True)
        page.get_by_role("button", name="Toggle navigation").click()
        page.get_by_role("link", name="My space", exact=True).click()
        expect(page.get_by_role("heading", name="My space", exact=True)).to_be_visible()
        page.get_by_role("button", name="Toggle navigation").click()
        page.get_by_role("link", name="My profile", exact=True).click()
        page.get_by_text("Import from Resume", exact=True).click()
        expect(page.get_by_label("Choose Resume", exact=True)).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
            "Mobile profile horizontal overflow"
        )
        page.screenshot(path=str(OUT / "profile-mobile.png"), full_page=True)
        page.get_by_role("button", name="Toggle navigation").click()
        page.keyboard.press("Escape")
        expect(page.get_by_role("button", name="Toggle navigation")).to_be_focused()
        expect(page.get_by_role("link", name="My profile", exact=True)).not_to_be_visible()
        assert not errors, errors
        print(
            "Browser journey passed: registration, profile, ML recommendations, connections, project applications, teams, two-user live chat, image/file uploads, private previews/downloads, retry deduplication, persistent attachment history, read receipts, events and mobile navigation."
        )
    except Exception:
        page.screenshot(path=str(OUT / "failure.png"), full_page=True)
        raise
    finally:
        context.tracing.stop(path=str(OUT / "browser-trace.zip"))
        browser.close()
