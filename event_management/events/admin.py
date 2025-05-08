from django.contrib import admin
from .models import Event, Review

admin.site.register(Event)

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'rating', 'created_at')
    search_fields = ('user__username', 'event__name')
    list_filter = ('rating', 'created_at')

admin.site.register(Review, ReviewAdmin)
