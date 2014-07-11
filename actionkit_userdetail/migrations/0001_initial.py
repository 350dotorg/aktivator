# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CalloutUserfield'
        db.create_table(u'actionkit_userdetail_calloutuserfield', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal(u'actionkit_userdetail', ['CalloutUserfield'])


    def backwards(self, orm):
        # Deleting model 'CalloutUserfield'
        db.delete_table(u'actionkit_userdetail_calloutuserfield')


    models = {
        u'actionkit_userdetail.calloutuserfield': {
            'Meta': {'object_name': 'CalloutUserfield'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['actionkit_userdetail']