from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns(
    'actionkit_userdetail.views',

    url(r'^$', 'jump_to_member', 
        name='userdetail_jump_to_member'),

    url(r'^(?P<user_id>\d+)/$', 'view_user_detail', 
        name='userdetail_detail'),
    url(r'^(?P<user_id>\d+)/json/$', 'detail_json', name='userdetail_json'),
    url(r'^(?P<user_id>\d+)/supplemental/$', 'supplemental_details_json',
        name='userdetail_supplemental_details_json'),

    url(r'^(?P<user_id>\d+)/mailings/$', 'mailing_history',
        name='userdetail_mailing_history'),
    url(r'^(?P<user_id>\d+)/fields/$', 'user_fields',
        name='userdetail_user_fields'),

    url(r'^(?P<user_id>\d+)/orders/(?P<order_id>\d+)/$', 
        'order_detail',
        name='userdetail_order_detail'),

    )
