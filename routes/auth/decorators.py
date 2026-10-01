from functools import wraps
from flask import redirect, url_for, session, flash

def login_required(view): #wraps route so it only runs for logged in users
    @wraps(view) #keeps og function name
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

#prevent back button from showing cached protected page after logout
def no_cache_for_logged_in_pages(response):
    if "user_id" in session:
        response.headers["Cache-Control"] = "no-store" #tells browser not to keep copy
    return response