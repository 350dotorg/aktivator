from django.db import connections, DatabaseError

def raw_sql_from_queryset(queryset, modifier_fn=None):
    dummy_queryset = queryset.using('dummy')
    # @@TODO: this is necessary for some reason.
    dummy_queryset.query.group_by = None

    try:
        if modifier_fn is not None:
            dummy_queryset = modifier_fn(dummy_queryset)

        # trigger the query
        list(dummy_queryset)
    except DatabaseError, e:
        queries = connections['dummy'].queries
        actual_sql = queries[-1]['sql']        
        return actual_sql.replace("-9999", "{{ user_ids }}")
    else:
        #sql, params = dummy_queryset.query.sql_with_params()
        #db = connections['dummy'].cursor()
        #import pdb; pdb.set_trace()
        assert False, "Dummy query was expected to fail"
