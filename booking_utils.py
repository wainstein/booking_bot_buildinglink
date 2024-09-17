import sys
import time
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def convert_to_24_hour_format(time_str):
    """Convert a time string to 24-hour format."""
    try:
        in_time = datetime.datetime.strptime(time_str.strip(), "%I:%M %p")
        return in_time.strftime("%H:%M")
    except ValueError:
        try:
            in_time = datetime.datetime.strptime(time_str.strip(), "%H:%M")
            return in_time.strftime("%H:%M")
        except ValueError:
            return time_str  # Return as is if conversion fails

def login(driver, username, password, login_date):
    """Log in to the booking system."""
    driver.get(f"https://auth.buildinglink.com/Account/Login?selectedDate={login_date}")

    # Login process
    username_field = driver.find_element(By.NAME, "Username")
    password_field = driver.find_element(By.NAME, "Password")

    username_field.send_keys(username)
    password_field.send_keys(password)

    login_button = driver.find_element(By.ID, "LoginButton")
    login_button.click()

def navigate_to_booking_page(driver, amenity_id, target_date):
    """Navigate to the booking page after logging in."""
    driver.get(f"https://www.buildinglink.com/V2/Tenant/Amenities/NewReservation.aspx?amenityId={amenity_id}&from=0&selectedDate={target_date}")

def keep_session_alive(driver, refresh_interval):
    """Keep the session alive by refreshing the page at regular intervals."""
    if int(time.time()) % refresh_interval == 0:
        driver.refresh()
        print("Refreshed page to keep session alive.")

def check_for_validation_error(driver):
    """Check if there is any text inside the ValidationContainer indicating an error."""
    try:
        validation_container = driver.find_element(By.ID, "ValidationContainer")
        validation_text = validation_container.text.strip()
        if validation_text:
            print(f"Detected validation error: {validation_text}")
            return True, validation_text
        return False, ""
    except:
        return False, ""

def book_time_slot(driver, start_time):
    """Book a specific time slot."""
    # Convert input start_time to 24-hour format
    start_time_24 = convert_to_24_hour_format(start_time)

    # Select time
    start_time_input = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.ID, 'ctl00_ContentPlaceHolder1_StartTimePicker_dateInput'))
    )
    start_time_input.click()  # Click to open the time options

    # Find all time options available in the time picker
    time_options = driver.find_elements(By.XPATH, "//div[@id='ctl00_ContentPlaceHolder1_StartTimePicker_timeView']//a")

    # Check both 12-hour and 24-hour formats
    matched = False
    for option in time_options:
        option_text = convert_to_24_hour_format(option.text.strip())  # Convert each option to 24-hour format
        if option_text == start_time_24:
            option.click()
            matched = True
            break
    
    if not matched:
        raise ValueError(f"Could not find a matching time option for '{start_time_24}'.")

    # Submit booking
    submit_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, 'ctl00_ContentPlaceHolder1_HeaderSaveButton'))
    )
    submit_button.click()
    
def setup_driver():
    """Set up the WebDriver with appropriate options based on the OS."""
    chrome_options = Options()
    # Detect if the OS is Linux or Darwin (macOS), and run headless if it is
    if sys.platform in ["linux", "darwin"]:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def run_booking_process(username, password, target_date, start_time, amenity_id, amenity_name, refresh_interval, check_interval):
    """Run the booking process for a specific user, date, and time."""
    result = {"username": username, "time": start_time, "amenity_id": amenity_id, "amenity_name": amenity_name, "status": "Failed", "message": ""}

    # Calculate target time based on target_date minus 3 days at midnight
    target_datetime = datetime.datetime.strptime(target_date, "%Y-%m-%d")
    target_time = datetime.datetime.combine(target_datetime - datetime.timedelta(days=3), datetime.time(0, 0))
    print(f"[{username}] Waiting for booking time: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Check if the current time is within 5 minutes of the target time or has already passed
    while True:
        now = datetime.datetime.now()
        time_to_booking = (target_time - now).total_seconds() / 60  # Time to booking in minutes
        
        if time_to_booking <= 5:
            break  # Within 5 minutes or already past target time
        
        # Wait and check again
        print(f"[{username}] Booking time is more than 5 minutes away. Waiting...")
        time.sleep(10)  # Check every 10 seconds

    driver = setup_driver()
    try:
        driver = webdriver.Chrome()

        # Login URL with dynamic date (current date + 3 days)
        login_date = (datetime.date.today() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
        login(driver, username, password, login_date)

        # Immediately navigate to the target booking page after login
        navigate_to_booking_page(driver, amenity_id, target_date)

        # Real-time check for booking time while keeping the session alive
        while True:
            now = datetime.datetime.now()
            if now >= target_time:
                break

            # Keep session alive
            keep_session_alive(driver, refresh_interval)

            # High-frequency check for target time
            time.sleep(check_interval)

        # Booking time reached, proceed with booking
        print(f"[{username}] Attempting to book at {start_time}.")
        book_time_slot(driver, start_time)

        # Check for validation errors immediately after clicking submit
        has_error, error_message = check_for_validation_error(driver)
        if has_error:
            result["message"] = f"Booking error detected: {error_message}"
            return result  # Exit if an error is detected

        # Wait for the success element indicating a redirect to the Calendar View page
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, 'ThePageHeaderWrap'))
            )
            # If the element is found, it means booking was successful
            result["status"] = "Success"
            result["message"] = "Reservation has been made successfully!"
        except:
            # If the element is not found, check for a warning
            result["message"] = "Booking was not successful."

    except Exception as e:
        result["message"] = f"An error occurred: {str(e)}"
    finally:
        if driver:
            driver.quit()
    return result
