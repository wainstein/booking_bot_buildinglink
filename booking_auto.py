import os
import threading
import time
import datetime
import json
from booking_utils import run_booking_process
from email_utils import generate_html_email, generate_ics_file, send_email

CONFIG_FILE = 'booking_config.json'

def load_config():
    """Load the configuration from the JSON file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        raise FileNotFoundError(f"{CONFIG_FILE} not found.")

def calculate_target_date(offset_days, target_days):
    """
    Calculate the target date for booking based on the configuration.
    The target date is determined based on whether the standby date matches any of the configured target days.
    """
    standby_date = datetime.date.today() + datetime.timedelta(days=offset_days)
    if standby_date.weekday() in target_days:
        return standby_date
    else:
        print(f"The standby date {standby_date} does not match any of the configured target days {target_days}. Exiting.")
        return None

def run_all_bookings(config):
    """Run booking processes for all users and summarize results."""
    user_list = config["users"]
    target_date_offset_days = config["target_date_offset_days"]
    primary_amenity_name = config["primary_amenity_name"]
    alternate_amenity_name = config["alternate_amenity_name"]
    times = config["times"]  # List of time_slots
    refresh_interval = config["refresh_interval_seconds"]
    check_interval = config["check_interval_seconds"]
    target_days = config["target_days"]
    prio_days = config["booking_start_offset_days"]

    # Map amenity names to IDs
    amenity_ids = config["amenities"]

    primary_amenity_id = amenity_ids[primary_amenity_name]
    alternate_amenity_id = amenity_ids[alternate_amenity_name]

    # Calculate target date
    target_date = calculate_target_date(target_date_offset_days, target_days)
    if not target_date:
        return  # Exit if no valid target date

    target_date_str = target_date.strftime("%Y-%m-%d")
    print(f"Target date for booking is {target_date_str}")

    # Data structure to hold booking results per time slot
    summary_results = {time_slot: {} for time_slot in times}

    # First Round Booking: Attempt to book primary amenity
    print("\nStarting first round booking for primary amenity.")
    threads = []
    first_round_results = []
    lock = threading.Lock()  # To synchronize access to first_round_results

    # Determine rotation offset for time_slots to ensure different starting slots per thread
    total_time_slots = len(times)

    for i, user in enumerate(user_list):
        username = user['username']
        password = user['password']

        # Rotate time_slots list for each thread to ensure different starting slots
        rotation_offset = i % total_time_slots if total_time_slots > 0 else 0
        rotated_times = times[rotation_offset:] + times[:rotation_offset]

        # Define the thread's target function with rotated time_slots
        def thread_target(user, rotated_times, first_round_results, lock):
            username = user['username']
            password = user['password']
            results = run_booking_process(
                username=username,
                password=password,
                target_date=target_date_str,
                time_slots=rotated_times,
                prio_days=prio_days,
                amenity_id=primary_amenity_id,
                amenity_name=primary_amenity_name,
                refresh_interval=refresh_interval,
                check_interval=check_interval,
                config=config
            )
            with lock:
                first_round_results.extend(results)

        # Create and start the thread
        t = threading.Thread(target=thread_target, args=(user, rotated_times, first_round_results, lock))
        threads.append(t)
        t.start()
        time.sleep(0.15)  # Optional: small delay to stagger thread starts

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Process first round results
    for result in first_round_results:
        time_slot = result['time']
        if result['status'] == 'Success' and time_slot in summary_results:
            summary_results[time_slot] = {
                'status': 'Success',
                'username': result['username'],
                'amenity_name': primary_amenity_name
            }

    # Update summary results for failed time slots
    for time_slot, res in summary_results.items():
        if res == {}:
            summary_results[time_slot] = {
                'status': 'Failed',
                'username': 'N/A',
                'amenity_name': 'N/A'
            }

    # Generate HTML content for the email
    html_content = generate_html_email(summary_results)

    # Generate .ics file with booking results
    ics_file_path = generate_ics_file(summary_results, target_date_str)

    # Send email with booking results and attach the .ics file
    send_email(
        config["smtp_server"],
        config["smtp_port"],
        config["sender_email"],
        config["sender_username"],
        config["sender_password"],
        config["recipient_emails"],
        f"Booking Summary for {target_date_str}",
        html_content,
        attachment_path=ics_file_path
    )

if __name__ == "__main__":
    # Load configuration
    config = load_config()
    run_all_bookings(config)
