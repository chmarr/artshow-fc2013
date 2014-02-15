"""This piece of crap code is intended for Further Confusion to be able to integrate the separate
registration database into the Person model by matching up registration IDs and, if the names
are different, giving the option of selecting one name over the other. As is this is probably
only useful for Further Confusion, but can be the basis of a local solution.

Remember to set PYTHONPATH and DJANGO_SETTINGS_MODULE variables before running.

It has _NOT_ been updated to support the new peeps.Person model yet."""

import sys
import sqlite3

from django.core.management.base import BaseCommand

from artshow.models import Person


cli_defaults = {
    'rejects-file': None,
}

cli_usage = "%prog [options] input-file"
cli_description = """\
Integrate information from another database to help complete missing fields.
"""

from artshow.models import Bidder
import optparse
from artshow.unicodewriter import UnicodeDictReader


class NameDoesntMatch(Exception):
    pass


class Command(BaseCommand):
    args = "input-file"
    help = "Integrate information from registration database to complete missing files in Person entities."
    option_list = BaseCommand.option_list + (
        optparse.make_option("--errors-file", default=None, help="Errors file"),
        optparse.make_option("--encoding", default="utf-8", help="Encoding [%default]"),
        optparse.make_option("--print-db", default=False, action="store_true", help="print out the internal reg DB"),
        optparse.make_option("--dry-run", default=False, action="store_true", help="Don't actually save."),
    )
    error_file = None

    def write_error(self, msg, *params):
        if params:
            formatted_message = msg % params
        else:
            formatted_message = msg
        print >> sys.stderr, formatted_message
        if self.error_file:
            print >> self.error_file, formatted_message


    def find_reg_entry(self, reg_id):
        cur = self.db.cursor()
        cur.execute("""\
            select rl_first, rl_last, phone, address_1_line_1, address_1_line_2, address_1_city,
            address_1_state, address_1_zip, email_1 from reg where joined_reg_id=?""", (reg_id,))
        rows = cur.fetchall()
        if rows:
            return rows
        cur.execute("""\
            select rl_first, rl_last, phone, address_1_line_1, address_1_line_2, address_1_city,
            address_1_state, address_1_zip, email_1 from reg where joined_reg_id_2=?""", (reg_id,))
        return cur.fetchall()


    def integrate_db(self, dry_run=False):
        for p in Person.objects.all():
            entries = None
            if p.city and p.email:
                # The Person has enough information to be considered complete
                continue
            if not p.reg_id:
                self.write_error("%s is missing Reg ID", p)
            else:
                reg_id = p.reg_id.replace(' ','')
                entries = self.find_reg_entry(p.reg_id)
                # self.write_error("reg id %s found %d entries:", p.reg_id, len(entries))
                # for e in entries:
                #     self.write_error("    - %r", e)
                if len(entries) > 1:
                    self.write_error("%s has multiple possible matches:", p)
                    for e in entries:
                        self.write_error("    * %r", e)
                    entries = None
                elif not entries:
                    self.write_error("%s could not be found in database", p)
            if not entries:
                try:
                    b = p.bidder
                except Bidder.DoesNotExist:
                    self.write_error("    - is not a registered bidder, so is safe")
                else:
                    num_invoices = b.invoice_set.count()
                    if num_invoices == 0:
                        self.write_error("    - has no invoices, so is safe")
            else:
                rl_first, rl_last, phone, address_1_line_1, address_1_line_2, address_1_city,\
                    address_1_state, address_1_zip, email_1 = entries[0]
                self.write_error("Updating %s. Reg DB name: %s %s", p, rl_first, rl_last)
                p.address1 = address_1_line_1
                p.address2 = address_1_line_2
                p.city = address_1_city
                p.state = address_1_state
                p.postcode = address_1_zip
                p.email = email_1
                p.save()


    def load_reg_db(self, regfile, encoding):
        f = open(regfile)
        c = UnicodeDictReader(f, encoding=encoding)
        db = sqlite3.connect(":memory:")
        with db:
            cur = db.cursor()
            cur.execute("""\
        CREATE TABLE reg ( uid TEXT, rl_first TEXT, rl_last TEXT, fan_name TEXT, fc2014_reg_num TEXT, phone TEXT,
        phone_name TEXT, address_1_id TEXT, address_1_ship_name TEXT, address_1_line_1 TEXT, address_1_line_2 TEXT,
        address_1_city TEXT, address_1_state TEXT, address_1_zip TEXT, address_1_updated timestamp, email_1 TEXT,
        spam_ok_1 BOOLEAN, joined_reg_id TEXT, joined_reg_id_2 TEXT )
        """)
            for r in c:
                cur.execute("""\
        INSERT INTO reg VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                    r['UID'], r['rl_first'], r['rl_last'], r['fan_name'], r['FC2014_reg_num'], r['PH 1'],
                    r['PH 1 Name'], r['Address 1 ID'], r['Address 1 Ship to Name'], r['Address 1 Line 1'],
                    r['Address 1 Line 2'], r['Address 1 City'], r['Address 1 State'], r['Address 1 Zip'],
                    r['Address 1 Updated'], r['EMail 1'], r['Spam_Ok 1'],
                    r["UID"] + "-" + r["FC2014_reg_num"],
                    r["UID"] + r["FC2014_reg_num"],
                ))
        self.db = db


    def print_db(self):
        cur = self.db.cursor()
        cur.execute("select * from reg")
        for r in cur:
            print r


    def handle(self, *args, **options):
        if options['errors_file'] is not None:
            self.error_file = open(options['errors_file'], 'w')
        else:
            self.error_file = None

        self.load_reg_db(args[0], options['encoding'])

        if options['print_db']:
            self.print_db()
            return

        self.integrate_db(dry_run=options['dry_run'])

        if self.error_file is not None:
            self.error_file.close()
