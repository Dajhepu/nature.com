import time
from playwright.sync_api import sync_playwright, expect

def run_verification(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    # Use a unique email for each run to avoid registration conflicts
    unique_email = f"user_{int(time.time())}@example.com"

    try:
        # --- 1. Registration ---
        print("Navigating to registration page...")
        page.goto("http://127.0.0.1:5000/register")
        page.screenshot(path="verification/01_register_page.png")

        print(f"Registering with email: {unique_email}")
        page.locator("#email").fill(unique_email)
        page.locator("#password").fill("password123")
        page.locator("button[type='submit']").click()

        # Wait for success message and redirection
        expect(page.locator("#message")).to_have_text("User registered successfully.", timeout=5000)
        page.wait_for_url("**/login")
        print("Registration successful.")

        # --- 2. Login ---
        print("Verifying login page...")
        page.screenshot(path="verification/02_login_page.png")

        print("Logging in...")
        page.locator("#email").fill(unique_email)
        page.locator("#password").fill("password123")
        page.locator("button[type='submit']").click()

        # Wait for success message and redirection
        expect(page.locator("#message")).to_have_text("Login successful.", timeout=5000)
        page.wait_for_url("**/create_offer")
        print("Login successful.")

        # --- 3. Offer Creation ---
        print("Verifying offer creation page...")
        page.screenshot(path="verification/03_create_offer_page.png")

        print("Creating an offer...")
        page.locator("#original_price").fill("250.50")
        page.locator("#discount_percent").fill("25")
        page.locator("button[type='submit']").click()

        # Wait for success message and redirection to the certificate
        expect(page.locator("#message")).to_have_text("Offer created successfully.", timeout=5000)
        page.wait_for_url("**/offer/**")
        print("Offer creation successful.")

        # --- 4. Certificate Verification ---
        print("Verifying offer certificate page...")
        page.screenshot(path="verification/04_certificate_page.png")

        # Check for key details on the certificate
        expect(page.locator(".price-box .strikethrough")).to_have_text("$250.50")
        expect(page.locator(".price-box .amount").last).to_have_text("$187.88") # 250.50 * 0.75
        expect(page.locator(".qr-code img")).to_be_visible()
        print("Certificate details are correct.")

        print("\n--- Full MVP Flow Verification Successful! ---")

    except Exception as e:
        print(f"\n--- An error occurred during verification ---")
        print(e)
        page.screenshot(path="verification/error.png")
        print("An error screenshot has been saved to verification/error.png")

    finally:
        browser.close()
        print("Browser closed.")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run_verification(playwright)
