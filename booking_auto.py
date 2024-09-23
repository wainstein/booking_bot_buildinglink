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
    times = config["times"]
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

    # Step 1: Each account attempts to book a unique time slot
    print("\nStep 1: Book a different time slot for each account.")
    first_step_results = []
    threads = []

    # Assign each user a unique time slot
    for i, user in enumerate(user_list):
        username = user['username']
        password = user['password']
        start_time = times[i % len(times)]  # Assign a time slot to each user
        t = threading.Thread(target=lambda q, *args: q.append(run_booking_process(*args)),
                             args=(first_step_results, username, password, target_date_str, start_time, prio_days, primary_amenity_id, primary_amenity_name, refresh_interval, check_interval))
        threads.append(t)
        t.start()
        time.sleep(0.1)  # Wait 100ms between each booking thread to avoid clashes

    # Wait for all threads in the first step to complete
    for t in threads:
        t.join()

    # Process first step results
    successful_times = []
    for result in first_step_results:
        time_slot = result['time']
        if result['status'] == 'Success':
            summary_results[time_slot] = {
                'status': 'Success',
                'username': result['username'],
                'amenity_name': primary_amenity_name
            }
            successful_times.append(time_slot)
        else:
            summary_results[time_slot] = {
                'status': 'Failed',
                'username': result['username'],
                'amenity_name': primary_amenity_name,
                'message': result['message']
            }

    # Step 2: Remaining combinations
    print("\nStep 2: Use the remaining 6 combinations to book the remaining time slots.")
    second_step_results = []
    threads = []

    # Build the remaining combinations for step 2
    remaining_combinations = []
    for user in user_list:
        username = user['username']
        password = user['password']
        for start_time in times:
            # Skip combinations attempted in the first step
            if not any(res['username'] == username and res['time'] == start_time for res in first_step_results):
                # Skip time slots that have been successfully booked
                if start_time not in successful_times:
                    remaining_combinations.append((username, password, start_time))

    # Start threads for remaining combinations
    for combo in remaining_combinations:
        username, password, start_time = combo
        t = threading.Thread(target=lambda q, *args: q.append(run_booking_process(*args)),
                             args=(second_step_results, username, password, target_date_str, start_time, prio_days, primary_amenity_id, primary_amenity_name, refresh_interval, check_interval))
        threads.append(t)
        t.start()
        time.sleep(0.1)

    # Wait for all threads in the second step to complete
    for t in threads:
        t.join()

    # Process second step results
    for result in second_step_results:
        time_slot = result['time']
        if result['status'] == 'Success' and summary_results[time_slot]['status'] != 'Success':
            summary_results[time_slot] = {
                'status': 'Success',
                'username': result['username'],
                'amenity_name': primary_amenity_name
            }
            successful_times.append(time_slot)
        elif summary_results[time_slot]['status'] != 'Success':
            summary_results[time_slot] = {
                'status': 'Failed',
                'username': result['username'],
                'amenity_name': primary_amenity_name,
                'message': result['message']
            }

    # Step 3: Remaining combinations
    print("\nStep 3: Use the remaining 3 combinations to book the remaining time slots.")
    third_step_results = []
    threads = []

    # Build the remaining combinations for step 3
    remaining_combinations_step3 = []
    for user in user_list:
        username = user['username']
        password = user['password']
        for start_time in times:
            # Skip combinations attempted in previous steps
            if not any(res['username'] == username and res['time'] == start_time for res in first_step_results + second_step_results):
                # Skip time slots that have been successfully booked
                if start_time not in successful_times:
                    remaining_combinations_step3.append((username, password, start_time))

    # Start threads for remaining combinations
    for combo in remaining_combinations_step3:
        username, password, start_time = combo
        t = threading.Thread(target=lambda q, *args: q.append(run_booking_process(*args)),
                             args=(third_step_results, username, password, target_date_str, start_time, prio_days, primary_amenity_id, primary_amenity_name, refresh_interval, check_interval))
        threads.append(t)
        t.start()
        time.sleep(0.1)

    # Wait for all threads in the third step to complete
    for t in threads:
        t.join()

    # Process third step results
    for result in third_step_results:
        time_slot = result['time']
        if result['status'] == 'Success' and summary_results[time_slot]['status'] != 'Success':
            summary_results[time_slot] = {
                'status': 'Success',
                'username': result['username'],
                'amenity_name': primary_amenity_name
            }
            successful_times.append(time_slot)
        elif summary_results[time_slot]['status'] != 'Success':
            summary_results[time_slot] = {
                'status': 'Failed',
                'username': result['username'],
                'amenity_name': primary_amenity_name,
                'message': result['message']
            }

    # 如果还有未成功的时段，尝试预订备用设施
    failed_time_slots = [time_slot for time_slot, res in summary_results.items() if res['status'] != 'Success']

    if failed_time_slots:
        print("\n尝试预订备用设施。")
        alternate_results = []
        threads = []

        for time_slot in failed_time_slots:
            for user in user_list:
                username = user['username']
                password = user['password']
                t = threading.Thread(target=lambda q, *args: q.append(run_booking_process(*args)),
                                     args=(alternate_results, username, password, target_date_str, time_slot, prio_days, alternate_amenity_id, alternate_amenity_name, refresh_interval, check_interval))
                threads.append(t)
                t.start()
                time.sleep(0.1)

        # Wait for all threads in the alternate step to complete
        for t in threads:
            t.join()

        # Process alternate amenity results
        for result in alternate_results:
            time_slot = result['time']
            if result['status'] == 'Success' and summary_results[time_slot]['status'] != 'Success':
                summary_results[time_slot] = {
                    'status': 'Success',
                    'username': result['username'],
                    'amenity_name': alternate_amenity_name
                }
            elif summary_results[time_slot]['status'] != 'Success':
                summary_results[time_slot] = {
                    'status': 'Failed',
                    'username': result['username'],
                    'amenity_name': alternate_amenity_name,
                    'message': result['message']
                }

    # 最终生成报告并发送邮件
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
