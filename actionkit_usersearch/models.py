from django.db import models
from zope.dottedname.resolve import resolve

from actionkit_usersearch.select_columns import TYPE_CHOICES as SELECT_TYPE_CHOICES
from actionkit_usersearch.where_clauses import TYPE_CHOICES as WHERE_TYPE_CHOICES

class UserPermissions(models.Model):
    user = models.OneToOneField('auth.User')
    
    records_per_search = models.IntegerField(default=0, help_text="Set this to 0 to let this user download CSVs without any limits.")

class WhereClause(models.Model):
    name = models.CharField(unique=True, max_length=50)
    display_name = models.CharField(max_length=100, null=True, blank=True)

    display_category = models.CharField(max_length=100)

    type = models.CharField(
        max_length=50,
        choices=[(i[0], i[1][0])
                 for i in 
                 WHERE_TYPE_CHOICES.items()])
    parameters = models.TextField(null=True, blank=True)

    def load(self):
        return resolve(WHERE_TYPE_CHOICES[self.type][1])(self)
    

class SelectColumn(models.Model):
    name = models.CharField(unique=True, max_length=50)
    display_name = models.CharField(max_length=100, null=True, blank=True)

    type = models.CharField(
        max_length=50,
        choices=[(i[0], i[1][0])
                 for i in 
                 SELECT_TYPE_CHOICES.items()])
    parameters = models.TextField(null=True, blank=True)

    def load(self):
        return resolve(SELECT_TYPE_CHOICES[self.type][1])(self)

