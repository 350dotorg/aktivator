from actionkit.models import CoreUserField
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
import json

TYPE_CHOICES = {
    "userfield": (_("Userfield Value"), 
                  "actionkit_usersearch.where_clauses.UserField"),
    "userfield_exists": (_("Userfield Existence"),
                         "actionkit_usersearch.where_clauses.UserFieldExists"),
#    "actionfield": (_("Actionfield Value"), 
#                    "actionkit_usersearch.where_clauses.ActionField"),
    }

class UserFieldExists(object):

    def __init__(self, data):
        self.name = data.name
        self.display_name = data.display_name
        self.do_not_call_in_templates = True

    def __call__(self, queryset, term, type, **params):
        query = {'fields__name': self.name}
        if type == "exclude":
            queryset = queryset.exclude(**query)
            human_query = u"userfield %s does not exist" % self.name
        else:
            queryset = queryset.filter(**query)
            human_query = u"userfield %s exists" % self.name
        
        return queryset, human_query

    def render(self):
        return render_to_string("actionkit_usersearch/where_clauses/userfield_exists.html",
                                {'clause': self})

class UserField(object):

    def __init__(self, data):
        self.name = data.name
        self.display_name = data.display_name
        self.do_not_call_in_templates = True

    def __call__(self, queryset, term, type, **params):
        query = {'fields__value__in': params[term],
                 'fields__name': self.name}
        
        if type == "exclude":
            queryset = queryset.exclude(**query)
            human_query = u"%s is not in (%s)" % (self.name, u', '.join(params[term]))
        else:
            queryset = queryset.filter(**query)
            human_query = u"%s is in (%s)" % (self.name, u', '.join(params[term]))

        return queryset, human_query
    
    def get_options(self):
        return [value for value in 
                CoreUserField.objects.using("ak").filter(name=self.name).values_list(
                "value", flat=True).distinct().order_by("value")]
    
    def render(self):
        return render_to_string("actionkit_usersearch/where_clauses/userfield.html",
                                {'clause': self})
