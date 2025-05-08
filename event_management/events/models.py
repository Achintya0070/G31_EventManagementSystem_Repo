from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class Event(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField()
    location = models.CharField(max_length=200)
    capacity = models.IntegerField(default=100)
    available_seats = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.id:  # Only set available_seats when creating
            self.available_seats = self.capacity
        super().save(*args, **kwargs)

    def book_seat(self):
        if self.available_seats > 0:
            self.available_seats -= 1
            self.save()
            return True
        return False

    def cancel_booking(self):
        if self.available_seats < self.capacity:
            self.available_seats += 1
            self.save()
            return True
        return False

    def get_average_rating(self):
        reviews = self.review_set.all()
        if not reviews:
            return 0
        return sum(review.rating for review in reviews) / len(reviews)

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    content = models.TextField()
    rating = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username}'s review for {self.event.name}"

    class Meta:
        unique_together = ['user', 'event']  # One review per user per event

class Booking(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    booking_date = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')

    def __str__(self):
        return f"{self.user.username}'s booking for {self.event.name}"

    class Meta:
        unique_together = ['user', 'event']  # One booking per user per event

class Query(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    response = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Query by {self.user.username}"
