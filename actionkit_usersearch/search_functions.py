from actionkit import rest
from actionkit.models import *
from collections import namedtuple
import datetime
import dateutil.parser
from django.db.models import Count
from django.db.models import Sum
from django.http import QueryDict
from django.template.defaultfilters import slugify
import hashlib
import re

from actionkit_usersearch import sql
from actionkit_usersearch.models import SelectColumn, WhereClause
from actionkit_usersearch.utils import latlon_bbox
from actionkit_usersearch.utils import zipcode_to_latlon


def make_default_user_query(users, term, type, **params):
    """
    given a query_data dict and values which come from the ui,
    generate a dict that will be used for a user query

    this default query is a within query, that optionally adds some
    extra key/value data to the query dict
    """

    query = {}

    query_str = QUERIES[term]['query']
    within = query_str + '__in'
    query[within] = params[term]

    if type == "include":
        users = users.filter(**query)
        human_query = u"%s is in (%s)" % (term, u', '.join(params[term]))
    else:
        users = users.exclude(**query)
        human_query = u"%s is not in (%s)" % (term, u', '.join(params[term]))
    return users, human_query

def make_date_query(users, term, type, **params):
    date = params[term]
    match = dateutil.parser.parse(date)
    query = {QUERIES[term]['query']: match}

    if type == "include":
        users = users.filter(**query)
        human_query = "%s is in %s" % (term, date)
    else:
        users = users.exclude(**query)
        human_query = "%s is not in %s" % (term, date)
    return users, human_query

def make_zip_radius_query(users, term, type, zipcode, zipcode__distance=None):
    if zipcode__distance:
        distance = float(zipcode__distance)
        assert distance > 0, "Bad distance"
        latlon = zipcode_to_latlon(zipcode)
        assert latlon is not None, "No location found for: %s" % zipcode
        lat, lon = latlon
        bbox = latlon_bbox(lat, lon, distance)
        assert bbox is not None, "Bad bounding box for latlon: %s,%s" % (lat, lon)
        lat1, lat2, lon1, lon2 = bbox
        if type == "include":
            users = users.filter(location__latitude__range=(lat1, lat2),
                                 location__longitude__range=(lon1, lon2))
            human_query = "within %s miles of %s" % (distance, zipcode)
        else:
            users = users.exclude(location__latitude__range=(lat1, lat2),
                                  location__longitude__range=(lon1, lon2))
            human_query = "not within %s miles of %s" % (distance, zipcode)
    else:
        if type == "include":
            users = users.filter(zip=zipcode)
            human_query = "in zip code %s" % zipcode
        else:
            users = users.exclude(zip=zipcode)
            human_query = "not in zip code %s" % zipcode
    return users, human_query


QUERIES = {
    'country': {
        'query': "country",
        },
    'region': {
        'query': "region",
        },
    'state': {
        'query': "state",
        },
    'city': {
        'query': "city",
        },
    'action': {
        'query': "action__page__id",
        },
    'source': {
        'query': "source",
        },
    'tag': {
        'query': "action__page__pagetags__tag__id",
        },
    'language': {
        'query': "lang__id",
        },
    'created_before': {
        'query': "created_at__lte",
        'query_fn': make_date_query,
        },
    'created_after': {
        'query': "created_at__gte",
        'query_fn': make_date_query,
        },
    'zipcode': {
        'query_fn': make_zip_radius_query,
        },
    }

Query = namedtuple("Query", "human_query query_string raw_sql report_data")
Report = namedtuple("Report", "id shortname task_id name")

def build_query_from_json(params, queryset_modifier_fn=None):
    or_clause = params['clauses']
    #columns = params['columns']

    base_user_query = CoreUser.objects.using("ak").order_by("id")
    extra_where_clauses = dict((clause.name,clause) for clause in WhereClause.objects.all())

    machine_query = []
    human_query = []

    for and_clause in or_clause:
        users = base_user_query
        _human_query = []

        for clause in and_clause:
            search_term = clause['term']
            if search_term in extra_where_clauses:
                search_function = extra_where_clauses[search_term].load()
            else:
                search_function = QUERIES[search_term].get("query_fn", make_default_user_query)

            users, __human_query = search_function(users, **clause)
            _human_query.append(__human_query)
            continue

        if not _human_query or (
            users.query.sql_with_params() == base_user_query.query.sql_with_params()):
            continue

        machine_query.append(users)
        human_query.append("(%s)" % " and ".join(_human_query))

    human_query = "\n or ".join(human_query)
    users = None
    for i, query in enumerate(machine_query):
        if i == 0:
            users = query
        else:
            users = users | query
    if users is None:
        users = base_user_query

    ### If both of user_name and user_email are filled out,
    ### search for anyone who matches EITHER condition, rather than both.
    extra_where = []
    extra_params = []
    if params.get("user_name", "").strip():
        extra_where.append(
            "CONCAT(`core_user`.`first_name`, ' ', `core_user`.`last_name`) LIKE %s")
        extra_params.append("%" + "%".join(params['user_name'].strip().split()) + "%")
        human_query += "\n and name is like \"%s\"" % params['user_name']
    if params.get("user_email", "").strip():
        extra_where.append("`core_user`.`email` LIKE %s")
        extra_params.append("%" + params['user_email'].strip() + "%")
        human_query += "\n and email is like \"%s\"" % params['user_email']
    if params.get("user_id", ""):
        akids = [int(i.strip()) for i in params["user_id"].split(",")]
        for akid in akids:
            extra_where.append("`core_user`.`id` = %s")
            extra_params.append(akid)
        human_query += "\n and ActionKit ID is in %s" % akids
    if len(extra_where):
        if len(extra_where) > 1:
            extra_where = [(" OR ".join(extra_where))]
        
        users = users.extra(
            where=extra_where,
            params=extra_params)

    #users = users.extra(select={'phone': (
    #            "SELECT `normalized_phone` FROM `core_phone` "
    #            "WHERE `core_phone`.`user_id`=`core_user`.`id` "
    #            "LIMIT 1"),
    #                            'name': (
    #            "CONCAT(CONCAT(first_name, \" \"), last_name)"),
    #                            })

    extra_select_columns = dict((column.name,column) 
                                for column in SelectColumn.objects.all())
    include_columns = params['columns']
    columns = set()
    for column in include_columns:
        if column in extra_select_columns:
            users = extra_select_columns[column].load()(users)
        else:
            columns.add(column)

    if not params.get('include_unsubscribed_users', False):
        users = users.filter(subscription_status='subscribed')
        human_query += "\n and user is currently subscribed"

    users = users.distinct()
    users = users.only(*columns)

    raw_sql = sql.raw_sql_from_queryset(users, queryset_modifier_fn)

    return Query(human_query, params, raw_sql, None)

def build_query(querystring, queryset_modifier_fn=None):
    query_params = QueryDict(querystring)

    base_user_query = CoreUser.objects.using("ak").order_by("id")
    
    includes = []

    include_pattern = re.compile("^include:\d+$")
    for key in query_params.keys():
        if (include_pattern.match(key)
            and query_params[key]
            and (not query_params[key].endswith('_istoggle'))):
            includes.append((key, query_params.getlist(key)))

    human_query = []

    extra_where_clauses = dict((clause.name,clause) for clause in WhereClause.objects.all())

    all_user_queries = []
    for include_group in includes:
        users = base_user_query
        _human_query = []
        for item in include_group[1]:
            ## "distance" is handled in a group with "zipcode", so we ignore it here
            if item == "zipcode__distance":
                continue
            ## same for "contacted_by", in a group with "contacted_since"
            if item == "contacted_since__contacted_by":
                continue
            if item == "contacted_by__contacted_since":
                continue
            ## ditto
            if item == 'more_actions__since':
                continue

            from pprint import pprint
            pprint(query_params)
            possible_values = query_params.getlist(
                "%s_%s" % (include_group[0], item))
            if len(possible_values) == 0:
                continue

            print item, possible_values
            istogglename = '%s_%s_istoggle' % (include_group[0], item)
            istoggle = query_params.get(istogglename, '1')
            try:
                istoggle = bool(int(istoggle))
            except ValueError:
                istoggle = True

            if item in extra_where_clauses:
                users, __human_query = extra_where_clauses[item].load()(
                    users, possible_values, is_not=not istoggle)
                _human_query.append(__human_query)
                continue
            
            query_data = QUERIES[item]
            extra_data = {}

            extra_data['istoggle'] = istoggle

            ## XXX special cased zip code and distance
            # these two fields are together, if we have another case like this
            # we should probably formalize this
            if item == "zipcode":
                distance = query_params.get('%s_zipcode__distance' % include_group[0])
                if distance:
                    extra_data['distance'] = distance

            make_query_fn = query_data.get('query_fn', make_default_user_query)
            users, __human_query = make_query_fn(
                users, query_data, possible_values, item, extra_data)
            _human_query.append(__human_query)

        if not _human_query or (
            users.query.sql_with_params() == base_user_query.query.sql_with_params()):
            continue

        all_user_queries.append(users)
        human_query.append("(%s)" % " and ".join(_human_query))

    human_query = "\n or ".join(human_query)
    users = None
    for i, query in enumerate(all_user_queries):
        if i == 0:
            users = query
        else:
            users = users | query
    if users is None:
        users = base_user_query

    ### If both of user_name and user_email are filled out,
    ### search for anyone who matches EITHER condition, rather than both.
    extra_where = []
    extra_params = []
    if query_params.get("user_name"):
        extra_where.append(
            "CONCAT(`core_user`.`first_name`, ' ', `core_user`.`last_name`) LIKE %s")
        extra_params.append("%" + "%".join(query_params['user_name'].split()) + "%")
        human_query += "\n and name is like \"%s\"" % query_params['user_name']
    if query_params.get("user_email"):
        extra_where.append("`core_user`.`email` LIKE %s")
        extra_params.append("%" + query_params.get("user_email") + "%")
        human_query += "\n and email is like \"%s\"" % query_params['user_email']
    if query_params.get("user_akid"):
        akids = [int(i.strip()) for i in query_params["user_akid"].split(",")]
        for akid in akids:
            extra_where.append("`core_user`.`id` = %s")
            extra_params.append(akid)
        human_query += "\n and AKID is in %s" % akids
    if len(extra_where):
        if len(extra_where) == 2:
            extra_where = ["(%s OR %s)" % tuple(extra_where)]
        users = users.extra(
            where=extra_where,
            params=extra_params)

    users = users.extra(select={'phone': (
                "SELECT `normalized_phone` FROM `core_phone` "
                "WHERE `core_phone`.`user_id`=`core_user`.`id` "
                "LIMIT 1"),
                                'name': (
                "CONCAT(CONCAT(first_name, \" \"), last_name)"),
                                })

    columns = SelectColumn.objects.filter(name__in=query_params.getlist("column"))
    for column in columns:
        users = column.load()(users)

    if users.query.sql_with_params() == base_user_query.query.sql_with_params():
        users = base_user_query.none()

    if not query_params.get('subscription_all_users', False):
        users = users.filter(subscription_status='subscribed')
        human_query += "\n and subscription_status is 'subscribed'"

    users = users.distinct()
    users = users.defer("password", "rand_id")

    raw_sql = sql.raw_sql_from_queryset(users, queryset_modifier_fn)

    del users

    return Query(human_query, querystring, raw_sql, None)

def run_report(request, query):
    slug = hashlib.sha1(
        query.raw_sql + datetime.datetime.now().utcnow().isoformat()).hexdigest()
    slug = slugify(slug)

    friendlier_name = "Your AKtivator search results (%s)" % slug

    ## Create a new report
    ## (https://roboticdogs.actionkit.com/docs/manual/api/rest/reports.html#creating-reports)
    ## using the raw sql
    resp = rest.create_report(query.raw_sql, query.human_query, friendlier_name, slug)

    report_id = resp['id']
    shortname = resp['short_name']

    ## and then trigger an asynchronous run of that report
    ## (https://roboticdogs.actionkit.com/docs/manual/api/rest/reports.html#running-reports-asynchronously)
    task_id = rest.run_report(shortname, email_to=request.user.email,
                              data=query.report_data)

    return Report(report_id, shortname, task_id, friendlier_name)
