"""Check the actual curated presentation accounts and capture the indigo theme in CI."""

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from playwright.sync_api import sync_playwright, expect

BASE = os.getenv("E2E_BASE_URL", "http://127.0.0.1:5173")
API = os.getenv("E2E_API_URL", "http://127.0.0.1:8000/api")
OUT = Path("test-results")
PASSWORD = os.environ["E2E_PASSWORD"]


def login(page, email):
    page.goto(BASE + "/login")
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Password", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Sign in →", exact=True).click()


with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 1440, "height": 1050}, reduced_motion="reduce")
    context.tracing.start(screenshots=True, snapshots=True)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(BASE + "/login")
        page.screenshot(path=str(OUT / "presentation-login.png"), full_page=True)
        login(page, "aarav@connect.example")
        expect(page.get_by_role("heading", name="Welcome, Aarav")).to_be_visible()
        rohan = page.locator(".student-card").filter(has_text="Rohan Mehta")
        expect(rohan).to_be_visible()
        expect(page.locator(".student-card").filter(has_text="Priya Verma")).to_have_count(0)
        rohan.locator(".match-details summary").click()
        expect(rohan.locator(".reasons")).to_contain_text("python")
        expect(
            page.locator(".activity-card").filter(has_text="Green Neighbourhood Plantation")
        ).to_be_visible()
        page.screenshot(path=str(OUT / "presentation-dashboard.png"), full_page=True)
        page.get_by_role("button", name="Projects", exact=True).click()
        study = page.locator(".project-card").filter(has_text="StudyCircle AI")
        expect(study).to_be_visible()
        page.screenshot(path=str(OUT / "presentation-project-matches.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        expect(page.locator(".sidebar")).not_to_be_in_viewport()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
            "Presentation dashboard overflows on mobile"
        )
        page.screenshot(path=str(OUT / "presentation-mobile.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 1050})
        page.get_by_role("link", name="Connections", exact=True).click()
        expect(page.get_by_text("Priya Verma", exact=True)).to_be_visible()
        page.get_by_role("button", name="Message", exact=True).click()
        expect(page.locator(".chat-panel header")).to_contain_text("Live")
        chat_url = page.url
        second = browser.new_context(
            viewport={"width": 1440, "height": 1050}, reduced_motion="reduce"
        )
        peer = second.new_page()
        peer.on("pageerror", lambda error: errors.append(str(error)))
        login(peer, "priya@connect.example")
        expect(peer.get_by_role("heading", name="Welcome, Priya")).to_be_visible()
        peer.goto(chat_url)
        expect(peer.locator(".chat-panel header")).to_contain_text("Live")
        page.get_by_label("Message", exact=True).fill(
            "Hi Priya, shall we review StudyCircle AI together?"
        )
        page.get_by_role("button", name="Send", exact=True).click()
        expect(peer.locator(".message").last).to_contain_text("review StudyCircle AI")
        peer.get_by_label("Message", exact=True).fill(
            "Yes! I can work on the recommendation pipeline."
        )
        peer.get_by_role("button", name="Send", exact=True).click()
        expect(page.locator(".message").last).to_contain_text("recommendation pipeline")
        page.screenshot(path=str(OUT / "presentation-chat.png"), full_page=True)
        page.get_by_role("link", name="Events", exact=True).click()
        expect(page.get_by_role("heading", name="Events & activities")).to_be_visible()
        expect(
            page.locator(".activity-card").filter(has_text="Neighbourhood Ration Drive")
        ).to_be_visible()
        page.screenshot(path=str(OUT / "presentation-activities.png"), full_page=True)
        # Exercise real API login and recommendations without saving access tokens to artifacts.
        data = json.dumps({"email": "aarav@connect.example", "password": PASSWORD}).encode()
        with urlopen(
            Request(API + "/auth/login/", data=data, headers={"Content-Type": "application/json"}),
            timeout=30,
        ) as response:
            access = json.load(response)["tokens"]["access"]
        with urlopen(
            Request(API + "/recommendations/users/", headers={"Authorization": "Bearer " + access}),
            timeout=30,
        ) as response:
            recommendations = json.load(response)
        print(
            "Measured presentation recommendation:",
            [
                {"name": item["name"], "score": item["match_score"]}
                for item in recommendations["items"]
            ],
        )
        assert not errors, errors
        print(
            "Presentation checks passed: real ML match, project match, ready connection, two-account live chat, activities and mobile layout."
        )
    except Exception:
        page.screenshot(path=str(OUT / "presentation-failure.png"), full_page=True)
        raise
    finally:
        context.tracing.stop(path=str(OUT / "presentation-trace.zip"))
        browser.close()
