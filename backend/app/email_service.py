import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_email(to_email, subject, html_content):
    """
    Sends an email using SendGrid.
    For now, this function will just print the email to the console.
    """
    print("---- Sending Email ----")
    print(f"To: {to_email}")
    print(f"Subject: {subject}")
    print(f"Body: {html_content}")
    print("-----------------------")
    return True

    # Uncomment the following to use the actual SendGrid API
    # try:
    #     message = Mail(
    #         from_email='your_verified_sendgrid_email@example.com',
    #         to_emails=to_email,
    #         subject=subject,
    #         html_content=html_content)
    #
    #     sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
    #     response = sg.send(message)
    #     return response.status_code == 202
    # except Exception as e:
    #     print(e)
    #     return False
