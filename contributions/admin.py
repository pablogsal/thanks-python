from django.contrib import admin
from .models import Commit, Contributor

admin.site.register(Commit)
admin.site.register(Contributor)

# Register your models here.
