from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Event, Review, Booking, Query

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

class EventBookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ('notes',)

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ('content', 'rating')
        widgets = {
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5}),
        }

class QueryForm(forms.ModelForm):
    class Meta:
        model = Query
        fields = ('content',)

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ('name', 'description', 'date', 'location', 'capacity', 'price')
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }