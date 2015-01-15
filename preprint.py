#! /usr/bin/env python

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, TA_CENTER, TA_LEFT, ParagraphStyle
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.pagesizes import letter
from django.conf import settings
from itertools import izip_longest
from pdfrw import PdfReader
from pdfrw.buildxobj import pagexobj
from pdfrw.toreportlab import makerl
from cgi import escape
from logging import getLogger

logger = getLogger(__name__)

PIECES_PER_CONTROL_FORM = 20

default_style = ParagraphStyle ( "default_style", fontName="Helvetica", alignment=TA_CENTER, allowWidows=0, allowOrphans=0 )
left_align = ParagraphStyle ( "left_align", fontName="Helvetica", alignment=TA_LEFT, allowWidows=0, allowOrphans=0 )

left_align_style = ParagraphStyle ( "left_align_style", fontName="Helvetica", alignment=TA_LEFT, allowWidows=0, allowOrphans=0 )

barcode_style = ParagraphStyle ( "barcode_style", fontName="PrecisionID C39 04", alignment=TA_CENTER, allowWidows=0, allowOrphans=0 )

piece_sticker_style = ParagraphStyle ( "piece_sticker_style", fontName="Times-Roman", alignment=TA_CENTER, allowWidows=0, allowOrphans=0, fontSize=12, leading=12 )

def draw_msg_into_frame ( frame, canvas, msg, font_size, min_font_size, style=default_style, escape_text=True ):
    # From the largest to the smallest font sizes, try to flow the message
    # into the given frame.
    if escape_text:
        msg = escape(msg)
        msg = msg.replace('\n','<br/>')
    for size in range ( font_size, min_font_size-1, -1 ):
        current_style = ParagraphStyle ( "temp_style", parent=style, fontSize=size, leading=size )
        story = [ Paragraph ( msg, current_style ) ]
        frame.addFromList ( story, canvas )
        if len(story) == 0: break  # Story empty, so all text was sucessfully flowed
    else:
        # We've run out font sizing options, so clearly the story/text is too big to flow in.
        raise Exception ( "Could not flow text into box." )
        

def text_into_box ( canvas, msg, x0, y0, x1, y1, fontName="Helvetica", fontSize=18, minFontSize=6, units=inch, style=default_style, escape_text=True ):
    frame = Frame ( x0*units, y0*units, (x1-x0)*units, (y1-y0)*units, leftPadding=2, rightPadding=2, topPadding=0, bottomPadding=4, showBoundary=0 )
    draw_msg_into_frame ( frame, canvas, msg, fontSize, minFontSize, style=style, escape_text=escape_text )
    

def bid_sheets ( pieces, output ):

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont(*settings.ARTSHOW_BARCODE_FONT))

    c = Canvas(output,pagesize=letter)

    pdf = PdfReader ( settings.ARTSHOW_BLANK_BID_SHEET )
    xobj = pagexobj ( pdf.pages[0] )
    rlobj = makerl ( c, xobj )
    
    nfs_pdf = PdfReader ( settings.ARTSHOW_BLANK_NFS_SHEET )
    nfs_xobj = pagexobj ( nfs_pdf.pages[0] )
    nfs_rlobj = makerl ( c, nfs_xobj )

    sheet_offsets = [
        (0,5.5),
        (4.25,5.5),
        (0,0),
        (4.25,0),
        ]

    sheets_per_page = len(sheet_offsets)
    sheet_num = 0
    pieceiter = iter(pieces)
    last_artist = None
    
    try:
        piece = pieceiter.next ()
        while True:
            try:
                for sheet_num in range(sheets_per_page):
                    if piece.artist != last_artist and sheet_num != 0:
                        continue
                    c.saveState ()
                    c.translate ( sheet_offsets[sheet_num][0]*inch, sheet_offsets[sheet_num][1]*inch )
                    if piece.not_for_sale:
                        c.doForm ( nfs_rlobj )
                    else:
                        c.doForm ( rlobj )
                    c.saveState ()
                    c.setLineWidth ( 4 )
                    c.setFillColorRGB ( 1, 1, 1 )
                    c.setStrokeColorRGB ( 1, 1, 1 )
                    c.roundRect ( 1.1875*inch, 4.4375*inch, 1.75*inch, 0.5*inch, 0.0675*inch, stroke=True, fill=True )
                    c.restoreState ()
                    text_into_box ( c, u"*A"+unicode(piece.artist.artistid)+u"P"+unicode(piece.pieceid)+u"*", 1.3125, 4.6, 2.8125, 4.875, fontSize=13, style=barcode_style )
                    text_into_box ( c, "Artist "+unicode(piece.artist.artistid), 1.25, 4.4375, 2.0, 4.625 )
                    text_into_box ( c, "Piece "+unicode(piece.pieceid), 2.125, 4.4375, 2.875, 4.625 )
                    text_into_box ( c, piece.artist.artistname(), 1.125, 4.125, 3.875, 4.375 )
                    text_into_box ( c, piece.name, 0.75, 3.8125, 3.875, 4.0625 )
                    if piece.not_for_sale:
                        text_into_box ( c, piece.media, 0.875, 3.5, 2.375, 3.75 )
                    else:
                        text_into_box ( c, piece.media, 0.875, 3.5, 3.875, 3.75 )
                        text_into_box ( c, piece.not_for_sale and "NFS" or unicode(piece.min_bid), 3.25, 2.625, 3.75, 3.0 )
                        text_into_box ( c, piece.buy_now and unicode(piece.buy_now) or "N/A", 3.25, 1.9375, 3.75, 2.3125 )
                        text_into_box ( c, "X", 3.375, 0.375, 3.5625, 0.675, style=left_align_style, fontSize=16 )      
                    c.restoreState ()
                    last_artist = piece.artist
                    piece = pieceiter.next ()
            finally:
                c.showPage ()
    except StopIteration:
        pass

    c.save ()

    
    

def mailing_labels ( artists, output ):

    c = Canvas(output,pagesize=letter)
    
    label_number = 0
    
    for artist in artists:
        column = label_number%3
        row = label_number/3
        c.saveState ()
        c.translate ( 3/16.0*inch + column*(2+3/4.0)*inch, (9+1/2.0)*inch - row*inch )
        text_into_box ( c, artist.person.get_mailing_label(), 0.1, 0.0, 2.5, 0.85, fontSize=14, style=left_align )
        c.restoreState ()
        
        label_number += 1
        if label_number == 30:
            c.showPage ()
            label_number = 0
            
    if label_number != 0:
        c.showPage ()
    c.save ()


def grouper(n, iterable, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)
    
def yn ( b ):
    return "Y" if b else "N"
    
def priceornfs ( nfs, price ):
    return "NFS" if nfs else unicode(price)
    
def buynoworna ( price ):
    return "N/A" if price is None else unicode(price)
    
    
class group_pieces_by_artist_and_n ( object ):
    def __init__ ( self, pieces, n ):
        self.pieces = iter(pieces)
        self.n = n
        self.current_artist = None
        self.current_piece = None
    def __iter__ ( self ):
        return self
    def next ( self ):
        if self.current_piece is None:
            self.current_piece = next(self.pieces) # Exit on Stop Iteration
        return ( self.current_piece.artist, self._grouper() )
    def _grouper ( self ):
        i = 0
        self.current_artist = self.current_piece.artist if self.current_piece is not None else None
        while i < self.n and self.current_piece is not None and self.current_piece.artist == self.current_artist:
            yield self.current_piece
            self.current_piece = next(self.pieces,None)
            i += 1


def control_forms ( pieces, output ):
    """Write a pdf file to 'output',
    and generate control forms (one or more pages each) for 'pieces'.
    """
    c = Canvas ( output, pagesize=letter )
    pdf = PdfReader ( settings.ARTSHOW_BLANK_CONTROL_FORM )
    xobj = pagexobj ( pdf.pages[0] )
    rlobj = makerl ( c, xobj )
    for artist, piecegroup in group_pieces_by_artist_and_n ( pieces, PIECES_PER_CONTROL_FORM ):
        c.doForm ( rlobj )
        text_into_box ( c, settings.ARTSHOW_SHOW_YEAR, 2.4, 10.3, 3.05, 10.6 )
        text_into_box ( c, unicode(artist.artistid), 6.6, 10.25, 8.0, 10.5 )
        text_into_box ( c, artist.person.name, 1.7, 9.875, 4.1, 10.225, style=left_align_style )
        text_into_box ( c, artist.artistname(), 1.7, 9.5,    4.1, 9.85, style=left_align_style )
        text_into_box ( c, artist.person.address1 + " " + artist.person.address2, 1.7, 9.125,  4.1, 9.475, style=left_align_style )
        text_into_box ( c, artist.person.city, 1.7, 8.75,   4.1,  9.1, style=left_align_style   )
        text_into_box ( c, artist.person.state, 1.7, 8.375,  4.1,  8.725, style=left_align_style )
        text_into_box ( c, artist.person.postcode, 1.7, 8.0,    4.1,  8.35, style=left_align_style  )
        text_into_box ( c, artist.person.country, 1.7, 7.625,  4.1,  7.975, style=left_align_style )
        text_into_box ( c, artist.person.phone, 1.7, 7.25,   4.1,  7.6, style=left_align_style   )
        text_into_box ( c, artist.person.email, 4.9, 9.875, 8.0, 10.225, style=left_align_style, fontSize=16 )      
        text_into_box ( c, ", ".join ( [agent.name for agent in artist.agent_set.all()] ), 5.9, 7.625, 8.0, 7.975, style=left_align_style )
        for i, piece in enumerate(piecegroup):
            if piece is None: continue
            y0 = 6.45 - i*0.25
            y1 = 6.675 - i*0.25
            text_into_box ( c, unicode(piece.pieceid), 0.5, y0, 1.0, y1 )           
            text_into_box ( c, piece.name, 1.0, y0, 4.0, y1, style=left_align_style )           
            text_into_box ( c, yn(piece.adult), 4.0, y0, 4.5, y1 )          
            text_into_box ( c, priceornfs(piece.not_for_sale,piece.min_bid), 4.5, y0, 5.25, y1 )            
            text_into_box ( c, buynoworna(piece.buy_now), 5.25, y0, 6.0, y1 )           
        c.showPage ()
    c.save ()
    
    
def piece_stickers ( pieces, output ):

    c = Canvas ( output, pagesize=letter )
    x_range = range(3)
    y_range = range(10)
    pieceiter = iter(pieces)
    
    last_artist = None

    try:
        piece = pieceiter.next ()
        while True:
            try:
                for y in range(10):
                    for x in range(3):
                        if piece.artist != last_artist and x != 0:
                            continue
                        message = "<b>%s</b><br/><i>%s</i><br/>%s" % ( piece.name, piece.artist.artistname(), piece.media )
                        c.saveState ()
                        c.translate ( (3/16.0 + x * (2+3/4.0)) * inch, (9.5 - y) * inch )
                        text_into_box ( c, message, 0.2, 0.1, 2.475, 0.9, style=piece_sticker_style, escape_text=False, fontSize=12 )
                        c.restoreState ()
                        last_artist = piece.artist
                        piece = pieceiter.next ()
            finally:
                c.showPage ()
    except StopIteration:
        pass
            
    c.save ()


def bidder_agreement(bidder, output):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    pdfmetrics.registerFont(TTFont(*settings.ARTSHOW_BARCODE_FONT))

    c = Canvas(output, pagesize=letter)
    pdf = PdfReader(settings.ARTSHOW_BLANK_BIDDER_AGREEMENT)
    xobj = pagexobj(pdf.pages[0])
    rlobj = makerl(c, xobj)

    c.translate(0, 5.5 * inch)

    c.doForm(rlobj)
    text_into_box(c, u"*P" + unicode(bidder.person.id) + u"*", 3.5, 4.8, 5.5, 5.05, fontSize=14, style=barcode_style)
    text_into_box(c, "Ref. " + unicode(bidder.person.id), 3.5, 4.55, 5.5, 4.75, fontSize=10)

    text_into_box(c, bidder.person.reg_id, 6.2, 1.35, 7.7, 1.6, fontSize=12)

    text_into_box(c, bidder.person.name, 1.3, 1.4, 5.2, 1.7, fontSize=14)
    text_into_box(c, bidder.at_con_contact, 2.1, 0.5, 5.2, 0.8, fontSize=12)

    c.showPage()
    c.save()
