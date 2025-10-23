# modules/home.py
#
# Description:
# This module handles the logic for the homepage of the P1-meter web application.
# It renders the home.html template with a welcome message.
#
# Version History:
# Version 1.0 (2025-10-22): Initial version for modular homepage.

from flask import render_template

def render_home():
    return render_template('home.html')