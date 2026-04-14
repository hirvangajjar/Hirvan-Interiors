from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(User)
admin.site.register(Designer)
admin.site.register(Moodboard)
admin.site.register(Site)
admin.site.register(Booking)

