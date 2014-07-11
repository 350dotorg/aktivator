from actionkit import rest
from actionkit.models import *
import datetime
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect
from django.template.defaultfilters import date
from djangohelpers import rendered_with, allow_http
import json
from actionkit_userdetail.models import CalloutUserfield

def _mailing_history(request, agent):
    _sends = mailings_by_user(agent)

    sends = {}
    for send in _sends:
        id = send['id']
        if id not in sends:
            sends[id] = {
                'id': send['id'],
                'mailed_at': send['mailed_at'],
                'subject_text': send['subject_text'],
                'clicks': set(),
                'opens': set(),
                }
        sends[id]['clicks'] = set(sends[id]['clicks'])
        sends[id]['opens'] = set(sends[id]['opens'])
        if send['clicked_at'] is not None:
            sends[id]['clicks'].add(send['clicked_at'])
        if send['opened_at'] is not None:
            sends[id]['opens'].add(send['opened_at'])
        sends[id]['clicks'] = list(sends[id]['clicks'])
        sends[id]['opens'] = list(sends[id]['opens'])
    
    return sends

@allow_http("GET")
def user_fields(request, user_id):
    try:
        agent = CoreUser.objects.using("ak").get(id=user_id)
    except CoreUser.DoesNotExist:
        return HttpResponseNotFound("No such record exists")

    fields = agent.fields.all()
    fields = [{'name': field.name, 'value': field.value} for field in fields]
    return HttpResponse(json.dumps(fields), content_type="application/json")

@allow_http("GET")
def mailing_history(request, user_id):
    try:
        agent = CoreUser.objects.using("ak").get(id=user_id)
    except CoreUser.DoesNotExist:
        return HttpResponseNotFound("No such record exists")

    sends = _mailing_history(request, agent)

    def dthandler(obj):
        if isinstance(obj, datetime.datetime):
            return date(obj)
    return HttpResponse(json.dumps(sends, default=dthandler),
                        content_type="application/json")

@allow_http("GET")
def jump_to_member(request):
    member = request.GET.get("member")
    if member.isdigit():
        return redirect("userdetail_detail", member)
    elif '@' in member:
        try:
            member = CoreUser.objects.using("ak").get(email=member)
        except CoreUser.DoesNotExist:
            return HttpResponseNotFound("No member exists with email %s" % member)
        return redirect("userdetail_detail", member.id)
    else:
        return HttpResponse(
            "I could not recognize this as an ID or an email address: '%s'" % member, 
            status=400)

@allow_http("GET")
@rendered_with("actionkit_userdetail/view_user_detail.html")
def view_user_detail(request, user_id):
    ctx = _detail(request, user_id)
    ctx['member_id'] = user_id
    return ctx

@allow_http("GET")
def detail_json(request, user_id):
    ctx = _detail(request, user_id)
    def dthandler(obj):
        if isinstance(obj, datetime.datetime):
            return date(obj)
        elif hasattr(obj, 'to_json'):
            return obj.to_json()
    try:
        ctx['latest_action'] = ctx['actions'][0]
    except IndexError:
        ctx['latest_action'] = None
    try:
        ctx['latest_order'] = ctx['orders'][0]
    except IndexError:
        ctx['latest_order'] = None
    try:
        ctx['latest_open'] = ctx['opens'][0]
    except IndexError:
        ctx['latest_open'] = None
    try:
        ctx['latest_click'] = ctx['clicks'][0]
    except IndexError:
        ctx['latest_click'] = None

    agent = ctx['agent']
    ctx['sends'] = _mailing_history(request, agent).values()
    ctx['sends'] = sorted(ctx['sends'], key=itemgetter("mailed_at"), reverse=True)
    try:
        ctx['latest_send'] = ctx['sends'][0]
    except IndexError:
        ctx['latest_send'] = None    

    return HttpResponse(json.dumps(ctx, cls=JSONEncoder, default=dthandler),
                        content_type="application/json")
    

def fetch_contact_details(email):
    #url = ('https://api.fullcontact.com/v2/person.json?email=%s&apiKey=%s'
    #        % (email, settings.FULLCONTACT_API))
    #try:
    #    response = urllib2.urlopen(url)
    #    result = response.read()
    #    jsondata = json.loads(result)
    #except urllib2.HTTPError:
    #    jsondata = dict(status=500,
    #                    message='Error retrieving supplemental data')
    #return jsondata

    return dict(status=500,
                message='Error retrieving supplemental data')

@allow_http("GET")
def supplemental_details_json(request, user_id):
    try:
        agent = CoreUser.objects.using("ak").get(id=user_id)
    except CoreUser.DoesNotExist:
        raise Http404("No user: %s" % user_id)
    email = agent.email
    contact_details = fetch_contact_details(email)
    return HttpResponse(json.dumps(contact_details),
                        content_type="application/json")

from collections import namedtuple
_AgentTag = namedtuple("AgentTag", "name ak_tag_id editable allowed_tag_id")
class AgentTag(_AgentTag):
    def __repr__(self):
        return self.name

@allow_http("GET")
@rendered_with("actionkit_userdetail/view_order_detail.html")
def order_detail(request, user_id, order_id):
    try:
        order = CoreOrder.objects.using("ak").select_related("user").get(
            id=order_id, user_id=user_id)
    except CoreOrder.DoesNotExist:
        raise Http404("No order %s for user %" % (order_id, user_id))
    
    recurrences = list(order.recurrences.all())
    transactions = list(order.transactions.all())

    if order.import_id:
        type = "Standalone Order (imported)"
    elif recurrences:
        type = "Recurring Order"
    elif transactions:
        type = "Standalone Order"

    return locals()

def _detail(request, user_id):
    callout_userfields = CalloutUserfield.objects.all()
    extra_select = {'phone_number': (
                    "SELECT `phone` FROM `core_phone` "
                    "WHERE `core_phone`.`user_id`=`core_user`.`id` "
                    "LIMIT 1")}
    for field in callout_userfields:
        extra_select[field.name] = (
            "SELECT `value` FROM `core_userfield` "
            "WHERE `core_userfield`.`parent_id`=`core_user`.`id` "
            'AND `core_userfield`.`name`="%s" LIMIT 1' % field.name)

    try:
        agent = CoreUser.objects.using("ak").extra(select=extra_select,
                                                   ).get(id=user_id)
    except CoreUser.DoesNotExist:
        return HttpResponseNotFound("No such record exists")

    actions = list(agent.action.all().select_related("page").order_by("-created_at"))
    orders = list(
        agent.orders.all().select_related("action", "action__page").order_by(
            "-created_at"))
    transactions = list(
        CoreTransaction.objects.using("ak").select_related("order").filter(
            order__user=agent).order_by("-created_at"))

    total_donations = sum(order.total for order in orders 
                          if order.import_id is not None 
                          and order.status == "completed"
                          and order.id not in [t.order_id for t in transactions]) + \
                      sum(transaction.amount for transaction in transactions
                          if transaction.status == "completed"
                          and transaction.order.status == "completed")

    recurring_donations = list(CoreOrderRecurring.objects.using(
            "ak").filter(user=agent).select_related("order").order_by("-start"))

    now = datetime.date.today()
    upcoming_recurring_donations = [
        recurrence for recurrence in recurring_donations
        if recurrence.status == "active"
        and recurrence.start > now
        ]

    clicks = clicks_by_user(agent)
    opens = opens_by_user(agent)
    sends = CoreUserMailing.objects.using("ak").filter(user=agent).order_by(
        "-created_at").select_related("subject")

    _agent_tags = CoreTag.objects.using("ak").filter(
        pagetags__page__coreaction__user=agent).values("name", "id", "pagetags__page_id")

    agent_tags = []
    
    for tag in _agent_tags:
        editable = False
        allowed_tag_id = None
        agent_tags.append(AgentTag(tag['name'], tag['id'], editable, allowed_tag_id))

    # The list of already-used tags may contain duplicates.
    # We need to filter out duplicates, and if there is an "editable" copy of the tag
    # as well as an "uneditable" copy, we need to discard the editable one.
    _agent_tags = {}
    for tag in agent_tags:
        _agent_tags.setdefault(tag.name, [])
        if tag.editable:
            _agent_tags[tag.name].append(tag)
        else:
            _agent_tags[tag.name].insert(0, tag)
    agent_tags = (copies[0] for copies in _agent_tags.values())

    # We also need to filter out the "special tag-page marker tag" 
    # from the list -- unless it too is editable!
    #agent_tags = [tag for tag in agent_tags
    #              if (tag.ak_tag_id != settings.AKTIVATOR_TAG_PAGE_TAG_ID
    #                  or tag.editable)]

    # Then, we need to filter out already-used tags from the list of addable tags.
    #_agent_tags = [tag.name for tag in agent_tags]
    #allowed_tags = [tag for tag in _allowed_tags if tag.tag_name not in _agent_tags]

    return locals()
