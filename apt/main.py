#-*- coding: utf-8 -*-


"""APT web application"""


## Imports

from flask import *
from apt import *
import datetime, time, os

## Setup

app = Flask(__name__)

## View functions

@app.route("/")
def index():
    """Web application home page.

    If there is an event in progress, redirect to it.
    Show a list of future events otherwise.

    """
    current_event = APTEvent.in_progress(database)
    if current_event.total_rows:
        return render_template("event.html", event=current_event.rows.pop())
    future_events = APTEvent.from_today(database)
    return render_template("index.html", events=future_events)


@app.route("/<int:year>/<int:month>/<int:day>/<title>", methods=["get", "post"])
def event(year, month, day, title):
    """Return the event for the given date and title.
    If method is POST, create a new event and store it.

    """
    # handle POST request
    if request.method == "POST":

        # get values POSTed by the user
        get = request.form.get
        hour_start = int(get("hour_start", 0))
        mins_start = int(get("mins_start", 0))
        seconds_start = int(get("seconds_start", 0))
        year_end = int(get("year_end", 2011))
        month_end = int(get("month_end", 1))
        day_end = int(get("day_end", 20))
        hour_end = int(get("hour_end", 0))
        mins_end = int(get("mins_end", 0))
        seconds_end = int(get("seconds_end", 0))

        # datetime objects
        date_start = datetime.datetime(year, month, day, hour_start, mins_start, seconds_start)
        date_end = datetime.datetime(year_end, month_end, day_end, hour_end, mins_end, seconds_end)

        # build the event object
        event = APTEvent.new(
            title = title,
            intro = get("intro"),
            stream = get("stream"),
            author = get("author"),
            date_start = date_start,
            date_end = date_end)
        event.store(database)
        
        # redirect to the created resource
        return redirect("/%s/%s/%s/%s" % (year, month, day, title))

    # handle GET request
    doc = datetime.date(year, month, day).isoformat() + "-" + title
    event = APTEvent.load(database, doc)
    if not event:
        return abort(404)
    return render_template("event.html", event=event)


@app.route("/<year>/<month>/<day>/<title>/new")
def new_event(year, month, day, title):
    """Render a form for creating a new event

    """
    return render_template("new_event.html", year=year, month=month, day=day, title=title)


@app.route("/<int:year>/<int:month>/<int:day>/<title>/add_comment", methods=["GET", "POST"])
def add_comment(year, month, day, title):
    """Fetch the document and append the comment to its comments list.
    A comment is a dictionary with an "author" and a "text" key. A "published" key is
    automaticaly generated with the current timestamp.

    """
    def randomize():
        """Create a random string of 6 characters"""
        import random
        from string import uppercase, lowercase, digits
        s = list(uppercase + lowercase + digits)
        random.shuffle(s)
        return "".join(s[:6])
    
    response_data = None
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'connect':
            response_data = [True, {'name': 'user%s' % randomize()}]
        elif action == 'publish':
            doc_id = datetime.date(year, month, day).isoformat() + "-" + title
            event = APTEvent.load(database, doc_id)
            if not event:
                return abort(404)
            comment_text = json.loads(request.form.get("payload"))["text"]
            comment = dict(author=request.form.get("originator"), text=comment_text)
            event.comments.append(comment)
            event.store(database)
            response_data = [True, {}]
            print "ADDED:", doc_id, comment, event
        else:
            response_data = [True, {}]
    return Response(json.dumps(response_data))


if __name__ == "__main__":
    app.run(host="10.0.0.3", debug=True)
