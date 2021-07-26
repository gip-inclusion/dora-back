from django.contrib import admin

from .models import AccessCondition, ConcernedPublic, Credential, Requirement, Service

admin.site.register(Service)
admin.site.register(AccessCondition)
admin.site.register(ConcernedPublic)
admin.site.register(Requirement)
admin.site.register(Credential)
