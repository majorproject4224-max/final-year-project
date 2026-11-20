"""Real browser evidence for survey fields, measured results and safe cold start.

All displayed accounts are fictional test fixtures in the disposable browser DB.
"""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from playwright.sync_api import sync_playwright, expect

BASE = os.getenv("E2E_BASE_URL", "http://127.0.0.1:5173")
API = os.getenv("E2E_API_URL", "http://127.0.0.1:8000/api")
PASSWORD = os.environ["E2E_PASSWORD"]
OUT = Path("test-results/survey-ui")
OUT.mkdir(parents=True, exist_ok=True)


def request(method, route, data=None, access=None):
    headers = {"Content-Type": "application/json"}
    if access:
        headers["Authorization"] = "Bearer " + access
    with urlopen(Request(API + route, data=json.dumps(data).encode() if data is not None else None, headers=headers, method=method), timeout=30) as response:
        return json.load(response)


def login(page, email):
    page.goto(BASE + "/login")
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Password", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Sign in →", exact=True).click()


with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    login(page, "aarav@connect.example")
    expect(page.get_by_role("heading", name="Welcome, Aarav")).to_be_visible()
    expect(page.locator(".student-card").first).to_be_visible()
    page.locator(".student-card .match-details summary").first.click()
    expect(page.locator(".student-card .reasons").first).to_contain_text("You want to use; they have used")
    expect(page.get_by_text("Learning exchange in both directions", exact=True)).to_have_count(0)
    expect(page.get_by_text("They want to use; you have used", exact=False)).to_have_count(0)
    page.screenshot(path=str(OUT / "dashboard-people.png"), full_page=True)
    page.goto(BASE + "/profile")
    expect(page.get_by_label("Languages you have used")).to_have_value("python, sql")
    expect(page.get_by_label("Academic year", exact=True)).to_have_count(0)
    page.screenshot(path=str(OUT / "survey-profile.png"), full_page=True)
    page.goto(BASE + "/method")
    expect(page.get_by_role("heading", name="Real data. Explainable discovery.")).to_be_visible()
    expect(page.get_by_text("65,437", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="70% for learning, 30% for testing")).to_be_visible()
    expect(page.get_by_text("The five presentation profiles and all newly registered accounts", exact=False)).to_be_visible()
    page.screenshot(path=str(OUT / "measured-method.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Method page overflows on mobile"
    page.screenshot(path=str(OUT / "method-mobile.png"), full_page=True)

    account = request("POST", "/auth/register/", {"name": "Empty Profile Example", "email": "nullcase@browser.example", "password": PASSWORD})
    token = account["tokens"]["access"]
    empty = {"name": "Empty Profile Example", "languages": None, "databases": None, "frameworks": None, "platforms": None, "wanted_languages": None, "years_code": None}
    saved = request("PUT", "/profiles/me/", empty, token)
    assert saved["languages"] == [] and saved["years_code"] is None
    response = request("GET", "/recommendations/users/", access=token)
    assert response["items"] == [] and "Add technologies" in response["detail"]
    try:
        request("PUT", "/profiles/me/", {**empty, "years_code": -5}, token)
        raise AssertionError("Negative coding years accepted")
    except HTTPError as error:
        assert error.code == 400
    second = browser.new_context(viewport={"width": 1440, "height": 1000})
    blank = second.new_page()
    login(blank, "nullcase@browser.example")
    expect(blank.get_by_text("Add technologies you have used in My profile. Empty or unsupported profiles do not receive ML scores.", exact=True)).to_be_visible()
    blank.screenshot(path=str(OUT / "empty-profile-behavior.png"), full_page=True)
    assert not errors, errors
    browser.close()
print("Survey UI, people recommendation explanations, measured results, mobile layout, null fields and invalid-number rejection passed.")
