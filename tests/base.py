#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
"""
    
"""
from datetime import datetime
from json import loads
import logging
from threading import Thread
from urllib.parse import urljoin
import os

from flask import Flask
import requests
from sqlalchemy import create_engine, schema, Column, Integer, String, ForeignKey, DateTime, func, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
import tornado.web
import tornado.ioloop
from flask.ext.restless import APIManager as FlaskRestlessManager

from tornado_restless import ApiManager as TornadoRestlessManager


__author__ = 'Martin Martimeo <martin@martimeo.de>'
__date__ = '21.08.13'


class TestBase(object):
    """
        Base class for all tests

        sets up tornado_restless and flask_restless
    """

    config = {
        'dns': 'sqlite:///test.lite',
        'encoding': 'utf-8',
        'tornado': {'port': 4091}
    }

    def setUp(self):

        self.setUpAlchemy()
        self.setUpModels()
        self.setUpFlask()
        self.setUpTornado()
        self.setUpRestless()

    def setUpFlask(self):
        """
            Create Flask application
        """

        app = Flask(__name__)
        app.config['DEBUG'] = True
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = self.config['dns']

        self.flask = app

    def setUpTornado(self):
        """
            Create Tornado application
        """
        app = tornado.web.Application([])
        app.listen(self.config['tornado']['port'])
        self.tornado = app

    def setUpRestless(self):
        """
            Create blueprints
        """
        Session = self.alchemy['Session']

        self.api = {'tornado': TornadoRestlessManager(application=self.tornado, Session=Session),
                    'flask': FlaskRestlessManager(self.flask, session=Session())}

        for model in self.models.values():
            self.api['tornado'].create_api(model)
            self.api['flask'].create_api(model)

        class TornadoThread(Thread):

            def run(self):
                try:
                    tornado.ioloop.IOLoop.instance().start()
                finally:
                    del self._target

        self.threads = {'tornado': TornadoThread(target=self),
                        'flask': self.flask.test_client()}
        self.threads['tornado'].start()

    def curl_tornado(self, url, method='get', assert_for=200, **kwargs):
        url = urljoin('http://localhost:%u' % self.config['tornado']['port'], url)
        r = getattr(requests, method)(url, **kwargs)
        if assert_for == 200:
            r.raise_for_status()
        else:
            assert assert_for == r.status_code
        try:
            return r.json()
        finally:
            r.close()

    def curl_flask(self, url, method='get', assert_for=200, **kwargs):
        r = getattr(self.threads['flask'], method)(url, **kwargs)
        assert assert_for == r.status_code
        return loads(r.data.decode(self.config['encoding']))

    def setUpAlchemy(self):
        """
            Init SQLAlchemy engine
        """
        engine = create_engine(self.config['dns'])
        metadata = schema.MetaData()
        Session = scoped_session(sessionmaker(bind=engine))
        Base = declarative_base(metadata=metadata)

        self.alchemy = {'Base': Base, 'Session': Session, 'engine': engine}

    def setUpModels(self):
        """
            Create models
        """

        Base = self.alchemy['Base']
        Session = self.alchemy['Session']
        engine = self.alchemy['engine']

        class Person(Base):
            __tablename__ = 'persons'

            _id = Column(Integer, primary_key=True)
            name = Column(String, unique=True)
            birth = Column(DateTime)

            @hybrid_property
            def age(self):
                return (datetime.now() - self.birth).days / 365.25

            @age.expression
            def age(self):
                return func.now() - self.birth

            def __init__(self, name, age):
                self.name = name
                self.birth = datetime.now().replace(year=datetime.now().year - age)

        class Computer(Base):
            __tablename__ = 'computers'

            _id = Column(Integer, primary_key=True)

            cpu = Column(Float)
            ram = Column(Float)

            _user = Column(ForeignKey(Person._id))
            user = relationship(Person, backref='computers')

        Base.metadata.create_all(engine)

        self.models = {'Person': Person, 'Computer': Computer}

        anastacia = Person('Anastacia', 44)
        bernd = Person('Bernd', 48)
        claudia = Person('Claudia', 20)
        dennise = Person('Dennise', 14)
        emil = Person('Emil', 81)

        self.persons = {p.name: p for p in [anastacia, bernd, claudia, dennise, emil]}

        a1 = Computer(user=anastacia, cpu=3.2, ram=4)
        a2 = Computer(user=anastacia, cpu=12, ram=4)
        b1 = Computer(user=bernd, cpu=12, ram=8)
        e1 = Computer(user=emil, cpu=1.6, ram=2)
        e2 = Computer(user=emil, cpu=3.4, ram=4)

        self.computers = [a1, a2, b1, e1, e2]

        session = Session()
        session.add_all(self.persons.values())
        session.add_all(self.computers)
        session.commit()

    def tearDown(self):

        self.tearDownTornado()
        self.tearDownAlchemy()

    def tearDownAlchemy(self):

        Base = self.alchemy['Base']
        engine = self.alchemy['engine']

        Base.metadata.drop_all(engine)

        del self.alchemy

        os.unlink('test.lite')

    def tearDownTornado(self):

        self.config['tornado']['port'] += 1

        def stop():
            """
                Stop the IOLoop
            """
            tornado.ioloop.IOLoop.instance().stop()

        tornado.ioloop.IOLoop.instance().add_callback(stop)
        self.threads['tornado'].join()

    def subsetOf(self, a, b):
        """
            Test wether a is an subset of b (or b an superset of a)
        """

        if type(a) != type(b):
            logging.error("Type not equal of a,b")
            return False

        if isinstance(a, dict) or hasattr(a, "items"):
            for (key, value) in a.items():
                if not self.subsetOf(value, b[key]):
                    return False
            else:
                return True

        if isinstance(a, list) or hasattr(a, "__iter__"):
            for element in a:
                if element not in b:
                    return False
            else:
                return True

        return a == b


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    base = TestBase()
    base.setUp()
    try:
        base.threads["tornado"].join()
    except KeyboardInterrupt:
        base.tearDown()
