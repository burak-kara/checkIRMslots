#!/usr/bin/env python3
"""
Debug script to inspect easydoct.com page structure.
This helps identify the correct selectors for automated login.
"""

import os
import sys
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def inspect_page(url, headless=False):
    """Inspect the page and save information for debugging."""

    # Determine output directory (same as script location)
    script_dir = Path(__file__).parent
    output_dir = script_dir

    # Setup Chrome options
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")

    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    try:
        print(f"Opening browser and navigating to: {url}")
        driver = webdriver.Chrome(options=chrome_options)

        print(f"Loading URL...")
        try:
            driver.get(url)
        except Exception as e:
            print(f"Warning: Exception during navigation: {e}")

        # Wait for page to load
        print(f"Waiting for page to load...")
        time.sleep(5)

        print(f"\n{'='*60}")
        print("PAGE INFORMATION")
        print(f"{'='*60}")
        print(f"Current URL: {driver.current_url}")
        print(f"Page Title: {driver.title}")

        # Save page source
        page_source_path = output_dir / 'page_source.html'
        with open(page_source_path, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print(f"\n✓ Page source saved to: {page_source_path}")

        # Take screenshot
        screenshot_path = output_dir / 'page_screenshot.png'
        driver.save_screenshot(str(screenshot_path))
        print(f"✓ Screenshot saved to: {screenshot_path}")

        # Look for common login form elements
        print(f"\n{'='*60}")
        print("SEARCHING FOR LOGIN ELEMENTS")
        print(f"{'='*60}")

        # Try to find email/username input
        email_selectors = [
            ("ID 'Email'", By.ID, "Email"),
            ("ID 'email'", By.ID, "email"),
            ("NAME 'Email'", By.NAME, "Email"),
            ("NAME 'email'", By.NAME, "email"),
            ("input[type='email']", By.CSS_SELECTOR, "input[type='email']"),
            ("input[name*='mail']", By.CSS_SELECTOR, "input[name*='mail']"),
            ("input[id*='mail']", By.CSS_SELECTOR, "input[id*='mail']"),
        ]

        print("\nSearching for email/username input:")
        found_email = False
        for desc, by, selector in email_selectors:
            try:
                elements = driver.find_elements(by, selector)
                if elements:
                    print(f"  ✓ Found via {desc}: {len(elements)} element(s)")
                    for idx, elem in enumerate(elements[:3]):  # Show first 3
                        print(f"    - Element {idx+1}: tag={elem.tag_name}, id={elem.get_attribute('id')}, name={elem.get_attribute('name')}, class={elem.get_attribute('class')}")
                    found_email = True
            except Exception as e:
                pass

        if not found_email:
            print("  ✗ No email input found")

        # Try to find password input
        password_selectors = [
            ("ID 'Password'", By.ID, "Password"),
            ("ID 'password'", By.ID, "password"),
            ("NAME 'Password'", By.NAME, "Password"),
            ("NAME 'password'", By.NAME, "password"),
            ("input[type='password']", By.CSS_SELECTOR, "input[type='password']"),
        ]

        print("\nSearching for password input:")
        found_password = False
        for desc, by, selector in password_selectors:
            try:
                elements = driver.find_elements(by, selector)
                if elements:
                    print(f"  ✓ Found via {desc}: {len(elements)} element(s)")
                    for idx, elem in enumerate(elements[:3]):
                        print(f"    - Element {idx+1}: tag={elem.tag_name}, id={elem.get_attribute('id')}, name={elem.get_attribute('name')}, class={elem.get_attribute('class')}")
                    found_password = True
            except Exception as e:
                pass

        if not found_password:
            print("  ✗ No password input found")

        # Try to find submit button
        button_selectors = [
            ("button[type='submit']", By.CSS_SELECTOR, "button[type='submit']"),
            ("input[type='submit']", By.CSS_SELECTOR, "input[type='submit']"),
            ("TAG 'button'", By.TAG_NAME, "button"),
            (".btn-login", By.CSS_SELECTOR, ".btn-login"),
            (".login-button", By.CSS_SELECTOR, ".login-button"),
        ]

        print("\nSearching for submit/login button:")
        found_button = False
        for desc, by, selector in button_selectors:
            try:
                elements = driver.find_elements(by, selector)
                if elements:
                    print(f"  ✓ Found via {desc}: {len(elements)} element(s)")
                    for idx, elem in enumerate(elements[:3]):
                        text = elem.text or elem.get_attribute('value') or '[no text]'
                        print(f"    - Element {idx+1}: tag={elem.tag_name}, text='{text}', id={elem.get_attribute('id')}, class={elem.get_attribute('class')}")
                    found_button = True
            except Exception as e:
                pass

        if not found_button:
            print("  ✗ No submit button found")

        # Search for forms
        print(f"\n{'='*60}")
        print("FORMS ON PAGE")
        print(f"{'='*60}")
        forms = driver.find_elements(By.TAG_NAME, "form")
        if forms:
            print(f"Found {len(forms)} form(s):")
            for idx, form in enumerate(forms):
                action = form.get_attribute('action') or '[no action]'
                method = form.get_attribute('method') or '[no method]'
                form_id = form.get_attribute('id') or '[no id]'
                form_class = form.get_attribute('class') or '[no class]'
                print(f"  Form {idx+1}:")
                print(f"    - ID: {form_id}")
                print(f"    - Class: {form_class}")
                print(f"    - Action: {action}")
                print(f"    - Method: {method}")

                # List inputs in this form
                inputs = form.find_elements(By.TAG_NAME, "input")
                if inputs:
                    print(f"    - Inputs ({len(inputs)}):")
                    for inp in inputs[:5]:  # Show first 5
                        inp_type = inp.get_attribute('type')
                        inp_name = inp.get_attribute('name')
                        inp_id = inp.get_attribute('id')
                        print(f"      • type={inp_type}, name={inp_name}, id={inp_id}")
        else:
            print("No forms found on page")

        # Check for existing session cookies
        print(f"\n{'='*60}")
        print("EXISTING COOKIES")
        print(f"{'='*60}")
        cookies = driver.get_cookies()
        if cookies:
            print(f"Found {len(cookies)} cookie(s):")
            for cookie in cookies:
                print(f"  - {cookie['name']}: {cookie['value'][:50]}..." if len(cookie['value']) > 50 else f"  - {cookie['name']}: {cookie['value']}")
        else:
            print("No cookies found")

        print(f"\n{'='*60}")
        print("INSPECTION COMPLETE")
        print(f"{'='*60}")
        print("\nNext steps:")
        print(f"1. Review {page_source_path} to see the full HTML")
        print(f"2. Check {screenshot_path} to see what the page looks like")
        print("3. Use the element information above to update auth.py selectors")

        input("\nPress Enter to close browser...")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'driver' in locals():
            driver.quit()
            print("\nBrowser closed")

if __name__ == "__main__":
    url = "https://www.easydoct.com/rdv/gie-irldr-imagerie-rennes"

    print("="*60)
    print("EASYDOCT.COM PAGE STRUCTURE INSPECTOR")
    print("="*60)
    print(f"\nTarget URL: {url}")
    print("\nThis script will:")
    print("  1. Open the page in Chrome")
    print("  2. Search for login form elements")
    print("  3. Save page source and screenshot")
    print("  4. Display element information")
    print("\nUse headless mode? (y/n, default=n): ", end='')

    try:
        choice = input().strip().lower()
        headless = choice == 'y'
    except:
        headless = False

    print()
    inspect_page(url, headless=headless)
