from django.core.management.base import BaseCommand, CommandError
from artshow.models import *
from optparse import make_option
import sys
from django.conf import settings
from itertools import izip_longest

PIECES_PER_CONTROL_FORM = 20


def auto_compress(s, std_width):
    if type(s) == unicode:
        s = s.encode('ascii', 'replace')
    else:
        s = str(s)

    if len(s) <= std_width - 2:
        return " %-*s " % ( std_width - 2, s )

    compressed_width, extras = divmod((std_width * 5), 3)
    # Extras is how many 60ths of an inch to add, will only be 0, 1 or 2

    # Condensed, Cancel Condensed
    data = "\x0f %-*s \x12" % ( compressed_width - 2, s )
    if extras:
        # Set Relative Horizontal Print Position, in 1/180ths (in LQ mode)
        data += "\x1b\\" + chr(extras * 3) + chr(0)

    return data


def grouper(n, iterable, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)


def generate_lq570(artist, pieces, data):
    for piecegroup in grouper(PIECES_PER_CONTROL_FORM, pieces):

        data.write("\x1b0") # Set 1/8 inch spacing
        data.write("\x1bM") # Set 12 CPI

        # Lines 1-4
        for i in range(2):
            data.write("\n")

        # Line 5
        # \x0e \x14 double width printing on/off
        # \x1b E \x1b F bold on/off
        data.write("%26s%s%43s\x0e\x1bE%s\x1bF\x14\n" % (
            " ", auto_compress(settings.ARTSHOW_SHOW_YEAR, 9), " ", str(artist.artistid) ))
        data.write("\n")
        data.write("\n")

        # Line 8
        data.write("%17s%s%12s%s\n" % (
            " ", auto_compress(artist.person.name, 27), " ", auto_compress(artist.person.email, 36) ))
        data.write("\n")
        data.write("\n")

        # Line 11
        data.write("%17s%s\n" % ( " ", auto_compress(artist.artistname(), 27) ))
        data.write("\n")
        data.write("\n")

        # Line 14
        data.write("%17s%s\n" % ( " ", auto_compress(" ".join([artist.person.address1, artist.person.address2]), 27) ))
        data.write("\n")
        data.write("\n")

        # Line 17
        data.write("%17s%s\n" % ( " ", auto_compress(artist.person.city, 27) ))
        data.write("\n")
        data.write("\n")

        # Line 20
        data.write("%17s%s\n" % ( " ", auto_compress(artist.person.state, 27) ))
        data.write("\n")
        data.write("\n")

        # Line 23
        data.write("%17s%s\n" % ( " ", auto_compress(artist.person.postcode, 27) ))
        data.write("\n")
        data.write("\n")

        # Line 26
        data.write("%17s%s\n" % ( " ", auto_compress(artist.person.country, 27) ))
        data.write("\n")
        data.write("\n")

        # Line 29
        data.write("%17s%s\n" % ( " ", auto_compress(artist.person.phone, 27) ))

        # Line 30-35
        for i in range(6):
            data.write("\n")

        # Line 36-95
        for piece in piecegroup:
            if piece is not None:
                # \x1bE and \x1bF = Bold on/off
                data.write("    %4d %s   %s   %7s  %7s\n" % (
                    piece.pieceid, auto_compress(piece.name, 36), piece.adult and "\x1bEY\x1bF" or "N",
                    piece.min_bid and ("%7d" % piece.min_bid) or "  NFS  ",
                    piece.buy_now and ("%7d" % piece.buy_now) or "  N/A  " ))
                data.write("\n")

        data.write("\x0c") # Form Feed


class Command(BaseCommand):
    args = 'artistid ... '
    help = "Generate LQ570 code for control forms"
    option_list = BaseCommand.option_list + (
        make_option("--marked", action="store_true", default=False, help="Print only pieces marked for printing"),
    )

    def print_marked_pieces(self):
        artists = Artist.objects.order_by('artistid')
        for a in artists:
            pieces = a.piece_set.filter(control_form_printing=Piece.PrintingToBePrinted).order_by('pieceid')
            if pieces.count() != 0:
                generate_lq570(a, pieces, sys.stdout)


    def print_specified_artists(self, artist_ids):
        for id in artist_ids:
            try:
                artist = Artist.objects.get(artistid=id)
            except Artist.DoesNotExist:
                print >> sys.stderr, "Artist with ID %d does not exist" % id
                continue
            if artist.piece_set.count() == 0:
                print >> sys.stderr, "Artist %s has no pieces. Not printing." % artist
                continue
            generate_lq570(artist, artist.piece_set.order_by('pieceid'), sys.stdout)


    def handle(self, *args, **options):
        artist_ids = [int(x) for x in args]

        if options['marked']:
            self.print_marked_pieces()
        else:
            self.print_specified_artists(artist_ids)
