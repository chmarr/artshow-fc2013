from artshow.models import Artist
from django.shortcuts import render
from django.conf import settings


def artists(request):
    aa = Artist.objects.all()
    aa = list(aa)
    aa = [a for a in aa if a.is_active()]
    aa.sort(key=lambda x: x.artistname().lower())
    column_length = (len(aa) + 2) / 3
    return render(request, "furcon/artists.html", {"artists": aa, "column_length": column_length,
                                                   "mark_waiting": settings.FURCON_ARTIST_LISTING_MARK_WAITING})
