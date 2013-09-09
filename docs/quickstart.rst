.. module:: quickstart

:mod:`quickstart` -- Quickstart
-------------------------------

Tornado Restless creates for each sqlalchemy model an tornado URLSpec route that will handle request made to the model.
The following example will create a tornado app, init sqlalchemy with a sqlite memory database and provide own route for the Person model on :8888/api/persons.::

    import tornado.ioloop
    import tornado.web

    from sqlalchemy import create_engine, schema, Column
    from sqlalchemy.types import Integer, String
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.declarative import declarative_base

    from tornado_restless import ApiManager

    # Init Tornado Application
    application = tornado.web.Application([])

    # Init SQLAlchemy
    engine = create_engine('sqlite:///:memory:')
    metadata = schema.MetaData()
    Session = sessionmaker(bind=engine)
    Base = declarative_base(metadata=metadata)
    session = Session()

    # Create some model
    class Person(Base):
       _\_tablename__ = 'persons'

       id = Column(Integer, primary_key=True)
       name = Column(String, unique=True)

    metadata.create_all(engine)

    # Create restless api handlers
    api = ApiManager(application=application, session_maker=Session)
    api.create_api(Person)

    if __name__ == "__main__":
       application.listen(8888)
       tornado.ioloop.IOLoop.instance().start()

