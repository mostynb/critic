# -*- mode: python; encoding: utf-8 -*-
#
# Copyright 2014 the Critic contributors, Opera Software ASA
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations under
# the License.

import sys
import psycopg2
import json
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("--uid", type=int)
parser.add_argument("--gid", type=int)

arguments = parser.parse_args()

os.setgid(arguments.gid)
os.setuid(arguments.uid)

data = json.load(sys.stdin)

import configuration

db = psycopg2.connect(**configuration.database.PARAMETERS)
cursor = db.cursor()

try:
    # Make sure the table doesn't already exist.
    cursor.execute("SELECT 1 FROM useremails")

    # Above statement should have thrown a psycopg2.ProgrammingError, but it
    # didn't, so just exit.
    sys.exit(0)
except psycopg2.ProgrammingError: db.rollback()
except: raise

# Create the table.
cursor.execute("""CREATE TABLE useremails
                    ( id SERIAL PRIMARY KEY,
                      uid INTEGER NOT NULL REFERENCES users ON DELETE CASCADE,
                      email VARCHAR(256) NOT NULL,
                      verified BOOLEAN,
                      verification_token VARCHAR(256),

                      UNIQUE (uid, email) )""")

# Create records for all current email addresses in the system.  Set verified to
# NULL which means the addresses can be used, but that they haven't gone through
# the verification process.
cursor.execute("""INSERT INTO useremails (uid, email)
                       SELECT id, email
                         FROM users
                        WHERE email IS NOT NULL""")

# Drop the old 'users.email' column.
cursor.execute("ALTER TABLE users DROP email")

# And create a new one based on the information we copied over to the new table.
cursor.execute("ALTER TABLE users ADD email INTEGER REFERENCES useremails")
cursor.execute("SELECT id, uid FROM useremails")
cursor.executemany("UPDATE users SET email=%s WHERE id=%s", cursor.fetchall())

db.commit()
db.close()
