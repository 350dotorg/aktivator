from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns(
    'actionkit_usersearch.views',
    url('^$',
        'search',
        name='usersearch_search'),

    url('^new/$',
        'create_report',
        name='usersearch_create_report'),

    url('^counts/$',
        'show_counts',
        name='usersearch_show_counts'),
    url('^sql/$',
        'show_sql',
        name='usersearch_show_sql'),

    url('^status/(?P<task_id>\d+)/$',
        'get_report_status',
        name='usersearch_get_report_status'),

    url('^download/(?P<task_id>\d+)/$',
        'download_report',
        name='usersearch_download_report'),

    url(r'^autocomplete/sources/$', 'sources', name='autocomplete_sources'),
    url(r'^autocomplete/campuses/$', 'campuses', name='autocomplete_campuses'),

    url(r'^choices/countries/$', 'countries', name='choices_countries'),
    url(r'^choices/regions/$', 'regions', name='choices_regions'),
    url(r'^choices/states/$', 'states', name='choices_states'),
    url(r'^choices/cities/$', 'cities', name='choices_cities'),
    url(r'^choices/pages/$', 'pages', name='choices_pages'),

    )
