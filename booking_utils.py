import sys
import time
import datetime
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

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
    try:
        driver.get(f"https://auth.buildinglink.com/Account/Login?selectedDate={login_date}")
        print(f"[{username}] Navigated to login page.")

        # Login process
        username_field = driver.find_element(By.NAME, "Username")
        password_field = driver.find_element(By.NAME, "Password")

        username_field.send_keys(username)
        password_field.send_keys(password)
        print(f"[{username}] Entered credentials.")

        login_button = driver.find_element(By.ID, "LoginButton")
        login_button.click()
        print(f"[{username}] Clicked login button.")
    except Exception as e:
        print(f"[{username}] Exception during login: {e}")
        raise

def navigate_to_booking_page(driver, amenity_id, target_date, username):
    """Navigate to the booking page after logging in."""
    try:
        driver.get(f"https://www.buildinglink.com/V2/Tenant/Amenities/NewReservation.aspx?amenityId={amenity_id}&from=0&selectedDate={target_date}")
        print(f"[{username}] Navigated to booking page for amenity ID {amenity_id} on {target_date}.")
    except Exception as e:
        print(f"[{username}] Exception during navigation to booking page: {e}")
        raise

def keep_session_alive(driver, refresh_interval, username):
    """Keep the session alive by refreshing the page at regular intervals."""
    try:
        if int(time.time()) % refresh_interval == 0:
            driver.refresh()
            print(f"[{username}] Refreshed page to keep session alive.")
    except Exception as e:
        print(f"[{username}] Exception during session refresh: {e}")

def check_for_errors_and_exit(driver, username):
    """Check the ValidationContainer for errors and exit if found."""
    try:
        validation_container = driver.find_element(By.ID, "ValidationContainer")
        if validation_container.text.strip():  # If ValidationContainer has any text
            # Check specific labels for detailed error messages
            errors = []
            try:
                error_label_1 = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ValidationSummary1")
                if error_label_1.text.strip():
                    errors.append(error_label_1.text.strip())
            except Exception as e:
                print(f"[{username}] No error in ValidationSummary1: {e}")

            try:
                error_label_2 = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ctl00_ContentPlaceHolder1_pnlAllocationErrorPanel")
                if error_label_2.text.strip():
                    errors.append(error_label_2.text.strip())
            except Exception as e:
                print(f"[{username}] No error in pnlAllocationErrorPanel: {e}")

            error_message = " | ".join(errors) if errors else "Unknown error in ValidationContainer."
            print(f"[{username}] Detected error: {error_message}")
            return True, error_message
    except Exception as e:
        print(f"[{username}] Exception during error checking: {e}")
    return False, ""

def check_amenity_unavailable(driver, username):
    """Check if the amenity is unavailable on the selected date."""
    try:
        # Look for the specific element indicating unavailability
        error_element = driver.find_element(By.CSS_SELECTOR, "div.Div.PT")
        if "This Amenity is currently unavailable on the selected date." in error_element.text:
            print(f"[{username}] Amenity is currently unavailable on the selected date.")
            return True
        return False
    except Exception as e:
        print(f"[{username}] Amenity availability check exception: {e}")
        return False
    
def wait_for_start_time_options_to_load(driver, timeout=10):
    """The text of the waiting time option is not empty"""
    WebDriverWait(driver, timeout).until(
        lambda d: all(option.text.strip() != '' for option in d.find_elements(By.XPATH, "//div[@id='ctl00_ContentPlaceHolder1_StartTimePicker_timeView']//a"))
    )
        
def wait_for_end_time_options_to_load(driver, timeout=10):
    """The text of the waiting time option is not empty"""
    WebDriverWait(driver, timeout).until(
        lambda d: all(option.text.strip() != '' for option in d.find_elements(By.XPATH, "//div[@id='ctl00_ContentPlaceHolder1_EndTimePicker_timeView']//a"))
    )

def book_time_slot(driver, start_time, username):
    """Book a specific time slot and handle validation errors for end time."""
    try:
        print(f"[{username}] Attempting to book time slot: {start_time}")

        # Convert input start_time to 24-hour format
        start_time_24 = convert_to_24_hour_format(start_time)
        print(f"[{username}] Converted start time to 24-hour format: {start_time_24}")

        # Select start time
        start_time_input = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, 'ctl00_ContentPlaceHolder1_StartTimePicker_dateInput'))
        )
        start_time_input.click()  # Click to open the time options
        print(f"[{username}] Clicked on start time input.")

        # Find all time options available in the time picker
        time_options = driver.find_elements(By.XPATH, "//div[@id='ctl00_ContentPlaceHolder1_StartTimePicker_timeView']//a")
        print(f"[{username}] Retrieved time options for start time.")

        # Check both 12-hour and 24-hour formats
        matched = False
        wait_for_start_time_options_to_load(driver)
        for option in time_options:
            option_text_raw = option.text.strip()
            option_text = convert_to_24_hour_format(option_text_raw)  # Convert each option to 24-hour format
            print(f"Raw option: {option_text_raw} - Converted: {option_text} - Target: {start_time_24}")
            if option_text == start_time_24:
                option.click()
                matched = True
                print(f"[{username}] Selected start time: {option_text}")
                break

        if not matched:
            raise ValueError(f"[{username}] Could not find a matching start time option for '{start_time_24}'.")

        # Automatically set end time
        #set_end_time(driver, start_time, username)

        # Check if validation error occurs and retry
        has_error, error_message = check_for_errors_and_exit(driver, username)
        if has_error:
            if "End time must be greater than start time" in error_message:
                print(f"[{username}] Error detected: End time is not valid. Retrying to select a new end time.")
                # Retry selecting the end time
                set_end_time(driver, start_time, username)
            else:
                raise ValueError(f"[{username}] Booking error detected: {error_message}")

        # Submit booking
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'ctl00_ContentPlaceHolder1_HeaderSaveButton'))
        )
        submit_button.click()
        print(f"[{username}] Clicked submit button to finalize booking.")

    except Exception as e:
        print(f"[{username}] Exception during booking time slot: {e}")
        raise

def set_end_time(driver, start_time, username):
    """Set the end time to one hour later than the start time."""
    try:
        print(f"[{username}] Setting end time.")
        # Convert start time to a datetime object and add one hour
        start_time_obj = datetime.datetime.strptime(start_time.strip(), "%I:%M")
        end_time_obj = start_time_obj + datetime.timedelta(hours=1)
        end_time_str = end_time_obj.strftime("%I:%M %p")  # Convert back to 12-hour format
        # Convert input start_time to 24-hour format
        end_time_24 = convert_to_24_hour_format(end_time_str)
        print(f"[{username}] Calculated end time: {end_time_24}")

        # Click the end time input to open the time options
        end_time_input = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, 'ctl00_ContentPlaceHolder1_EndTimePicker_dateInput'))
        )
        end_time_input.click()  # Click to open the time options
        print(f"[{username}] Clicked on end time input.")

        # Find all time options available in the time picker
        time_options = driver.find_elements(By.XPATH, "//div[@id='ctl00_ContentPlaceHolder1_EndTimePicker_timeView']//a")
        print(f"[{username}] Retrieved time options for end time.")

        # Check both 12-hour and 24-hour formats
        matched = False
        wait_for_end_time_options_to_load(driver)
        for option in time_options:
            option_text = convert_to_24_hour_format(option.text.strip())  # Convert each option to 24-hour format
            print(f"{option_text}-{end_time_24}")
            if option_text == end_time_24:
                option.click()
                matched = True
                print(f"[{username}] Selected start time: {option_text}")
                break

        if not matched:
            raise ValueError(f"[{username}] Could not find a matching start time option for '{end_time_24}'.")

    except Exception as e:
        print(f"[{username}] Exception during setting end time: {e}")
        raise

def setup_driver():
    """Set up the WebDriver with appropriate options based on the OS."""
    chrome_options = Options()
    if sys.platform in ["linux"]:
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def run_booking_process(username, password, target_date, start_time, prio_days, amenity_id, amenity_name, refresh_interval, check_interval):
    """Run the booking process for a specific user, date, and time."""
    result = {"username": username, "time": start_time, "amenity_id": amenity_id, "amenity_name": amenity_name, "status": "Failed", "message": ""}

    # Calculate target time based on target_date minus prio days at midnight
    target_datetime = datetime.datetime.strptime(target_date, "%Y-%m-%d")
    target_time = datetime.datetime.combine(target_datetime - datetime.timedelta(days=prio_days), datetime.time(0, 0))
    print(f"[{username}] Waiting for booking time: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Check if the current time is within 5 minutes of the target time or has already passed
    while True:
        now = datetime.datetime.now()
        time_to_booking = (target_time - now).total_seconds() / 60  # Time to booking in minutes

        if time_to_booking <= 5:
            print(f"[{username}] Booking time is less than 5 minutes away. Getting ready...")
            break  # Within 5 minutes or already past target time

        # Wait and check again
        time.sleep(10)  # Check every 10 seconds

    try:
        driver = setup_driver()
        print(f"[{username}] Browser ready.")

        # Login URL with dynamic date (current date + prio days)
        login_date = (datetime.date.today() + datetime.timedelta(days=prio_days)).strftime("%Y-%m-%d")
        login(driver, username, password, login_date)
        print(f"[{username}] Logged in.")

        # Immediately navigate to the target booking page after login
        navigate_to_booking_page(driver, amenity_id, target_date, username)
        print(f"[{username}] Navigated to reserve page and standing by.")

        # Real-time check for booking time while keeping the session alive
        while True:
            now = datetime.datetime.now()
            if now >= target_time:
                print(f"[{username}] Booking time reached. Proceeding to book.")
                break

            # Check for any validation errors immediately
            has_error, error_message = check_for_errors_and_exit(driver, username)
            if has_error:
                result["message"] = f"Booking error detected: {error_message}"
                print(f"[{username}] {result['message']}")
                return result

            # Keep session alive
            keep_session_alive(driver, refresh_interval, username)

            # High-frequency check for target time
            time.sleep(check_interval)

        driver.refresh()
        print(f"[{username}] Page refreshed at booking time.")

        # Retry logic for unavailable amenity
        max_retries = 3
        retries = 0
        while retries < max_retries:
            if check_amenity_unavailable(driver, username):
                retries += 1
                print(f"[{username}] Attempt {retries}: Amenity unavailable, refreshing page...")
                if retries >= max_retries:
                    print(f"[{username}] Max retries reached. Exiting with error.")
                    result["message"] = "Amenity unavailable on the selected date after 3 attempts."
                    return result
                driver.refresh()
                time.sleep(5)  # Wait a bit before trying again
            else:
                print(f"[{username}] Amenity is available. Proceeding.")
                break

        if retries == max_retries:
            result["message"] = f"Booking date error. Exiting"
            print(f"[{username}] {result['message']}")
            return result

        # Check for any validation errors immediately
        has_error, error_message = check_for_errors_and_exit(driver, username)
        if has_error:
            result["message"] = f"Booking error detected: {error_message}"
            print(f"[{username}] {result['message']}")
            return result

        # Booking time reached, proceed with booking
        print(f"[{username}] Attempting to book at {start_time}.")
        book_time_slot(driver, start_time, username)

        # Wait for the success element indicating a redirect to the Calendar View page
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, 'ThePageHeaderWrap'))
            )
            # If the element is found, it means booking was successful
            result["status"] = "Success"
            result["message"] = "Reservation has been made successfully!"
            print(f"[{username}] Booking successful.")
        except Exception as e:
            # If the element is not found, check for a warning
            result["message"] = "Booking was not successful."
            print(f"[{username}] Booking failed: {e}")

    except Exception as e:
        result["message"] = f"An error occurred: {str(e)}"
        print(f"[{username}] Exception in booking process: {traceback.format_exc()}")
    finally:
        if driver:
            driver.quit()
            print(f"[{username}] Browser closed.")
    return result
