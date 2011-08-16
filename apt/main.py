#-*- coding: utf-8 -*-


"""APT web application"""


## Imports

from flask import *
from flaskext.openid import OpenID
from apt import *
from urllib import unquote
from time import mktime
import datetime, time, os, uuid


## Setup

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24)
oid = OpenID(app, "./openid_store")


## Hooks

@app.before_request
def lookup_current_user():
    """Setup context for openid

    """
    g.user = None
    if 'openid' in session:
        g.user = session["openid"]
        print session

        
## View functions
# User handling
        
@app.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    if g.user is not None:
        return redirect(oid.get_next_url())
    if request.method == 'POST':
        openid = request.form.get('openid')
        if openid:
            return oid.try_login(openid, ask_for=['email', 'fullname',
                                                  'nickname'])
    return render_template('login.html', next=oid.get_next_url(),
                           error=oid.fetch_error())


@oid.after_login
def create_or_login(resp):
    """Login handler for OpenID

    """
    session['openid'] = resp
    g.uid = session['uid'] = uuid.uuid4()
    session.premanent = True
    user = resp
    if user is not None:
        flash(u'Successfully signed in')
        g.user = user
    return redirect(oid.get_next_url()) 


@app.route('/logout')
def logout():
    """Destroy the session

    """
    session.pop('openid', None)
    session.pop('uid', None)
    session.permanent = False
    flash(u'You were signed out')
    return redirect(oid.get_next_url())


# Application

@app.route("/")
def index():
    """Web application home page.

    If there is an event in progress, redirect to it.
    Show a list of future events otherwise.

    """
    # check for a running event
    current_event = APTEvent.in_progress(database)
    if current_event.total_rows:
        event = current_event.rows.pop()
    else:
        event = None
    # lookup future and past events
    future_events = APTEvent.from_today(database)
    past_events = APTEvent.past_events(database)
    return render_template("index.html", event=event, future_events=future_events, past_events=past_events)


@app.route("/<int:year>/<int:month>/<int:day>/<title>", methods=["get", "post"])
def event(year, month, day, title):
    """Return the event for the given date and title.
    If method is POST, create a new event and store it.

    """
    # handle POST request
    if request.method == "POST":

        # check login
        if not g.user:
            return redirect(url_for("login"))
    
        # get values POSTed by the user
        get = request.form.get

        # override default values with those from the form
        title = get("title")
        
        # parse date input fields data
        datetime_start = get("datetime_start")
        date, time = datetime_start.split()
        month, day, year = [ int(i) for i in date.split("/") ]
        hour_start, mins_start = [ int(i) for i in time.split(":") ]

        datetime_end = get("datetime_end")
        date, time = datetime_end.split()
        month_end, day_end, year_end = [ int(i) for i in date.split("/") ]
        hour_end, mins_end = [ int(i) for i in time.split(":") ]
        
        # datetime objects
        date_start = datetime.datetime(year, month, day, hour_start, mins_start)
        date_end = datetime.datetime(year_end, month_end, day_end, hour_end, mins_end)

        # get related links
        urls = [ get("rel_link%s" % i) for i in xrange(1,5) ]
        descs = [ get("desc_link%s" % i) for i in xrange(1,5) ]
        links = [ dict(url=url, description=desc) for url, desc in zip(urls, descs) if url ]
        
        # build the event object
        event = APTEvent.new(
            title = title,
            intro = get("intro"),
            stream = get("stream"),
            author = get("author"),
            date_start = mktime(date_start.timetuple()),
            date_end = mktime(date_end.timetuple()),
            related_links = links)
        event.store(database)
        
        # redirect to the created resource
        return redirect("/%s/%s/%s/%s" % (year, month, day, title))

    # handle GET request
    # unquote wont handle unicode properly
    title = title.encode("utf-8")
    while "%" in title:
        # I know. Wtf, Openid is quoting the url more than once
        title = unquote(title)
    doc = datetime.date(year, month, day).isoformat() + "-" + title
    event = APTEvent.load(database, doc)
    if not event:
        # we do this just to get the werkzeug debugger
        raise Exception("404")
    return render_template("event.html", event=event)


@app.route("/<year>/<month>/<day>/<title>/new")
def new_event(year, month, day, title):
    """Render a form for creating a new event

    """
    # check login
    if not g.user:
        return redirect(url_for("login"))
    
    return render_template("new_event.html", year=year, month=month, day=day, title=title)


@app.route("/add_comment", methods=["GET", "POST"])
def add_comment():
    """Fetch the document and append the comment to its comments list.
    A comment is a dictionary with an "author" and a "text" key. A "published" key is
    automaticaly generated with the current timestamp.

    """

    response_data = None
    if request.method == 'POST':
        # handle the different actions defined by hookbox protocol
        action = request.form.get('action')
        if action == 'connect':
            # assign a nickname to the new user on connect
            if g.user:
                nickname = g.user.nickname or g.user.fullname or g.user.email
            else:
                nickname = 'user_%s' % random_nick()
            response_data = [True, {'name': nickname}]
        elif action == 'publish':
            print "PUBLISH:: ", session
            print "PUBLISH:: ", g
            data = json.loads(request.form.get("payload"))
            doc_id = data["event"]
            event = APTEvent.load(database, doc_id)
            if not event:
                return abort(404)
            comment_text = data["text"]
            comment = dict(author=request.form.get("originator"), text=comment_text)
            event.comments.append(comment)
            event.store(database)
            response_data = [True, {}]
        else:
            response_data = [True, {}]
    return Response(json.dumps(response_data))


## Filters

@app.template_filter("format_title")
def format_title(title):
    """Replace _ with a space

    """
    return title.replace("_", " ")


## Helpers

def random_nick():
    """Create a random string of 6 characters

    """
    import random
    from string import uppercase, lowercase, digits
    s = list(uppercase + lowercase + digits)
    random.shuffle(s)
    return "".join(s[:6])


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
