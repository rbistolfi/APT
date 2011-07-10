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
    date_start = DateTimeField()
    date_end = DateTimeField()
    related_links = ListField(DictField(Mapping.build(
                url = TextField(),
                description = TextField())))
    comments = ListField(DictField(Mapping.build(
                text = TextField(),
                author = TextField(),
                published = DateTimeField(default=datetime.datetime.now))))

    ## Views
    
    from_today = ViewField("events",
                           '''function (doc) {
                                  // return document if its date is ahead
                                  var today = new Date();
                                  var ddate = new Date(doc.date_start);
                                  if (today <= ddate) {
                                      emit(doc._id, doc);
                                  }
                              }''')

    past_events = ViewField("events",
                           '''function (doc) {
                                  // return document if its date is in the past
                                  var today = new Date();
                                  var ddate = new Date(doc.date_end);
                                  if (today > ddate) {
                                      emit(doc._id, doc);
                                  }
                              }''')

    in_progress = ViewField("events",
                           '''function (doc) {
                                  // return document if event is in progress
                                  var now = new Date();
                                  var sdate = new Date(doc.date_start);
                                  var edate = new Date(doc.date_end);
                                  if (now > sdate & now < edate) {
                                      emit(doc._id, doc);
                                  }
                              }''')

    ## Creation

    @classmethod
    def new(cls, **kwargs):
        """Create a new APTObject and set its id"""

        date_start = kwargs.get("date_start")
        date = datetime.date(date_start.year, date_start.month, date_start.day)
        title = kwargs.get("title")
        doc_id = date.isoformat() + "-" + title
        # Add an empty list for appending comments to it
        kwargs["comments"] = []
        self = cls(**kwargs)
        self.id = doc_id
        return self


database = Database("apt")
APTEvent.from_today.sync(database)
APTEvent.in_progress.sync(database)
APTEvent.past_events.sync(database)
