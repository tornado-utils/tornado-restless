tornado-restless
================

Inspired on flask-restless this is a sqlalchemy restless api wrapper for tornado.

Flask-Restless provides a ReSTful JSON API for sqlalchemy.

Due to the fact that I'm a tornado fan I adapted Lincoln de Sousa's and Jeffrey Finkelstein's great library for using with tornado.

In many details this implementation follows the documentation of Flask-Restless:

https://flask-restless.readthedocs.org/en/latest/index.html

However there are some restrictions that are currently not implemented (like processors) or are slightly differ.

Copyright license
=================

flask-restless was dual licensed under the GNU Affero General Public License and 3-clause BSD License.

tornado-restless is licensed under the GNU Affero General Public License, for more information see the LICENSE.txt.

Installing
==========

tornado-restless was developed under python3.3, sqlalchemy0.8 and tornado3.0

It may work with previous python3.X versions and sqlalchemy 2.7 (and maybe even with python2.7) but I did not test it at all.

To install this library as an egg use:

    python setup.py install

Quickstart
==========

    import tornado.ioloop
    import tornado.web

    from tornado_restless import ApiManager
    from sqlalchemy import create_engine, schema, Column
    from sqlalchemy.types import Integer, String
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.declarative import declarative_base

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
       __tablename__ = 'persons'

       id = Column(Integer, primary_key=True)
       name = Column(String, unique=True)

    metadata.create_all(engine)

    # Create restless api handlers
    api = ApiManager(application=application, session=session)
    api.create_api(Person)

    if __name__ == "__main__":
       application.listen(8888)
       tornado.ioloop.IOLoop.instance().start()