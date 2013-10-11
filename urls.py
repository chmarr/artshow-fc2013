# Artshow Jockey
# Copyright (C) 2013 Chris Cogdon
# See file COPYING for licence details

from django.conf.urls import patterns

# This is not expected to be linked in the ROOT_URLCONF, but instead
# directed here by middleware. This way, common_settings.py does not
# need to be modified. Only local_settings.py

urlpatterns = patterns('furcon',
                       (r'^furcon/artists/$', 'views.artists'),
                       )
