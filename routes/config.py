import os
from dotenv import load_dotenv

load_dotenv() # read .env into os.environ

SECRET_KEY = os.environ["SECRET_KEY"] 

#email (SMTP) settings
MAIL_SERVER=os.environ.get("MAIL_SERVER")
MAIL_PORT=int(os.environ.get("MAIL_PORT", 587))
MAIL_USE_TLS=True                  
MAIL_USERNAME=os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD")

#validity of password reset-link
RESET_MAX_AGE = 15 * 60