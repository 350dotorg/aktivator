from django.db import models

class CalloutUserfield(models.Model):
    name = models.CharField(max_length=255)
