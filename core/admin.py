from django.contrib import admin
from .models import Lesson, Word, UserWord, Attempt

admin.site.register(Lesson)
admin.site.register(Word)
admin.site.register(UserWord)
admin.site.register(Attempt)