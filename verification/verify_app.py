from playwright.sync_api import sync_playwright, expect

def run_verification(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    try:
        # Step 1: Go to the main page and take a screenshot
        page.goto("http://127.0.0.1:5000")
        page.screenshot(path="verification/01_main_page.png")
        print("Captured 01_main_page.png")

        # Step 2: Fill out the form and create an offer
        page.locator("#original_price").fill("150")
        page.locator("#discount_percentage").fill("50")
        page.locator("button[type='submit']").click()

        # Wait for navigation to the offer page
        page.wait_for_url("**/offer/**")

        # Step 3: Take a screenshot of the offer page
        page.screenshot(path="verification/02_offer_page.png")
        print("Captured 02_offer_page.png")

        # Verify some content on the offer page
        expect(page.locator(".new-price")).to_have_text("$75.00")
        expect(page.locator(".guarantee")).to_be_visible()

        # Step 4: Click the claim button to go to the business owner page
        page.locator(".claim-button").click()

        # Wait for navigation to the claim page
        page.wait_for_url("**/claim/**")

        # Step 5: Take a screenshot of the claim page
        page.screenshot(path="verification/03_claim_page.png")
        print("Captured 03_claim_page.png")

        # Verify some content on the claim page
        expect(page.locator("h1")).to_have_text("Unlock Your Revenue Growth!")

        print("\nVerification successful!")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please check the Flask server logs in flask.log")

    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run_verification(playwright)
