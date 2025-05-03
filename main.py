from fastapi import FastAPI, HTTPException
import requests
from bs4 import BeautifulSoup
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = FastAPI()

def check_dl_status(dln: str, issue_dt: str = "04/30/2025"):
    """Checks the Illinois driving license status."""
    url = "https://apps.ilsos.gov/dlstatus/dlstatus"
    payload = {
        'command': 'dlstatus',
        'dln': dln,
        'issueDt': issue_dt,
        'submitBtn': 'Submit'
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Origin': 'https://apps.ilsos.gov',
        'Referer': 'https://apps.ilsos.gov/dlstatus/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    session = requests.Session()
    try:
        response = session.post(url, headers=headers, data=payload, timeout=50)
        response.raise_for_status()  # Raise an exception for bad status codes
        soup = BeautifulSoup(response.text, 'html.parser')
        status_row = soup.find_all("div", class_="row details")
        status_text = None
        for row in status_row:
            label = row.find("div", class_="col-md-4")
            if label and "Status" in label.text:
                value_div = row.find("div", class_="col-md-8")
                if value_div:
                    status_text = value_div.get_text(strip=True)
                    break
        return status_text, response.text
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error during request: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

def send_status_email(status: str, html_content: str):
    """Sends an email with the driving license status."""
    from_email = os.environ.get('FROM_EMAIL')
    to_email = os.environ.get('TO_EMAIL')
    sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')

    if not all([from_email, to_email, sendgrid_api_key]):
        print("Error: Please set FROM_EMAIL, TO_EMAIL, and SENDGRID_API_KEY environment variables.")
        return

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=f'Driving license tracking status: {status}',
        html_content=html_content
    )
    try:
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        print(f"Email sent with status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending email: {e}")

@app.get("/check_dl_status")
async def check_status():
    """Endpoint to check driver's license status (DLN from env) and send email."""
    # dln = os.environ.get('DLN')
    dln = 'd25279395148'
    if not dln:
        raise HTTPException(status_code=400, detail="DLN environment variable not set.")

    status_text, html_content = check_dl_status(dln)
    if status_text:
        # send_status_email(status_text, html_content)
        return {"status": "success", "message": f"Status: {status_text}. Email sent."}
    else:
        raise HTTPException(status_code=500, detail="Could not retrieve driver's license status.")
    
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to the Driving License Status Checker API!"}

# For local testing (optional)
if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    load_dotenv()
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
