from djangohelpers.lib import register_admin

from actionkit_usersearch.models import SelectColumn, WhereClause, UserPermissions

register_admin(SelectColumn)
register_admin(WhereClause)
register_admin(UserPermissions)
