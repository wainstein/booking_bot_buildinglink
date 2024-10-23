from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import sys
import threading
import time
import datetime
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import logging
import os


MAX_RETRIES = 10
RETRY_DELAY = 3  # seconds

def setup_logger(username, time_slot):
    """Set up a logger for each booking process and time slot."""
    thread_id = threading.get_ident()  # Get unique thread ID
    # Ensure the logs directory exists
    os.makedirs("logs", exist_ok=True)
    log_filename = f"logs/{username}_{time_slot}_{thread_id}.log"
    
    logger = logging.getLogger(log_filename)  # Use filename as logger name to avoid conflicts
    logger.setLevel(logging.DEBUG)

    # Create a file handler for logging
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)

    # Create a logging format
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add the handlers to the logger
    if not logger.hasHandlers():  # Avoid adding multiple handlers in case of re-entry
        logger.addHandler(file_handler)

    return logger

def convert_to_24_hour_format(time_str):
    """Convert a time string to 24-hour format."""
    try:
        # Handle 12-hour format with AM/PM
        in_time = datetime.datetime.strptime(time_str.strip(), "%I:%M %p")
        return in_time.strftime("%H:%M")
    except ValueError:
        try:
            # Handle already in 24-hour format
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
        print(f"[{username}] Can't find Error section")
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
        wait_for_start_time_options_to_load(driver)
        time_options = driver.find_elements(By.XPATH, "//div[@id='ctl00_ContentPlaceHolder1_StartTimePicker_timeView']//a")
        print(f"[{username}] Retrieved time options for start time.")

        # Check both 12-hour and 24-hour formats
        matched = False
        for option in time_options:
            option_text_raw = option.text.strip()
            option_text = convert_to_24_hour_format(option_text_raw)  # Convert each option to 24-hour format
            if option_text == start_time_24:
                option.click()
                matched = True
                print(f"[{username}] Selected start time: {option_text}")
                break

        if not matched:
            raise ValueError(f"[{username}] Could not find a matching start time option for '{start_time_24}'.")

        # Automatically set end time
        set_end_time(driver, start_time, username)

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
        
        time.sleep(2)
        # After submitting, immediately check for errors
        has_error, error_message = check_for_errors_and_exit(driver, username)
        if has_error:
            raise ValueError(f"[{username}] Booking error detected: {error_message}")

    except Exception as e:
        # Log the exception and re-raise
        print(f"[{username}] Exception during booking time slot: {e}")
        raise

def set_end_time(driver, start_time, username):
    """Set the end time to one hour later than the start time."""
    try:
        print(f"[{username}] Setting end time.")
        # Convert start time to a datetime object and add one hour
        start_time_obj = datetime.datetime.strptime(start_time.strip(), "%I:%M")
        end_time_obj = start_time_obj + datetime.timedelta(hours=1)
        end_time_str = end_time_obj.strftime("%I:%M")  # Convert back to 12-hour format
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
        wait_for_end_time_options_to_load(driver)
        time_options = driver.find_elements(By.XPATH, "//div[@id='ctl00_ContentPlaceHolder1_EndTimePicker_timeView']//a")
        print(f"[{username}] Retrieved time options for end time.")

        # Check both 12-hour and 24-hour formats
        matched = False
        for option in time_options:
            option_text = convert_to_24_hour_format(option.text.strip())  # Convert each option to 24-hour format
            if option_text == end_time_24:
                option.click()
                matched = True
                print(f"[{username}] Selected end time: {option_text}")
                break

        if not matched:
            raise ValueError(f"[{username}] Could not find a matching end time option for '{end_time_24}'.")

    except Exception as e:
        print(f"[{username}] Exception during setting end time: {e}")
        raise

def verify_page_url(driver, target_date, username, amenity_id):
    """Verify if the current URL matches the expected target date URL, ignoring case."""
    expected_url = f"https://www.buildinglink.com/V2/Tenant/Amenities/NewReservation.aspx?amenityId={amenity_id}&from=0&selectedDate={target_date}".lower()
    max_attempts = 10
    attempts = 0

    while attempts < max_attempts:
        current_url = driver.current_url.lower()  # Convert current URL to lowercase for case-insensitive comparison
        if current_url == expected_url:
            print(f"[{username}] URL verification successful. Current URL matches target (ignoring case): {current_url}")
            return True
        else:
            print(f"[{username}] URL mismatch (ignoring case). Current URL: {current_url}, expected: {expected_url}. Reloading...")
            driver.get(expected_url)
            time.sleep(0.1)  # Wait for the page to load before checking again
            attempts += 1

    print(f"[{username}] URL verification failed after {max_attempts} attempts.")
    return False

def send_error_email(config, username, error_message):
    subject = f"Error in booking process for {username}"
    body = f"An error occurred while setting up the browser for {username}. Error details: {error_message}"
    
    msg = MIMEMultipart()
    msg['From'] = config["sender_email"]
    msg['To'] = ', '.join(config["recipient_emails"])
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["sender_username"], config["sender_password"])
            server.send_message(msg)
        print(f"Error email sent for {username}")
    except Exception as e:
        print(f"Failed to send error email for {username}: {str(e)}")

def setup_driver(logger):
    chrome_options = Options()
    if sys.platform in ["linux", "darwin"]:
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

    for attempt in range(MAX_RETRIES):
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            logger.info("Browser successfully initialized.")
            return driver
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error("Max retries reached. Unable to initialize browser.")
                raise

def run_booking_process(username, password, target_date, time_slots, prio_days, amenity_id, amenity_name, refresh_interval, check_interval, config):
    logger = setup_logger(username, "multiple_slots")
    logger.info(f"Starting booking process for {username} for date {target_date} with time slots {time_slots}")

    target_datetime = datetime.datetime.strptime(target_date, "%Y-%m-%d")
    target_time = datetime.datetime.combine(target_datetime - datetime.timedelta(days=prio_days), datetime.time(0, 0))
    logger.info(f"Waiting for booking time: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")

    while True:
        now = datetime.datetime.now()
        time_to_booking = (target_time - now).total_seconds()

        if time_to_booking <= 300:
            logger.info("Booking time is less than 5 minutes away. Getting ready...")
            break

        time.sleep(check_interval)
        
    driver = None
    all_results = []

    try:
        driver = setup_driver(logger)
        logger.info("Browser ready.")

        # Login
        login_date = (datetime.date.today() + datetime.timedelta(days=prio_days)).strftime("%Y-%m-%d")
        login(driver, username, password, login_date)
        logger.info("Logged in.")

        # Wait until target time
        while True:
            now = datetime.datetime.now()
            time_to_booking = (target_time - now).total_seconds()
            if time_to_booking <= 0:
                break
            elif time_to_booking <= 5:  # If less than 5 seconds, wait precisely
                time.sleep(time_to_booking)
                break
            else:
                time.sleep(check_interval)  # Wait in small intervals

        for start_time in time_slots:
            result = {"username": username, "time": start_time, "amenity_id": amenity_id, "amenity_name": amenity_name, "status": "Failed", "message": ""}
            slot_logger = setup_logger(username, start_time)
            slot_logger.info(f"Starting booking for time slot {start_time}")

            try:
                # Navigate to the booking page for the target date
                navigate_to_booking_page(driver, amenity_id, target_date, username)
                slot_logger.info(f"Navigated to reserve page for amenity {amenity_name} on {target_date}.")

                # Verify if the page is for the correct date
                if verify_page_url(driver, target_date, username, amenity_id):
                    slot_logger.info("Correct date page loaded.")
                else:
                    msg = "Incorrect date page loaded. Skipping this time slot."
                    slot_logger.error(msg)
                    result["message"] = msg
                    all_results.append(result)
                    continue  # Skip to the next time slot

                # Check if amenity is unavailable
                if check_amenity_unavailable(driver, username):
                    msg = "Amenity is currently unavailable on the selected date."
                    slot_logger.error(msg)
                    result["message"] = msg
                    all_results.append(result)
                    continue  # Skip to the next time slot

                # Attempt to book the time slot
                slot_logger.info(f"Attempting to book at {start_time}.")
                book_time_slot(driver, start_time, username)

                try:
                    driver.find_element(By.ID, "ThePageHeaderWrap")
                    result["status"] = "Success"
                    result["message"] = "Reservation has been made successfully!"
                    slot_logger.info("Booking successful.")
                except NoSuchElementException:
                    result["message"] = "Booking was not successful."
                    slot_logger.error("Booking failed.")

            except Exception as e:
                result["message"] = f"An error occurred: {str(e)}"
                slot_logger.error(f"Exception in booking process: {traceback.format_exc()}")

            finally:
                all_results.append(result)
                slot_logger.info(f"Finished booking attempt for time slot {start_time}.")

        # After all bookings, optionally logout or perform any cleanup if necessary

    except Exception as e:
        error_message = f"Exception in overall booking process: {traceback.format_exc()}"
        logger.error(error_message)
        send_error_email(config, username, error_message)
    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed.")
    
    logger.info(f"All booking attempts completed. Results: {all_results}")
    return all_results