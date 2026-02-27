from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Turf, TurfBanner, TurfGallery, Ground, Slot, Booking, Payment, AdminUser


class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "date_joined",
        ]


class TurfBannerSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True)
    
    class Meta:
        model = TurfBanner
        fields = ["id", "image"]


class TurfGallerySerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True)
    
    class Meta:
        model = TurfGallery
        fields = ["id", "image"]


class TurfSerializer(serializers.ModelSerializer):
    banners = TurfBannerSerializer(many=True, read_only=True)
    gallery = TurfGallerySerializer(many=True, read_only=True)
    # Keep image for backward compatibility - returns first banner
    image = serializers.SerializerMethodField()

    class Meta:
        model = Turf
        fields = "__all__"
    
    def get_image(self, obj):
        # Return first banner image for backward compatibility
        banner = obj.banners.first()
        if banner:
            return banner.image.url
        return None



class VendorTurfCreateSerializer(serializers.Serializer):
    turfName = serializers.CharField()
    location = serializers.CharField()
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False
    )
    turfCount = serializers.IntegerField(required=False)
    price = serializers.IntegerField()


class GroundSerializer(serializers.ModelSerializer):
    turf = TurfSerializer(read_only=True)

    class Meta:
        model = Ground
        fields = ["id", "turf", "turf_id", "name","game_type"]


class SlotSerializer(serializers.ModelSerializer):
    # Frontend-க்கு readable time format
    time_display = serializers.SerializerMethodField()
    # Price field add pannanum
    price_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Slot
        fields = [
            "id", 
            "turf",  # ✅ turf FK instead of ground_id
            "start_time", 
            "end_time", 
            "price",  # ✅ Added price field
            "is_available",  # ✅ is_available instead of is_booked
            "time_display",
            "price_display"
        ]
    
    def get_time_display(self, obj):
        """Frontend-friendly time format"""
        return f"{obj.start_time.strftime('%I:%M %p')} - {obj.end_time.strftime('%I:%M %p')}"
    
    def get_price_display(self, obj):
        """₹ formatted price"""
        return f"₹{obj.price}"


class BookingListSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    turf_name = serializers.CharField(source="cart.turf.name", read_only=True)
    ground_name = serializers.CharField(source="cart.ground.name", read_only=True)
    date = serializers.DateField(source="cart.date", read_only=True)
    slot_start = serializers.TimeField(source="cart.slot.start_time", read_only=True)
    slot_end = serializers.TimeField(source="cart.slot.end_time", read_only=True)
    amount = serializers.SerializerMethodField()

    def get_amount(self, obj):
        # In your backend, price is stored on Turf as price_per_hour.
        try:
            return obj.cart.turf.price_per_hour
        except Exception:
            return None

    class Meta:
        model = Booking
        fields = [
            "id",
            "user",
            "status",
            "created_at",
            "turf_name",
            "ground_name",
            "date",
            "slot_start",
            "slot_end",
            "amount",
        ]


class PaymentListSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    booking_id = serializers.IntegerField(source="booking.id", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "booking_id",
            "user",
            "razorpay_order_id",
            "razorpay_payment_id",
            "amount",
            "status",
            "created_at",
        ]
# ----------------adminserilization


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminUser
        fields = "__all__"

class AdminTurfCreateSerializer(serializers.Serializer):
    vendorId = serializers.CharField()
    name = serializers.CharField()
    location = serializers.CharField()
    price = serializers.IntegerField()

    games = serializers.ListField(child=serializers.CharField(), required=False)
    amenities = serializers.ListField(child=serializers.CharField(), required=False)
    features = serializers.ListField(child=serializers.CharField(), required=False)
    description = serializers.CharField(required=False)

    banner = serializers.ListField(
        child=serializers.ImageField(), required=False
    )
    gallery = serializers.ListField(
        child=serializers.ImageField(), required=False
    )

    slots = serializers.JSONField(required=False)