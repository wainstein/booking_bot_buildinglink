import datetime
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def send_email(smtp_server, smtp_port, sender_email, sender_username, sender_password, recipient_emails, subject, html_content, attachment_path=None):
    """Send an email with the booking summary using SendGrid SMTP."""
    try:
        # Set up the SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_username, sender_password)

        # Create the email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join(recipient_emails)
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))

        # Attach the .ics file if provided
        if attachment_path:
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(attachment_path)}",
                )
                msg.attach(part)

        # Send the email
        server.sendmail(sender_email, recipient_emails, msg.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def generate_html_email(summary_results):
    """Generate a HTML email template for the booking summary."""
    html_content = """
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2 style="color: #2E86C1;">Booking Summary</h2>
            <table style="border-collapse: collapse; width: 100%; margin-top: 20px;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="border: 1px solid #dddddd; text-align: left; padding: 8px;">Time Slot</th>
                        <th style="border: 1px solid #dddddd; text-align: left; padding: 8px;">Status</th>
                        <th style="border: 1px solid #dddddd; text-align: left; padding: 8px;">Account</th>
                        <th style="border: 1px solid #dddddd; text-align: left; padding: 8px;">Facility</th>
                    </tr>
                </thead>
                <tbody>
    """

    for time_slot, result in summary_results.items():
        status = result.get('status', 'Failed')
        account = result.get('username', 'N/A')
        amenity_name = result.get('amenity_name', 'N/A')
        html_content += f"""
                    <tr>
                        <td style="border: 1px solid #dddddd; text-align: left; padding: 8px;">{time_slot}</td>
                        <td style="border: 1px solid #dddddd; text-align: left; padding: 8px;">{status}</td>
                        <td style="border: 1px solid #dddddd; text-align: left; padding: 8px;">{account}</td>
                        <td style="border: 1px solid #dddddd; text-align: left; padding: 8px;">{amenity_name}</td>
                    </tr>
        """

    html_content += """
                </tbody>
            </table>
        </body>
    </html>
    """
    return html_content

def generate_ics_file(summary_results, target_date_str):
    """Generate an .ics file with the booking summary for calendar import."""
    ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nCALSCALE:GREGORIAN\n"

    for time_slot, result in summary_results.items():
        if result.get("status") == "Success":
            # Create an event for each successful booking
            start_datetime = datetime.datetime.strptime(time_slot, "%H:%M")  # Convert time to datetime
            start_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")  # Use the target date
            start_dt = datetime.datetime.combine(start_date, start_datetime.time())
            end_dt = start_dt + datetime.timedelta(hours=1)  # Assume each booking is 1 hour

            description = f"Successfully booked {time_slot} for {result['username']} at {result['amenity_name']}."

            ics_content += (
                "BEGIN:VEVENT\n"
                f"SUMMARY:Booking for {result['username']} at {result['amenity_name']}\n"
                f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}\n"
                f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}\n"
                f"DESCRIPTION:{description}\n"
                "END:VEVENT\n"
            )

    ics_content += "END:VCALENDAR"

    # Save to file
    ics_file_path = "booking_summary.ics"
    with open(ics_file_path, "w") as ics_file:
        ics_file.write(ics_content)

    return ics_file_path
