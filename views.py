from django.http import HttpResponse
from artshow.models import Artist
from django.shortcuts import render
import json


def artists(request):
    format = request.GET.get("format","html")
    aa = Artist.objects.all()
    aa = list(aa)
    aa = [a for a in aa if a.is_active()]
    aa.sort(key=lambda x: x.artistname().lower())
    if format == "html":
        mark_waiting = bool(request.GET.get("mark_waiting", ""))
        column_length = (len(aa) + 2) / 3
        return render(request, "furcon/artists.html", {"artists": aa, "column_length": column_length,
                                                       "mark_waiting": mark_waiting})
    else:
        artists = [ {"artist_name": a.artistname(), "website": a.website, "is_showing": a.is_showing()} for a in aa ]
        data = { "artists": artists }
        json_str = json.dumps( data )
        return HttpResponse( json_str, content_type="application/json" )




