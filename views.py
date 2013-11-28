from artshow.models import Artist
from django.shortcuts import render


def artists(request):
    mark_waiting = bool(request.GET.get("mark_waiting", ""))
    aa = Artist.objects.all()
    aa = list(aa)
    aa = [a for a in aa if a.is_active()]
    aa.sort(key=lambda x: x.artistname().lower())
    column_length = (len(aa) + 2) / 3
    return render(request, "furcon/artists.html", {"artists": aa, "column_length": column_length,
                                                   "mark_waiting": mark_waiting})
