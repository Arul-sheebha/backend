from django.db import models
from django.contrib.auth.models import User


# -------------------- ACCOUNTS --------------------

import uuid
from django.db import models

class OTP(models.Model):
    mobile = models.CharField(max_length=15)
    otp = models.CharField(max_length=6)

    token = models.UUIDField(default=uuid.uuid4, editable=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.mobile


# -------------------- TURFS --------------------

# class Turf(models.Model):
#     name = models.CharField(max_length=100)
#     location = models.CharField(max_length=255)
#     price_per_hour = models.IntegerField()

#     description = models.TextField(null=True, blank=True)

#     games = models.JSONField(default=list, blank=True)
#     amenities = models.JSONField(default=list, blank=True)
#     features = models.JSONField(default=list, blank=True)

#     # ✅ slots JSON
#     slots = models.JSONField(default=list, blank=True)

#     vendor = models.ForeignKey(
#         "Vendor",
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True
#     )

#     vendor_code = models.CharField(max_length=20, blank=True)

#     owner = models.ForeignKey(
#         User,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True
#     )

#     is_approved = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def save(self, *args, **kwargs):
#         """
#         ✅ Auto add slot id + booking status
#         """
#         updated_slots = []

#         for slot in self.slots or []:

#             # generate id if not exists
#             if "id" not in slot:
#                 slot["id"] = str(uuid.uuid4())

#             # booking flag
#             if "is_booked" not in slot:
#                 slot["is_booked"] = False

#             updated_slots.append(slot)

#         self.slots = updated_slots

#         super().save(*args, **kwargs)

#     def __str__(self):
#         return self.name
import uuid
from django.db import models
from django.contrib.auth.models import User


# =========================
# TURF
# =========================
class Turf(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    price_per_hour = models.IntegerField()

    description = models.TextField(null=True, blank=True)

    games = models.JSONField(default=list, blank=True)
    amenities = models.JSONField(default=list, blank=True)
    features = models.JSONField(default=list, blank=True)

    # ✅ OLD JSON SLOT (keep for now)
    slots = models.JSONField(default=list, blank=True)

    vendor = models.ForeignKey(
        "Vendor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    vendor_code = models.CharField(max_length=20, blank=True)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # AUTO SLOT ID FOR JSON (legacy)
    def save(self, *args, **kwargs):

        updated_slots = []

        for slot in self.slots or []:
            if not isinstance(slot, dict):
                continue

            if not slot.get("id"):
                slot["id"] = str(uuid.uuid4())

            slot.setdefault("is_booked", False)
            updated_slots.append(slot)

        self.slots = updated_slots

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# =========================
# SLOT TABLE (NEW ✅)
# =========================
class Slot(models.Model):

    turf = models.ForeignKey(
        Turf,
        on_delete=models.CASCADE,
        related_name="slot_items"   # ⭐ IMPORTANT FIX
    )

    start_time = models.TimeField()
    end_time = models.TimeField()
    price = models.IntegerField()

    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.turf.name} {self.start_time}-{self.end_time}"


# =========================
# IMAGES
# =========================
class TurfBanner(models.Model):
    turf = models.ForeignKey(
        Turf,
        on_delete=models.CASCADE,
        related_name="banners"  
    )
    image = models.ImageField(upload_to="turf/banners/")

    def __str__(self):
        return f"Banner - {self.turf.name}"


class TurfGallery(models.Model):
    turf = models.ForeignKey(
        Turf,
        on_delete=models.CASCADE,
        related_name="gallery"
    )
    image = models.ImageField(upload_to="turf/gallery/")

    def __str__(self):
        return f"Gallery - {self.turf.name}"


# =========================
# CART (FIXED FK)
# =========================
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    turf = models.ForeignKey(Turf, on_delete=models.CASCADE)

    slot = models.ForeignKey(
        "Slot",          # ⭐ string reference fix
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    date = models.DateField()

# ----------------adminlaa vendor add panna vendiya model-----------------
from django.db import models
from datetime import datetime

class Vendor(models.Model):
    venuename = models.CharField(max_length=200)
    ownername = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)

    location = models.CharField(max_length=100)
    address = models.TextField()
    pincode = models.CharField(max_length=10)

    totalturf = models.IntegerField()

    availablegames = models.JSONField()

    vendor_id = models.CharField(max_length=20, unique=True, blank=True)

    status = models.CharField(max_length=20, default="Approved")

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.vendor_id:
            prefix = self.email[:3].upper()
            year = datetime.now().year

            base_id = f"{prefix}{year}"

            count = Vendor.objects.filter(
                vendor_id__startswith=base_id
            ).count()

            if count == 0:
                self.vendor_id = base_id
            else:
                self.vendor_id = f"{base_id}-{count+1}"

        super().save(*args, **kwargs)


class Ground(models.Model):
    GAME_CHOICES = (
        ("football", "Football"),
        ("cricket", "Cricket"),
        ("badminton", "Badminton"),
        ("tennis", "Tennis"),
    )
    turf = models.ForeignKey(Turf, on_delete=models.CASCADE, related_name="grounds")
    name = models.CharField(max_length=100)
    game_type = models.CharField(max_length=50, choices=GAME_CHOICES)

    def __str__(self):
        return f"{self.turf.name} - {self.game_type}- {self.name}"


# class Slot(models.Model):
#     ground = models.ForeignKey(Ground, on_delete=models.CASCADE, related_name="slots")
#     start_time = models.TimeField()
#     end_time = models.TimeField()
#     is_booked = models.BooleanField(default=False)

#     def __str__(self):
#         return f"{self.start_time} - {self.end_time}"


# -------------------- BOOKINGS --------------------

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    turf = models.ForeignKey(Turf, on_delete=models.CASCADE)

    ground = models.ForeignKey(Ground, on_delete=models.CASCADE)
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE)
    date = models.DateField()

    def __str__(self):
        return f"Cart - {self.user.username}"


class Booking(models.Model):
    BOOKING_STATUS = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='PENDING')
    # Vendor flow: vendor approves/rejects/cancels
    vendor_status = models.CharField(max_length=20, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking {self.id} - {self.status}"


# -------------------- PAYMENTS --------------------

class Payment(models.Model):
    PAYMENT_STATUS = (
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)

    razorpay_order_id = models.CharField(max_length=200)
    razorpay_payment_id = models.CharField(max_length=200, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=300, null=True, blank=True)

    amount = models.IntegerField()  # in paise
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.booking.id} - {self.status}"



# -------------------- Admin --------------------

# Adminotp Model



class AdminOTP(models.Model):
    phone = models.CharField(max_length=10)
    email = models.EmailField()   
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} - {self.phone}"


class AdminUser(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=10, unique=True)
    password = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


