#-*- coding: utf-8 -*-


"""APT data model"""


from couchdb.mapping import *
from couchdb import Database
import datetime


class APTEvent(Document):
    """A scheduled astronomic event"""

    ## Fields
    
    title = TextField()
    intro = TextField()
    stream = TextField()
    author = TextField()
    date_start = FloatField()
    date_end = FloatField()
    related_links = ListField(DictField(Mapping.build(
                url = TextField(),
                description = TextField())))
    comments = ListField(DictField(Mapping.build(
                text = TextField(),
                author = TextField(),
                published = DateTimeField(default=datetime.datetime.utcnow))))

    ## Views
    
    from_today = ViewField("events",
                           '''function (doc) {
                                  // return document if its date is ahead
                                  var today = new Date().getTime()/1000;
                                  if (today <= doc.date_start) {
                                      emit(doc._id, doc);
                                  }
                              }''')

    past_events = ViewField("events",
                           '''function (doc) {
                                  // return document if its date is in the past
                                  var today = new Date().getTime()/1000;
                                  if (today > doc.date_end) {
                                      emit(doc._id, doc);
                                  }
                              }''')

    in_progress = ViewField("events",
                           '''function (doc) {
                                  // return document if event is in progress
                                  var now = new Date().getTime()/1000;
                                  if (now > doc.date_start & now < doc.date_end) {
                                      emit(doc._id, doc);
                                  }
                              }''')

    ## Creation

    @classmethod
    def new(cls, **kwargs):
        """Create a new APTObject and set its id"""

        date_start = kwargs.get("date_start")
        date = datetime.date.fromtimestamp(date_start)
        title = kwargs.get("title")
        doc_id = date.isoformat() + "-" + title
        # Add an empty list for appending comments to it
        kwargs["comments"] = []
        self = cls(**kwargs)
        self.id = doc_id
        return self

    ## Utility

    def comments_by_date(self):
        return sorted(self.comments, key=lambda x: x["published"], reverse=True)

    def get_year(self):
        """Return the year for this event

        """
        return datetime.date.fromtimestamp(self.date_start).year

    def get_month(self):
        """Return the month for this event

        """
        return datetime.date.fromtimestamp(self.date_start).month

    def get_day(self):
        """Return the day for this event

        """
        return datetime.date.fromtimestamp(self.date_start).day

    def isoformat(self):
        """Return the start date in iso format

        """
        return datetime.datetime.fromtimestamp(self.date_start).isoformat()


database = Database("apt")
APTEvent.from_today.sync(database)
APTEvent.in_progress.sync(database)
APTEvent.past_events.sync(database)
