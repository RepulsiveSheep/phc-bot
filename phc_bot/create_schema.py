#!/usr/bin/env python3

from db import db, Base

db.create_tables(Base.__subclasses__())
