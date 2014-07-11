from actionkit import rest
from actionkit.models import *
from actionkit.rest import *
import dateutil.parser
from django.conf import settings
from django.http import HttpResponse
from django.http import QueryDict
from django.shortcuts import redirect
from djangohelpers import rendered_with, allow_http
import json
import requests.exceptions

from actionkit_usersearch.models import SelectColumn, WhereClause, UserPermissions
from actionkit_usersearch.search_functions import (build_query, 
                                                   build_query_from_json,
                                                   run_report)
from actionkit_usersearch.utils import normalize_querystring

@allow_http("GET")
def campuses(request):
    prefix = request.GET.get('q')
    limit = request.GET.get('limit', '10')
    try:
        limit = int(limit)
    except ValueError:
        limit = 10
    limit = clamp(limit, 1, 1000)
    if prefix:
        cursor = connections['ak'].cursor()
        prefix = prefix + '%'
        cursor.execute("SELECT distinct value FROM core_userfield "
                       "WHERE name=\"campus\" and value LIKE %s ORDER BY value LIMIT %s",
                       [prefix, limit])
        values = [row[0] for row in cursor.fetchall()]
        if not values:
            prefix = '%' + prefix
            cursor.execute("SELECT distinct value FROM core_userfield "
                           "WHERE name=\"campus\" and value LIKE %s ORDER BY value LIMIT %s",
                           [prefix, limit])
            values = [row[0] for row in cursor.fetchall()]
    else:
        values = []

    return HttpResponse(json.dumps(values), content_type='application/json')

@allow_http("GET")
def sources(request):
    prefix = request.GET.get('q')
    limit = request.GET.get('limit', '10')
    try:
        limit = int(limit)
    except ValueError:
        limit = 10
    limit = clamp(limit, 1, 1000)
    if prefix:
        cursor = connections['ak'].cursor()
        prefix = prefix + '%'
        cursor.execute("SELECT distinct source FROM core_user "
                       "WHERE source LIKE %s ORDER BY source LIMIT %s",
                       [prefix, limit])
        sources = [row[0] for row in cursor.fetchall()]
    else:
        sources = []
    return HttpResponse(json.dumps(sources), content_type='application/json')

@allow_http("GET")
def countries(request):
    countries = CoreUser.objects.using("ak").values_list("country", flat=True).distinct().order_by("country")
    countries = [(i,i) for i in countries]
    return HttpResponse(json.dumps(countries),
                        content_type="application/json")

@allow_http("GET")
def regions(request):
    countries = request.GET.getlist("country")
    raw_regions = CoreUser.objects.using("ak").filter(
        country__in=countries).values(
        "country", "region").distinct().order_by("country", "region")
    regions = {}
    for region in raw_regions:
        if region['country'] not in regions:
            regions[region['country']] = []
        regions[region['country']].append(region['region'])
    return HttpResponse(json.dumps(regions), 
                        content_type="application/json")

@allow_http("GET")
def states(request):
    countries = request.GET.getlist("country")
    raw_states = CoreUser.objects.using("ak").filter(
        country__in=countries).values(
        "country", "state").distinct().order_by("country", "state")
    states = {}
    for state in raw_states:
        if state['country'] not in states:
            states[state['country']] = []
        states[state['country']].append(state['state'])
    return HttpResponse(json.dumps(states), 
                        content_type="application/json")

@allow_http("GET")
def cities(request):
    cities = CoreUser.objects.using("ak").values_list("city", flat=True).distinct().order_by("city")
    cities = [(i,i) for i in cities]
    return HttpResponse(json.dumps(cities), 
                        content_type="application/json")

@allow_http("GET")
def pages(request):
    pages = CorePage.objects.using("ak").all().order_by("title")
    pages = [(i.id, str(i)) for i in pages]
    return HttpResponse(json.dumps(pages), 
                        content_type="application/json")

DEFAULT_CHECKED_COLUMNS = [
    "id", "email", "zip", "country", "first_name", "last_name", "phone",
    ]

@allow_http("GET")
@rendered_with("actionkit_usersearch/build_search.html")
def search(request):

    sources = CoreUser.objects.using("ak").values_list(
        "source", flat=True).distinct().order_by("source")
    tags = CoreTag.objects.using("ak").all().order_by("name")
    countries = CoreUser.objects.using("ak").values_list(
            "country", flat=True).distinct().order_by("country")

    pages = CorePage.objects.using("ak").all().order_by("title")

    column_options = [
        {'name': field.name, 
         'display_name': ' '.join([i.title() for i in field.name.split("_")]),
         'checked': field.name in DEFAULT_CHECKED_COLUMNS}
        for field in CoreUser._meta.fields
        if getattr(field, 'rel', None) is None and field.name is not "password"]
    for col in SelectColumn.objects.all():
        if col.name in DEFAULT_CHECKED_COLUMNS:
            col.checked = True
        column_options.append(col)
    column_options = sorted(column_options, key=lambda x: x.get("name") if isinstance(x, dict) else x.name)

    where_clauses = WhereClause.objects.all()        
    
    languages = CoreLanguage.objects.using(
            "ak").all().distinct().order_by("name")

    fields = {
        'Location':
            [('country', 'Country'),
             ('state', 'State', 'disabled'),
             ('city', 'City', 'disabled'),
             ('zipcode', 'Zip Code'),
             ],
        'Activity':
            [('action', 'Took part in action'),
             ('source', 'Source'),
             ('tag', 'Is tagged with'),
             ],
        'About':
            [
             ('language', "Preferred Language"),
             ('created_before', "Created Before"),
             ('created_after', "Created After"),
             ],
        }
    for clause in where_clauses:
        fields.setdefault(clause.display_category, []).append(
            (clause.name, clause.display_name))

    return locals()

@allow_http("POST")
def show_counts(request):

    query = build_query_from_json(json.loads(request.body),
                                  queryset_modifier_fn=lambda x: x.count())
    error = None
    try:
        resp = rest.run_query(query.raw_sql)
    except requests.exceptions.Timeout:
        error = "Actionkit took too long to respond.  This is probably because your search is very complex.  Please request a CSV with full results instead."
        count = None
    else:
        count = resp[0][0]

    params = request.body

    return HttpResponse(json.dumps({
        'human_query': query.human_query,
        'count': count,
        'params': params,
        'error': error,
        }), content_type="application/json")

@allow_http("POST")
def show_sql(request):

    query = build_query_from_json(json.loads(request.body),
                                  queryset_modifier_fn=lambda x: x.values_list("id"))

    return HttpResponse(json.dumps({
        'raw_sql': query.raw_sql,
        'human_query': query.human_query,
        }), content_type="application/json")

@allow_http("POST")
def create_report(request):

    if not request.user.email:
        return HttpResponse(json.dumps({
                    "error": True,
                    "error_message": "Your account's email address is not set up.  To get full results, please ask an administrator to set up an email address for your account (%s)" % request.user.username}), content_type="application/json")

    try:
        max_records = UserPermissions.objects.get(user=request.user).records_per_search
    except UserPermissions.DoesNotExist:
        max_records = 500

    query = build_query_from_json(json.loads(request.body),
                                  queryset_modifier_fn=lambda x: x[:max_records] if max_records > 0 else x)
    report = run_report(request, query)

    status_url = redirect("usersearch_get_report_status", report.task_id)['Location']
    return HttpResponse(json.dumps({
                'redirect': status_url,
                'email_to': request.user.email,
                'email_subject': report.name,
                'human_query': query.human_query,
                }), content_type="application/json")

@allow_http("GET")
@rendered_with("actionkit_usersearch/report_status.html")
def get_report_status(request, task_id):
    status = rest.poll_report(task_id)
    
    try:
        status['updated_at'] = dateutil.parser.parse(status['updated_at'])
    except Exception:
        pass

    report_id = status['params']['report_id']
    report = QueryReport.objects.using("ak").select_related("report").get(
        report_ptr=report_id)
    
    return dict(
        status=status,
        report=report,
        )

@allow_http("GET")
def download_report(request, task_id):
    status = rest.poll_report(task_id)

    download = status['details']['download_uri']

    host = settings.ACTIONKIT_API_HOST
    url = "%s%s" % (host, download)

    resp = requests.get(url, auth=HTTPBasicAuth(
            settings.ACTIONKIT_API_USER, settings.ACTIONKIT_API_PASSWORD),
                        prefetch=False)
    resp.encoding = "utf-8"

    return HttpResponse(json.dumps(status))
