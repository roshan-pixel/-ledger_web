from playwright.sync_api import Page, expect
import re

def test_god_mode_title(page: Page):
    """
    Opens the God Mode application and checks that the title is present.
    """
    page.goto("http://127.0.0.1:5000")
    
    # Check that the title contains at least one character
    expect(page).to_have_title(re.compile(r".+"))
