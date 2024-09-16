
# Booking System Setup Guide

This guide provides detailed instructions on how to set up and configure a Python-based automated booking system. This system is designed to automatically attempt to book amenities at specific times and send an email summary of the booking results.

## Prerequisites

Before you begin, ensure you have Python 3 and `pip` installed on your system. You can download and install Python from [python.org](https://www.python.org/downloads/).

## Setting Up the Environment

1. **Create a Virtual Environment**:
   This step isolates the project dependencies from the global Python environment.

   ```bash
   python3 -m venv .venv
   ```

2. **Activate the Virtual Environment**:
   - On **Linux/macOS**:

     ```bash
     source .venv/bin/activate
     ```

   - On **Windows**:

     ```cmd
     .venv\Scripts\activate
     ```

3. **Install Dependencies**:
   Install the required Python packages specified in `requirements.txt`.

   ```bash
   pip3 install -r requirements.txt
   ```

## Configuration

The system uses a configuration file named `booking_config.json`. You should create this file based on the provided template `booking_config.template.json`.

1. **Copy the Template**:
   Copy the contents of `booking_config.template.json` into a new file named `booking_config.json`.

2. **Edit the Configuration**:
   Modify the `booking_config.json` file to fit your requirements. Below is an explanation of each field in the configuration file:

   - `users`: List of user credentials for logging into the booking system.
   - `target_date_offset_days`: Number of days from today when the booking should be attempted.
   - `booking_start_offset_days`: Offset to determine when the booking process starts.
   - `primary_amenity_name`: The primary amenity to attempt to book.
   - `alternate_amenity_name`: An alternative amenity to book if the primary is unavailable.
   - `amenities`: A dictionary mapping amenity names to their respective IDs.
   - `times`: A list of times for which to attempt bookings.
   - `refresh_interval_seconds`: How often to refresh the booking page in seconds.
   - `check_interval_seconds`: How often to check the system for a chance to start the booking process.
   - `target_days`: Days of the week when bookings should be attempted (0=Monday, 6=Sunday).
   - `smtp_server`: SMTP server for sending emails.
   - `smtp_port`: SMTP server port.
   - `sender_email`: The email address used to send summaries.
   - `sender_username`: Username for SMTP authentication.
   - `sender_password`: Password for SMTP authentication.
   - `recipient_emails`: List of email addresses to receive the booking summary.

   Here is an example of how you might fill out the template:

   ```json
   {
     "users": [
       {"username": "example_user", "password": "example_password"},
       {"username": "example_user2", "password": "example_password2"}
     ],
     "target_date_offset_days": 4,
     "booking_start_offset_days": 3,
     "primary_amenity_name": "Gym",
     "alternate_amenity_name": "Pool",
     "amenities": {
       "Gym": "12345",
       "Pool": "67890"
     },
     "times": ["18:00", "19:00", "20:00"],
     "refresh_interval_seconds": 60,
     "check_interval_seconds": 0.5,
     "target_days": [0, 1, 2, 3, 4, 5, 6],
     "smtp_server": "smtp.sendgrid.com",
     "smtp_port": 587,
     "sender_email": "sender@example.com",
     "sender_username": "smtp_user",
     "sender_password": "smtp_pass",
     "recipient_emails": ["recipient1@example.com", "recipient2@example.com"]
   }
   ```

## Running the System

Once your configuration is set, run the booking system using:

```bash
python auto_book.py
```

Ensure that your system's clock is set correctly and that you have an uninterrupted internet connection during the booking process.

## Troubleshooting

- **Environment Errors**: If you encounter errors related to missing packages or dependencies, ensure that your virtual environment is activated and that all dependencies are installed as per the `requirements.txt` file.
- **Configuration Issues**: Double-check your `booking_config.json` file for any typos or incorrect values, especially in user credentials and SMTP settings.

## Conclusion

This setup guide should help you configure and run the automated booking system efficiently. For any further questions or support, refer to the project documentation or contact the system administrator.

## License

This project is available under a non-commercial open-source license. This allows individuals and organizations to use, modify, and distribute the software for non-commercial purposes only. Any usage of the software for commercial purposes without permission is strictly prohibited.

```
Copyright (c) 2024 JUNJUN WAN

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```
