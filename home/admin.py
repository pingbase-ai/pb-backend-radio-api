from django.contrib import admin
from .models import Meeting, EndUserLogin, VoiceNote, Call

# Register your models here.
admin.site.register(Meeting)
admin.site.register(EndUserLogin)
admin.site.register(VoiceNote)
admin.site.register(Call)
