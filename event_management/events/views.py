from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.utils.timezone import make_aware
from rest_framework import viewsets
import requests
from django.http import Http404
from datetime import datetime
from django.urls import reverse
from .models import Event, Review, Booking, Query
from .forms import UserRegistrationForm, EventBookingForm, ReviewForm, QueryForm, EventForm
from .serializers import EventSerializer, ReviewSerializer, BookingSerializer, QuerySerializer

def fetch_flask_events():
    try:
        response = requests.get('http://127.0.0.1:5000/api/events')
        if response.status_code == 200:
            events = response.json()
            # Add source field to distinguish Flask events
            for event in events:
                event['source'] = 'flask'
            return events
    except requests.RequestException:
        return []
    return []

# Class-based views for REST API
class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

class QueryViewSet(viewsets.ModelViewSet):
    queryset = Query.objects.all()
    serializer_class = QuerySerializer

# Template Views
class EventListView(ListView):
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'

    def get_queryset(self):
        # Get Django events and add source field
        django_events = list(Event.objects.all().values())
        for event in django_events:
            event['source'] = 'django'

        # Get Flask events
        flask_events = fetch_flask_events()
        for event in flask_events:
            # Convert Flask event date to timezone-aware datetime object
            naive_date = datetime.strptime(event['date'], '%Y-%m-%d %H:%M')
            event['date'] = make_aware(naive_date)

        # Combine both sets of events
        all_events = django_events + flask_events
        return sorted(all_events, key=lambda x: x.get('date'))

class EventDetailView(DetailView):
    template_name = 'event_detail.html'
    context_object_name = 'event'

    def get_object(self):
        event_id = self.kwargs.get('pk')
        # Try to get Django event first
        try:
            return Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            # If not found, try to get Flask event
            try:
                response = requests.get(f'http://127.0.0.1:5000/api/events/{event_id}')
                if response.status_code == 200:
                    event_data = response.json()
                    event_data['source'] = 'flask'
                    return type('FlaskEvent', (), event_data)
            except requests.RequestException:
                pass
        raise Http404("Event not found")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['booking_form'] = EventBookingForm()

        # Add user_has_booking to context
        if self.request.user.is_authenticated:
            event = self.object
            context['user_has_booking'] = False
            django_reviews = []  # Initialize django_reviews to avoid UnboundLocalError
            flask_reviews = []  # Initialize flask_reviews to avoid UnboundLocalError

            if isinstance(event, Event):  # Django event
                context['user_has_booking'] = Booking.objects.filter(
                    user=self.request.user, 
                    event=event
                ).exists()
                # Add reviews for Django events
                django_reviews = list(Review.objects.filter(event=event).select_related('user').order_by('-created_at').values())
                context['review_form'] = ReviewForm()
            else:  # Flask event
                try:
                    response = requests.get(
                        f'http://127.0.0.1:5000/api/reviews/{event.id}',
                        cookies={'session': self.request.COOKIES.get('session')}
                    )
                    if response.status_code == 200:
                        flask_reviews = response.json()
                except requests.RequestException:
                    flask_reviews = []

            # Combine Flask and Django reviews
            context['reviews'] = django_reviews + flask_reviews

        return context

import requests
from django.conf import settings

@login_required
def profile(request):
    # Fetch Django bookings and reviews
    bookings = Booking.objects.filter(user=request.user)
    reviews = Review.objects.filter(user=request.user)

    # Fetch Flask bookings and reviews
    flask_bookings = []
    flask_reviews = []
    try:
        flask_bookings_response = requests.get(
            f'http://127.0.0.1:5000/api/bookings/user/{request.user.username}',
            cookies={'session': request.COOKIES.get('session')}
        )
        if flask_bookings_response.status_code == 200:
            flask_bookings = flask_bookings_response.json()
        else:
            print(f"Failed to fetch Flask bookings: {flask_bookings_response.status_code}")
    except requests.RequestException as e:
        print(f"Error fetching Flask bookings: {e}")

    try:
        flask_reviews_response = requests.get(
            f'http://127.0.0.1:5000/api/reviews/user/{request.user.username}',
            cookies={'session': request.COOKIES.get('session')}
        )
        if flask_reviews_response.status_code == 200:
            flask_reviews = flask_reviews_response.json()
        else:
            print(f"Failed to fetch Flask reviews: {flask_reviews_response.status_code}")
    except requests.RequestException as e:
        print(f"Error fetching Flask reviews: {e}")

    # Combine Django and Flask reviews and bookings
    combined_bookings = list(bookings.values()) + flask_bookings
    combined_reviews = list(reviews.values()) + flask_reviews

    return render(request, 'profile.html', {
        'bookings': combined_bookings,
        'reviews': combined_reviews
    })

@login_required
def user_bookings(request):
    # Get Django bookings
    django_bookings = Booking.objects.filter(user=request.user).select_related('event')
    
    # Get Flask bookings
    flask_bookings = []
    try:
        response = requests.get(
            'http://127.0.0.1:5000/api/bookings/user',
            cookies={'session': request.COOKIES.get('session')}
        )
        if response.status_code == 200:
            flask_bookings = response.json()
    except requests.RequestException:
        messages.error(request, 'Unable to fetch some bookings')

    return render(request, 'user_bookings.html', {
        'bookings': list(django_bookings) + flask_bookings,
        'now': timezone.now(),
    })

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registration successful! Please login.')
            return redirect('login')
        messages.error(request, 'Invalid registration details')
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})

@login_required
def book_event(request, event_id):
    try:
        # Try to get Django event first
        event = Event.objects.get(id=event_id)
        is_flask_event = False
    except Event.DoesNotExist:
        # If not found, try to get Flask event
        try:
            response = requests.get(f'http://127.0.0.1:5000/api/events/{event_id}')
            if response.status_code == 200:
                event = response.json()
                is_flask_event = True
            else:
                raise Http404("Event not found")
        except requests.RequestException:
            messages.error(request, 'Unable to connect to event server')
            return redirect('home')

    if request.method == 'POST':
        booking_form = EventBookingForm(request.POST)
        if is_flask_event:
            # Book Flask event
            try:
                book_response = requests.post(
                    f'http://127.0.0.1:5000/event/{event_id}/book', 
                    json={'notes': booking_form.data.get('notes', '')},
                    cookies={'session': request.COOKIES.get('session')}
                )
                if book_response.status_code == 200:
                    messages.success(request, 'Event booked successfully!')
                    # Redirect to booking confirmation page with event info
                    return redirect(f"{reverse('booking_confirmation', kwargs={'event_id': event_id})}?notes={booking_form.data.get('notes', '')}&status=confirmed")
                else:
                    messages.error(request, 'Failed to book event')
            except requests.RequestException:
                messages.error(request, 'Unable to connect to event server')
        else:
            # Book Django event
            if Booking.objects.filter(user=request.user, event=event).exists():
                messages.warning(request, 'You have already booked this event!')
            elif event.book_seat():
                if booking_form.is_valid():
                    booking = Booking(
                        user=request.user, 
                        event=event,
                        notes=booking_form.cleaned_data.get('notes', '')
                    )
                    booking.save()
                    messages.success(request, 'Event booked successfully!')
                    # Redirect to booking confirmation page with event info
                    return redirect(f"{reverse('booking_confirmation', kwargs={'event_id': event.id})}?notes={booking.notes}&status={booking.status}")
                else:
                    messages.error(request, 'Invalid booking form')
            else:
                messages.error(request, 'No seats available for this event!')

    return redirect('home')

@login_required
def submit_review(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    # Check for existing review
    if Review.objects.filter(user=request.user, event=event).exists():
        messages.warning(request, 'You have already reviewed this event!')
        return redirect('event_detail', pk=event_id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.event = event
            review.save()
            messages.success(request, 'Review submitted successfully!')
        else:
            messages.error(request, 'Invalid review submission!')
    
    # Redirect to the event detail page after saving the review
    return redirect('event_detail', pk=event_id)

@login_required
def submit_query(request):
    if request.method == 'POST':
        form = QueryForm(request.POST)
        if form.is_valid():
            query = form.save(commit=False)
            query.user = request.user
            query.save()
            messages.success(request, 'Query submitted successfully!')
            return redirect('profile')
    return redirect('index')

@login_required
def booking_confirmation(request, event_id):
    # Try to get Django event first
    try:
        event = Event.objects.get(id=event_id)
        is_flask_event = False
    except Event.DoesNotExist:
        # Try to get Flask event
        try:
            response = requests.get(f'http://127.0.0.1:5000/api/events/{event_id}')
            if response.status_code == 200:
                event_data = response.json()
                event_data['source'] = 'flask'
                event = type('FlaskEvent', (), event_data)
                is_flask_event = True
            else:
                messages.error(request, 'Event not found')
                return redirect('home')
        except requests.RequestException:
            messages.error(request, 'Unable to connect to event server')
            return redirect('home')

    notes = request.GET.get('notes', '')
    status = request.GET.get('status', 'confirmed')

    return render(request, 'booking_confirmation.html', {
        'event': event,
        'notes': notes,
        'status': status,
        'is_flask_event': is_flask_event,
    })
