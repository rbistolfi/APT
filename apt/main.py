#-*- coding: utf-8 -*-


"""APT web application"""


## Imports

from flask import *
from flaskext.couchdb import CouchDBManager
from flaskext.sijax import init_sijax, route
from apt import *
import datetime, time, os


## Setup

app = Flask(__name__)
app.config["SIJAX_STATIC_PATH"] = os.path.join('.', os.path.dirname(__file__), 'static/js/sijax/')
app.config["COUCHDB_SERVER"] = "http://0.0.0.0:5984"
app.config["COUCHDB_DATABASE"] = "caleu-cheques"
manager = CouchDBManager()
manager.setup(app)
init_sijax(app)

## View functions

@app.route("/")
def index():
    """Web application home page.

    If there is an event in progress, redirects to it.
    Shows a list of future events otherwise.

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
    g.sijax.set_request_uri("/get_comments")
    # handle POST request
    if request.method == "POST":

        # get values POSTed by the user
        get = request.form.get
        mins_start = int(get("mins_start", 0))
        seconds_start = int(get("seconds_start", 0))
        year_end = int(get("year_end", 2011))
        month_end = int(get("month_end", 1))
        day_end = int(get("day_end", 20))
        hour_end = int(get("hour_end", 0))
        mins_end = int(get("mins_end", 0))
        seconds_end = int(get("seconds_end", 0))

        # datetime objects
        date_start = datetime.datetime(year, month, day, mins_start, seconds_start)
        date_end = datetime.datetime(year_end, month_end, day_end, mins_end, seconds_end)

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


@app.route("/<int:year>/<int:month>/<int:day>/<title>/add_comment", methods=["post"])
def add_comment(year, month, day, title):
    """Fetch the document and append the comment to its comments list.
    A comment is a dictionary with an "author" and a "text" key. A "published" key is
    automaticaly generated with the current timestamp.

    """
    doc_id = datetime.date(year, month, day).isoformat() + "-" + title
    event = APTEvent.load(database, doc_id)
    if not event:
        return abort(404)
    comment = dict(author=request.form.get("author"), text=request.form.get("text"))
    event.comments.append(comment)
    event.store(database)
    return redirect("/%s/%s/%s/%s#comments" % (year, month, day, title))


@route(app, "/get_comments", methods=["POST"])
def test():
    if g.sijax.is_sijax_request:
        # The request looks like a valid Sijax request
        # Let's register the handlers and tell Sijax to process it
        g.sijax.register_comet_callback('get_comments', comet_comment_handler)

        return g.sijax.process_request()


def comet_comment_handler(obj_response, sleep_time, event_id):

    event = APTEvent.load(database, event_id)
    sent = set()
    for comment in event.comments:
        if comment["text"] not in sent:
            obj_response.html_prepend('#comments ul', '<li>%s</li>' % comment["text"])
            sent.add(comment["text"])
            print comment, sent
            yield event.comments[-1]
        time.sleep(sleep_time)
    """    
    for i in range(6):
        obj_response.html_prepend('#comments ul', '<li>%s</li>' % i)

        # Yielding tells Sijax to flush the data to the browser.
        # This only works for Streaming functions (Comet or Upload)
        # and would not work for normal Sijax functions
        yield obj_response

        if i != 5:"""

    
if __name__ == "__main__":
    app.run(debug=True)
