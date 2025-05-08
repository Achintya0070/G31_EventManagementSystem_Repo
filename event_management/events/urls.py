from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EventViewSet, ReviewViewSet, BookingViewSet, QueryViewSet,
    EventListView, EventDetailView, profile, register,
    book_event, submit_review, submit_query, user_bookings, booking_confirmation
)

router = DefaultRouter()
router.register(r'events', EventViewSet)
router.register(r'reviews', ReviewViewSet)
router.register(r'bookings', BookingViewSet)
router.register(r'queries', QueryViewSet)

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),
    
    # Template URLs
    path('', EventListView.as_view(), name='home'),
    path('event/<int:pk>/', EventDetailView.as_view(), name='event_detail'),
    path('profile/', profile, name='profile'),
    path('register/', register, name='register'),
    path('event/<int:event_id>/book/', book_event, name='book_event'),
    path('event/<int:event_id>/review/', submit_review, name='submit_review'),
    path('query/', submit_query, name='submit_query'),
    path('my-bookings/', user_bookings, name='user_bookings'),
    path('event/<int:event_id>/confirmation/', booking_confirmation, name='booking_confirmation'),
]
