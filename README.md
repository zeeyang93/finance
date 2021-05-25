# Finance

A finance website that lets you quote, buy and sell US listed stocks. 
Users are given 10 000 credits upon signup, and buy/sell stocks to see how their portfolio performs.

You can try this on Heroku website, but code is not optimised for the page. https://finance5461.herokuapp.com/

## Instructions to use locally: 

To install pip, run:

`sudo apt install python3-pip`

To install Flask, run:

`sudo apt install python3-flask`

To install this project's dependecies, run:

`pip3 install -r requirements.txt`

Define the correct file as the default Flask application:

Unix Bash (Linux, Mac, etc.):

`export FLASK_APP=application.py`

Windows CMD:

`set FLASK_APP=application.py`

Windows PowerShell:

`$env:FLASK_APP = "application.py"`

Run Flask and you're good to go!

`python -m flask run`