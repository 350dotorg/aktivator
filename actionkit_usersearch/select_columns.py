from django.utils.translation import ugettext_lazy as _
import json

TYPE_CHOICES = {
    "userfield": (_("Userfield Value"), 
                  "actionkit_usersearch.select_columns.UserField"),
    "actionfield": (_("Actionfield Value"), 
                    "actionkit_usersearch.select_columns.ActionField"),
    "actionfield": (_("Raw SQL Subquery"), 
                    "actionkit_usersearch.select_columns.RawSqlSubquery"),
    "num_actions": (_("Number of Actions"), 
                    "actionkit_usersearch.select_columns.NumActions"),
    "num_donations": (_("Number of Donations"), 
                      "actionkit_usersearch.select_columns.NumDonations"),
    "total_donations": (_("Total Amount Donated"), 
                        "actionkit_usersearch.select_columns.TotalDonations"),
    "yearly_donations": (_("Amount Donated Per Year"),
                         "actionkit_usersearch.select_columns.YearlyDonations"),
    }


class UserField(object):

    def __init__(self, data):
        self.name = data.name

    def __call__(self, queryset):
        return queryset.extra(select={
                self.name: ("SELECT `value` FROM `core_userfield` "
                            "WHERE `core_userfield`.`parent_id`=`core_user`.`id` "
                            "AND `core_userfield`.`name`=%s LIMIT 1"
                            )},
                              select_params=[self.name])

class RawSqlSubquery(object):

    def __init__(self, data):
        self.name = data.name
        self.raw_sql = data.parameters

    def __call__(self, queryset):
        return queryset.extra(select={
                self.name: self.raw_sql})

class ActionField(object):

    def __init__(self, data):
        self.name = data.name
        try:
            self.pages = json.loads(data.parameters)['page_ids']
        except (ValueError, TypeError, KeyError):
            self.pages = None

    def __call__(self, queryset):
        if self.pages is None:
            return queryset.extra(select={
                    self.name: ("SELECT `value` FROM `core_actionfield` "
                                "JOIN `core_action` "
                                "ON `core_action`.`id`=`core_actionfield`.`parent_id` "
                                "WHERE `core_action`.`user_id`=`core_user`.`id` "
                                "AND `core_actionfield`.`name`=%s LIMIT 1"
                                )},
                                  select_params=[self.name])
        else:
            sql = ("SELECT `value` FROM `core_actionfield` "
                   "JOIN `core_action` "
                   "ON `core_action`.`id`=`core_actionfield`.`parent_id` "
                   "WHERE `core_action`.`user_id`=`core_user`.`id` "
                   "AND (")
            sql_or = []
            for page in self.pages:
                sql_or.append("`core_action`.`page_id` = %s")
            sql += " OR ".join(sql_or)
            sql += (") AND `core_actionfield`.`name`=%s LIMIT 1")
            return queryset.extra(select={self.name: sql},
                                  select_params=self.pages + [self.name])

class YearlyDonations(object):
    def __init__(self, data):
        self.name = data.name
        self.year = json.loads(data.parameters)['year']

    def __call__(self, queryset):
        return queryset.extra(select={
                    self.name: ("SELECT SUM(`total`) FROM `core_order` "
                                "WHERE `core_order`.`user_id`=`core_user`.`id` "
                                "AND `core_order`.`status`=\"completed\" "
                                "AND YEAR(`core_order`.`created_at`) = %s "
                                )
                    },
                              select_params=[self.year])
            
class TotalDonations(object):

    def __init__(self, data):
        self.name = data.name
        try:
            self.tag = json.loads(data.parameters)['tag']
        except (KeyError, ValueError, TypeError):
            self.tag = None

    def __call__(self, queryset):
        if self.tag is None:
            return queryset.extra(select={
                    self.name: ("SELECT SUM(`total`) FROM `core_order` "
                                "WHERE `core_order`.`user_id`=`core_user`.`id` "
                                "AND `core_order`.`status`=\"completed\" ")
                    })
        else:
            return queryset.extra(select={
                    self.name: ("SELECT SUM(`total`) FROM `core_order` "
                                "JOIN `core_action` "
                                "ON `core_action`.`id`=`core_order`.`action_id` "
                                "JOIN `core_page` "
                                "ON `core_page`.`id`=`core_action`.`page_id` "
                                "JOIN `core_page_tags` "
                                "ON `core_page_tags`.`page_id`=`core_page`.`id` "
                                "JOIN `core_tag` "
                                "ON `core_tag`.`id`=`core_page_tags`.`tag_id` "
                                "WHERE `core_order`.`user_id`=`core_user`.`id` "
                                "AND `core_order`.`status`=\"completed\" "
                                "AND `core_tag`.`name` = %s "
                                )
                    },
                                  select_params=[self.tag])
            

class NumDonations(object):

    def __init__(self, data):
        self.name = data.name

    def __call__(self, queryset):
        return queryset.extra(select={
                self.name: ("SELECT COUNT(*) FROM `core_order` "
                            "WHERE `core_order`.`user_id`=`core_user`.`id` "
                            "AND `core_order`.`status`=\"completed\" ")
                })

class NumActions(object):

    def __init__(self, data):
        self.name = data.name

    def __call__(self, queryset):
        return queryset.extra(select={
                self.name: ("SELECT COUNT(*) FROM `core_action` "
                            "WHERE `core_action`.`user_id`=`core_user`.`id` "
                            "AND `core_action`.`status`=\"complete\" ")
                })

