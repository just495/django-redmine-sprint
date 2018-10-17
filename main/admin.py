from django.contrib import admin
from solo.admin import SingletonModelAdmin
from .models import Redmine, Sprint

admin.site.register(Redmine, SingletonModelAdmin)
admin.site.register(Sprint)
