import random
from datetime import timedelta,datetime
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from math import radians, cos, sin, asin, sqrt
from django.db.models import F
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import ListAPIView

from core.serializers import SlotSerializer, TurfSerializer,BookingListSerializer,VendorTurfCreateSerializer,AdminTurfCreateSerializer
from core.models import (
    OTP,
    Cart,
    Booking,
    Payment,
    Turf,
    Ground,
    Slot, 
    AdminOTP, 
    AdminUser,
)

@api_view(['GET'])
def home(request):
    return Response({
        "message": "Home API working",
        "status": "ok"
    })


@api_view(['POST'])
def send_otp(request):
    mobile = request.data.get('mobile')
    if not mobile:
        return Response({"error": "Mobile required"}, status=400)

    OTP.objects.filter(mobile=mobile).delete()
    otp = str(random.randint(100000, 999999))
    OTP.objects.create(mobile=mobile, otp=otp)

    return Response({"message": "OTP sent"})

@api_view(['POST'])
def verify_otp(request):
    mobile = request.data.get('mobile')
    otp = request.data.get('otp')

    try:
        otp_obj = OTP.objects.get(
            mobile=mobile,
            otp=otp,
            created_at__gte=timezone.now() - timedelta(minutes=5),
            is_verified=False
        )
    except OTP.DoesNotExist:
        return Response({"error": "Invalid OTP"}, status=400)

    otp_obj.is_verified = True
    otp_obj.save()

    # ✅ IMPORTANT
    return Response({
        "message": "OTP verified",
        "otp_token": str(otp_obj.token)
    })


@api_view(['POST'])
def signup(request):
    mobile = request.data.get('mobile')
    password = request.data.get('password')
    otp_token = request.data.get('otp_token')

    if not all([mobile, password, otp_token]):
        return Response({"error": "Missing fields"}, status=400)

    try:
        otp_obj = OTP.objects.get(
            mobile=mobile,
            token=otp_token,
            is_verified=True
        )
    except OTP.DoesNotExist:
        return Response({"error": "OTP verification failed"}, status=400)

    if User.objects.filter(username=mobile).exists():
        return Response({"error": "User already exists"}, status=400)

    User.objects.create(
        username=mobile,
        password=make_password(password)
    )

    # OTP invalidate after use
    otp_obj.delete()

    return Response({"message": "Account created successfully"})


@api_view(['POST'])
def login(request):
    mobile = request.data.get('mobile')
    password = request.data.get('password')

    if not mobile or not password:
        return Response({"error": "Mobile and password required"}, status=400)

    user = authenticate(username=mobile, password=password)

    if user is None:
        return Response({"error": "Invalid credentials"}, status=401)

    refresh = RefreshToken.for_user(user)

    return Response({
        "token": str(refresh.access_token),
        "refresh": str(refresh),
        "message": "Login successful"
    })


@api_view(['GET'])
def list_turfs(request):
    date_str = request.GET.get('date')
    
    qs = Turf.objects.select_related("owner", "vendor").prefetch_related(
        "banners", "gallery", "slot_items"
    ).filter(is_approved=True).order_by("-id")

    data = []
    for t in qs:
        available_slots = []
        
        # NEW SLOTS
        if hasattr(t, 'slot_items') and t.slot_items.exists():
            slots_qs = t.slot_items.filter(is_available=True)
                
            for slot in slots_qs:
                available_slots.append({
                    "id": slot.id,
                    "start_time": slot.start_time.strftime("%H:%M"),
                    "end_time": slot.end_time.strftime("%H:%M"),
                    "time_display": f"{slot.start_time.strftime('%I:%M %p')} - {slot.end_time.strftime('%I:%M %p')}",
                    "price_display": f"₹{slot.price}",
                    "price": slot.price,
                    "is_available": slot.is_available
                })
        else:
            # Legacy JSON fallback
            for slot in t.slots or []:
                if not slot.get("is_booked", False):
                    available_slots.append({
                        "id": slot.get("id"),
                        "start_time": slot.get("start_time", ""),
                        "end_time": slot.get("end_time", ""),
                        "time_display": slot.get("slot_display", ""),
                        "price": slot.get("price", t.price_per_hour),
                        "price_display": f"₹{slot.get('price', t.price_per_hour)}",
                        "is_available": True
                    })

        data.append({
            "id": t.id,
            "name": t.name,
            "location": t.location,
            "price_per_hour": t.price_per_hour,
            "description": t.description or "",
            "games": t.games or [],
            "amenities": t.amenities or [],
            "features": t.features or [],
            
            "banner_images": [img.image.url for img in t.banners.all()],
            "gallery_images": [img.image.url for img in t.gallery.all()],
            "slots": available_slots,
            
            "vendor": {
                "vendor_id": getattr(t.vendor, 'vendor_id', None) if t.vendor else None,
                "venuename": getattr(t.vendor, 'venuename', None) if t.vendor else None,
            },
            
            "owner": {
                "id": t.owner.id if t.owner else None,
                "username": t.owner.username if t.owner else None,
                "email": t.owner.email if t.owner else None,
            } if t.owner else {"id": None, "username": None, "email": None},
            
            "is_approved": t.is_approved,
        })

    return Response(data)


@api_view(['GET'])
def turf_details(request, turf_id):
    turf = Turf.objects.get(id=turf_id)
    return Response({
        "id": turf.id,
        "name": turf.name,
        "location": turf.location,
        "price_per_hour": turf.price_per_hour
    })

@api_view(['GET'])
def ground_availability(request):
    turf_id=request.query_params.get('turf_id')
    game_type=request.query_params.get('game')
    if not turf_id or not game_type:
        return Response({"error": "turf_id and game required"}, status=400)
    grounds = Ground.objects.filter(turf_id=turf_id, game_type=game_type)
    data =[]
    for ground in grounds:
        slots = Slot.objects.filter(ground=ground,is_booked=False).values()

        data.append({
            "ground_id": ground.id,
            "ground_name": ground.name,
            "game": ground.game_type,
            "slots": list(slots)
        })

    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    Cart.objects.create(
        user=request.user,
        turf_id=request.data['turf_id'],
        ground_id=request.data['ground_id'],
        date=request.data['date'],
        slot_id=request.data['slot_id']
    )
    return Response({"message": "Added to cart"})
from django.db import transaction

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_booking(request):

    slot_ids = request.data.get("slot_ids", [])

    with transaction.atomic():

        slots = Slot.objects.select_for_update().filter(
            id__in=slot_ids,
            is_available=True
        )

        if slots.count() != len(slot_ids):
            return Response(
                {"error": "Some slots already booked"},
                status=400
            )

        # LOCK SLOTS
        slots.update(is_available=False)

        cart = Cart.objects.create(
            user=request.user,
            turf_id=request.data["turf_id"],
            date=request.data["date"]
        )

        booking = Booking.objects.create(
            user=request.user,
            cart=cart,
            status="CONFIRMED"
        )

    return Response({"booking_id": booking.id})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_order(request):
    booking = Booking.objects.get(id=request.data['booking_id'])

    payment = Payment.objects.create(
        user=request.user,
        booking=booking,
        razorpay_order_id="dummy_order_id",
        amount=request.data.get("amount", 50000),
        status="PENDING"
    )

    return Response({
        "order_id": payment.razorpay_order_id,
        "amount": payment.amount
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    payment = Payment.objects.get(
        razorpay_order_id=request.data['order_id']
    )
    payment.status = "SUCCESS"
    payment.save()

    return Response({"message": "Payment successful"})

@api_view(["GET"])
def nearby_turfs(request):
    lat = request.query_params.get("lat")
    lng = request.query_params.get("lng")
    radius_km = float(request.query_params.get("radius", 10))

    if not lat or not lng:
        return Response({"error": "lat and lng required"}, status=400)

    lat = float(lat)
    lng = float(lng)

    turfs = Turf.objects.filter(is_approved=True)

    results = []
    for turf in turfs:
        if turf.latitude is None or turf.longitude is None:
            continue

        # Haversine distance
        dlat = radians(turf.latitude - lat)
        dlon = radians(turf.longitude - lng)
        a = sin(dlat/2)**2 + cos(radians(lat)) * cos(radians(turf.latitude)) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        distance = 6371 * c  # km

        if distance <= radius_km:
            results.append({
                "id": turf.id,
                "name": turf.name,
                "location": turf.location,
                "distance_km": round(distance, 2),
            })

    return Response(results)

@api_view(['GET'])
def turf_games(request, turf_id):
    games=Ground.objects.filter(turf_id=turf_id)\
        .values("game_type").distinct()
    return Response(list(games))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).select_related(
        "cart", "cart__turf"
    )

    data = []
    for booking in bookings:
        turf = booking.cart.turf

        image_url = (
            request.build_absolute_uri(turf.image.url)
            if turf.image else None
        )

        data.append({
            "id": booking.id,
            "turf_name": turf.name,
            "date": booking.created_at.strftime("%b %d, %Y"),
            "time": "Slots based",
            "price": booking.cart.total_price,
            "status": booking.status,
            "image": image_url
        })

    return Response(data)





@api_view(['POST'])
def reset_password(request):
    mobile = request.data.get('mobile')
    new_password = request.data.get('password')
    otp_token = request.data.get('otp_token')

    if not all([mobile, new_password, otp_token]):
        return Response({"error": "Missing fields"}, status=400)

    try:
        otp_obj = OTP.objects.get(
            mobile=mobile,
            token=otp_token,
            is_verified=True
        )
    except OTP.DoesNotExist:
        return Response({"error": "OTP verification failed"}, status=400)

    try:
        user = User.objects.get(username=mobile)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    user.password = make_password(new_password)
    user.save()

    # ❌ Invalidate OTP after use
    otp_obj.delete()

    return Response({"message": "Password reset successful"})

class TurfListView(ListAPIView):
    queryset = Turf.objects.all()
    serializer_class = TurfSerializer

    def get_serializer_context(self):
        context= super().get_serializer_context()
        context.update({"request": self.request})
        return context

# -------------------Admin Views ---------------------------#

@api_view(['POST'])
def admin_send_otp(request):
    phone = request.data.get('phone')
    otp = str(random.randint(100000, 999999))

    AdminOTP.objects.create(phone=phone, otp=otp)
    print("ADMIN OTP:", otp)

    return Response({"message": "Admin OTP sent"})


@api_view(['POST'])
def admin_verify_otp(request):
    phone = request.data.get('phone')
    otp = request.data.get('otp')
    password = request.data.get('password')
    email = request.data.get('email')

    otp_qs = AdminOTP.objects.filter(phone=phone, otp=otp)

    if not otp_qs.exists():
        return Response({"error": "Invalid OTP"}, status=400)

    # 🔴 ADD THIS CHECK (HERE)
    if AdminUser.objects.filter(email=email).exists():
        return Response({"error": "Email already exists"}, status=400)

    admin = AdminUser.objects.filter(phone=phone).first()
    if not admin:
        AdminUser.objects.create(
            name=request.data.get("name", ""),
            email=email,
            phone=phone,
            password=make_password(password)
        )

    otp_qs.delete()
    return Response({"message": "Admin account created"})
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User

@api_view(['POST'])
def admin_login(request):
    password = request.data.get("password")
    email = request.data.get("email")
    phone = request.data.get("phone")

    try:
        if email:
            admin = AdminUser.objects.get(email=email)
        elif phone:
            admin = AdminUser.objects.get(phone=phone)
        else:
            return Response({"error": "Email or phone required"}, status=400)
    except AdminUser.DoesNotExist:
        return Response({"error": "Invalid credentials"}, status=400)

    if not check_password(password, admin.password):
        return Response({"error": "Invalid credentials"}, status=400)

    # JWT needs Django User
    user, _ = User.objects.get_or_create(username=admin.email)

    refresh = RefreshToken.for_user(user)

    return Response({
        "token": str(refresh.access_token),
        "refresh": str(refresh),
        "message": "Login successful"
    })


@staff_member_required
def dashboard_summary(request):
    """Admin dashboard KPIs similar to your React admin pages."""
    total_users = User.objects.count()
    total_turfs = Turf.objects.count()

    # You don't have a Vendor model in this backend; return 0 so UI can render.
    total_vendors = 0

    total_bookings = Booking.objects.count()
    today = timezone.localdate()
    today_bookings = Booking.objects.filter(created_at__date=today).count()
    today_new_users = User.objects.filter(date_joined__date=today).count()

    # Revenue from successful payments (amount stored in paise)
    total_revenue_paise = (
        Payment.objects.filter(status="SUCCESS").aggregate(s=Sum("amount"))["s"] or 0
    )
    today_revenue_paise = (
        Payment.objects.filter(status="SUCCESS", created_at__date=today).aggregate(s=Sum("amount"))["s"]
        or 0
    )

    payload = {
        "total_users": total_users,
        "total_vendors": total_vendors,
        "total_turfs": total_turfs,
        "total_bookings": total_bookings,
        "today": {
            "bookings": today_bookings,
            "revenue_paise": today_revenue_paise,
            "new_users": today_new_users,
            "new_vendors": 0,
        },
        "revenue": {
            "total_paise": total_revenue_paise,
        },
    }
    return JsonResponse(payload)


@staff_member_required
def dashboard_weekly(request):
    """Returns last 7 days booking counts and revenue totals for chart."""
    today = timezone.localdate()
    start = today - timezone.timedelta(days=6)
    days = [start + timezone.timedelta(days=i) for i in range(7)]

    booking_counts = {
        row["d"]: row["c"]
        for row in Booking.objects.filter(created_at__date__gte=start, created_at__date__lte=today)
        .extra(select={"d": "date(created_at)"})
        .values("d")
        .annotate(c=Count("id"))
    }

    revenue = {
        row["d"]: row["s"]
        for row in Payment.objects.filter(
            status="SUCCESS", created_at__date__gte=start, created_at__date__lte=today
        )
        .extra(select={"d": "date(created_at)"})
        .values("d")
        .annotate(s=Sum("amount"))
    }

    payload = {
        "labels": [d.strftime("%a") for d in days],
        "bookings": [int(booking_counts.get(d, 0)) for d in days],
        "revenue_paise": [int(revenue.get(d, 0) or 0) for d in days],
    }
    return JsonResponse(payload)


@staff_member_required
def users_list(request):
    qs = User.objects.all().order_by("-date_joined")
    data = [
        {
            "id": u.id,
            "username": u.username,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "email": u.email,
            "is_active": u.is_active,
            "date_joined": u.date_joined,
        }
        for u in qs
    ]
    return JsonResponse({"results": data})


@staff_member_required
def user_toggle_active(request, user_id: int):
    if request.method not in ("POST", "PATCH"):
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    try:
        u = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"detail": "User not found"}, status=404)
    u.is_active = not u.is_active
    u.save(update_fields=["is_active"])
    return JsonResponse({"id": u.id, "is_active": u.is_active})



@api_view(["GET"])
@permission_classes([AllowAny])
def turfs_list(request):
    date_str = request.GET.get('date')
    
    qs = Turf.objects.select_related("owner", "vendor").prefetch_related(
        "banners", "gallery", "slot_items"
    ).filter(is_approved=True).order_by("-id")

    data = []
    for t in qs:
        available_slots = []
        
        # NEW SLOTS ✅
        if hasattr(t, 'slot_items') and t.slot_items.exists():
            slots_qs = t.slot_items.filter(is_available=True)
            
            # Date filter (if date field added later)
            if date_str:
                # slots_qs = slots_qs.filter(date=date_str)  # Add date field to Slot
                pass
                
            for slot in slots_qs:
                available_slots.append({
                    "id": slot.id,
                    "start_time": slot.start_time.strftime("%H:%M"),
                    "end_time": slot.end_time.strftime("%H:%M"),
                    "time_display": f"{slot.start_time.strftime('%I:%M %p')} - {slot.end_time.strftime('%I:%M %p')}",
                    "price_display": f"₹{slot.price}",
                    "price": slot.price,
                    "is_available": slot.is_available
                })
        else:
            # Legacy JSON fallback
            for slot in t.slots or []:
                if not slot.get("is_booked", False):
                    available_slots.append({
                        "id": slot.get("id"),
                        "start_time": slot.get("start_time", ""),
                        "end_time": slot.get("end_time", ""),
                        "time_display": slot.get("slot_display", ""),
                        "price": slot.get("price", t.price_per_hour),
                        "price_display": f"₹{slot.get('price', t.price_per_hour)}",
                        "is_available": True
                    })

        data.append({
            "id": t.id,
            "name": t.name,
            "location": t.location,
            "price_per_hour": t.price_per_hour,
            "description": t.description or "",
            "games": t.games or [],
            "amenities": t.amenities or [],
            "features": t.features or [],
            
            "banner_images": [img.image.url for img in t.banners.all()],
            "gallery_images": [img.image.url for img in t.gallery.all()],
            "slots": available_slots,  # ✅ Dynamic slots ready
            
            # ✅ SAFE VENDOR ACCESS
            "vendor": {
                "vendor_id": getattr(t.vendor, 'vendor_id', None) if t.vendor else None,
                "venuename": getattr(t.vendor, 'venuename', None) if t.vendor else None,
            },
            
            # ✅ SAFE OWNER ACCESS
            "owner": {
                "id": t.owner.id if t.owner else None,
                "username": t.owner.username if t.owner else None,
                "email": t.owner.email if t.owner else None,
            } if t.owner else {"id": None, "username": None, "email": None},
            
            "is_approved": t.is_approved,
        })

    return Response({"results": data})

@api_view(['GET'])
def turf_detail(request, turf_id):
    """Single turf with all slots"""
    try:
        turf = Turf.objects.get(id=turf_id, is_approved=True)
        slots = Slot.objects.filter(turf=turf).order_by('start_time')
        
        return Response({
            'id': turf.id,
            'name': turf.name,
            'location': turf.location,
            'price_per_hour': turf.price_per_hour,
            'description': turf.description,
            'games': turf.games,
            'amenities': turf.amenities,
            'features': turf.features,
            'slots': SlotSerializer(slots, many=True).data,
            'banners': [banner.image.url for banner in turf.banners.all()],
            'gallery': [img.image.url for img in turf.gallery.all()]
        })
    except Turf.DoesNotExist:
        return Response({"error": "Turf not found"}, status=404)
    
    
@staff_member_required
def bookings_list(request):
    qs = Booking.objects.select_related("user", "cart", "cart__turf", "cart__ground", "cart__slot").order_by(
        "-created_at"
    )
    data = []
    for b in qs:
        data.append(
            {
                "id": b.id,
                "status": b.status,
                "created_at": b.created_at,
                "user": {
                    "id": b.user.id,
                    "username": b.user.username,
                    "email": b.user.email,
                },
                "turf": {
                    "id": b.cart.turf_id,
                    "name": getattr(b.cart.turf, "name", None),
                },
                "ground": {
                    "id": b.cart.ground_id,
                    "name": getattr(b.cart.ground, "name", None),
                },
                "date": b.cart.date,
                "slot": {
                    "id": b.cart.slot_id,
                    "start_time": getattr(b.cart.slot, "start_time", None),
                    "end_time": getattr(b.cart.slot, "end_time", None),
                },
                "amount_paise": getattr(b.cart.turf, "price_per_hour", None),
            }
        )
    return JsonResponse({"results": data})


@staff_member_required
def booking_cancel(request, booking_id: int):
    if request.method not in ("POST", "PATCH"):
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    try:
        b = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return JsonResponse({"detail": "Booking not found"}, status=404)
    b.status = "CANCELLED"
    b.save(update_fields=["status"])
    return JsonResponse({"id": b.id, "status": b.status})


@staff_member_required
def payments_list(request):
    qs = Payment.objects.select_related("user", "booking").order_by("-created_at")
    data = [
        {
            "id": p.id,
            "booking_id": p.booking_id,
            "user": {
                "id": p.user.id,
                "username": p.user.username,
                "email": p.user.email,
            },
            "razorpay_order_id": p.razorpay_order_id,
            "razorpay_payment_id": p.razorpay_payment_id,
            "amount": p.amount,
            "status": p.status,
            "created_at": p.created_at,
        }
        for p in qs
    ]
    return JsonResponse({"results": data})


# --- Vendor endpoints (stub) ---
# Your backend doesn't include a Vendor model yet.
# These endpoints exist so your Admin React flow won't break.


@staff_member_required
def vendors_list(request):
    return JsonResponse({"results": []})


@staff_member_required
def vendor_approve(request, user_id: int):
    return JsonResponse({"detail": "Vendor module not implemented in backend"}, status=501)


@staff_member_required
def vendor_reject(request, user_id: int):
    return JsonResponse({"detail": "Vendor module not implemented in backend"}, status=501)

@staff_member_required
def turfs_approve(request, turf_id):
    if request.method not in ("POST", "PATCH"):
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    try:
        turf = Turf.objects.get(id=turf_id)
    except Turf.DoesNotExist:
        return JsonResponse({"detail": "Turf not found"}, status=404)

    turf.is_approved = True
    turf.save(update_fields=["is_approved"])

    return JsonResponse({
        "id": turf.id,
        "is_approved": True,
        "message": "Turf approved"
    })


@staff_member_required
def turfs_reject(request, turf_id):
    if request.method not in ("POST", "PATCH"):
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    try:
        turf = Turf.objects.get(id=turf_id)
    except Turf.DoesNotExist:
        return JsonResponse({"detail": "Turf not found"}, status=404)

    turf.is_approved = False
    turf.save(update_fields=["is_approved"])

    return JsonResponse({
        "id": turf.id,
        "is_approved": False,
        "message": "Turf rejected"
    })

# -----------------Vendor Views --------------------#

# --------- Helpers

def _ensure_vendor(user: User) -> bool:
    # Minimal vendor rule: must be authenticated. You can tighten this later.
    return user and user.is_authenticated


# --------- Vendor Dashboard

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_dashboard(request):
    """Return stats for Vendor/Dashboard.jsx.

    Notes:
    - Your frontend currently uses dummy data; this endpoint gives real data
      based on turfs owned by the logged-in user.
    """

    if not _ensure_vendor(request.user):
        return Response({"detail": "Unauthorized"}, status=401)

    owner = request.user
    owned_turfs = Turf.objects.filter(owner=owner)
    turf_ids = list(owned_turfs.values_list("id", flat=True))

    # Bookings for owned turfs via Cart -> Turf
    bookings_qs = Booking.objects.filter(cart__turf_id__in=turf_ids)

    today = now().date()
    todays = bookings_qs.filter(cart__date=today).count()
    upcoming = bookings_qs.filter(cart__date__gt=today).count()

    # Earnings: sum successful payments for those bookings
    earnings = (
        Payment.objects.filter(booking__in=bookings_qs, status="SUCCESS")
        .aggregate(total=Sum("amount"))
        .get("total")
        or 0
    )

    pending_approvals = bookings_qs.filter(vendor_status__iexact="PENDING").count()

    data = {
        "stats": [
            {"title": "Total Turfs Owned", "value": owned_turfs.count(), "icon": "🏠"},
            {"title": "Today’s Bookings", "value": todays, "icon": "📅"},
            {"title": "Upcoming Bookings", "value": upcoming, "icon": "🗓️"},
            # amounts stored in paise; convert to rupees for display
            {"title": "Monthly Earnings", "value": round(earnings / 100, 2), "icon": "💲"},
            {"title": "Pending Approvals", "value": pending_approvals, "icon": "⏳"},
        ],
        # Keep these for UI compatibility (frontend shows these blocks)
        "coaches": [],
        "reviews": [],
    }

    return Response(data)


# --------- Turfs

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_list_turfs(request):
    turfs = Turf.objects.filter(owner=request.user)
    return Response(TurfSerializer(turfs, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def vendor_add_turf(request):
    ser = VendorTurfCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    payload = ser.validated_data

    turf_count = payload.get("turfCount") or 1

    turf = Turf.objects.create(
        name=payload["turfName"],
        location=payload["location"],
        latitude=payload.get("latitude"),
        longitude=payload.get("longitude"),
        price_per_hour=payload["price"],
        owner=request.user,
        is_approved=False,
    )

    for i in range(1, turf_count + 1):
        Ground.objects.create(turf=turf, name=f"Ground {i}")

    return Response({
        "success": True,
        "turf_id": turf.id
    })


# --------- Booking Management

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_booking_list(request):
    """Return bookings belonging to vendor-owned turfs."""
    turfs = Turf.objects.filter(owner=request.user)
    turf_ids = list(turfs.values_list("id", flat=True))
    qs = Booking.objects.select_related("user", "cart", "cart__turf", "cart__ground", "cart__slot").filter(
        cart__turf_id__in=turf_ids
    ).order_by("-created_at")

    data = BookingListSerializer(qs, many=True).data
    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def vendor_update_booking_status(request):
    """Used by Vendor/BookingManagement.jsx (placeholder).

    Accepts:
      { bookingId: "#BK101" or 123, status: "Approved"|"Rejected"|"Cancelled" }
    We map this to Booking.vendor_status and optionally Booking.status.
    """
    booking_id = request.data.get("bookingId")
    status_text = (request.data.get("status") or "").strip()

    if not booking_id or not status_text:
        return Response({"success": False, "error": "bookingId and status required"}, status=400)

    # bookingId may come as "#BK101" in UI dummy; try to parse digits
    if isinstance(booking_id, str) and booking_id.startswith("#"):
        digits = "".join([c for c in booking_id if c.isdigit()])
        booking_id = int(digits) if digits else None

    try:
        booking = Booking.objects.select_related("cart", "cart__turf").get(id=booking_id)
    except Exception:
        return Response({"success": False, "error": "Booking not found"}, status=404)

    # Ensure booking belongs to vendor
    if booking.cart.turf.owner_id != request.user.id:
        return Response({"success": False, "error": "Forbidden"}, status=403)

    normalized = status_text.upper()
    if normalized == "APPROVED":
        booking.vendor_status = "APPROVED"
        booking.status = "CONFIRMED"
    elif normalized == "REJECTED":
        booking.vendor_status = "REJECTED"
        booking.status = "CANCELLED"
    elif normalized == "CANCELLED":
        booking.vendor_status = "CANCELLED"
        booking.status = "CANCELLED"
    else:
        booking.vendor_status = status_text

    booking.save(update_fields=["vendor_status", "status"])
    return Response({"success": True})


# --------- Schedule Time (Slots)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_list_slots(request):
    """List slots for a ground (and vendor must own the turf)."""
    ground_id = request.query_params.get("ground_id")
    if not ground_id:
        return Response({"error": "ground_id required"}, status=400)

    try:
        ground = Ground.objects.select_related("turf").get(id=ground_id)
    except Ground.DoesNotExist:
        return Response({"error": "Ground not found"}, status=404)

    if ground.turf.owner_id != request.user.id:
        return Response({"error": "Forbidden"}, status=403)

    slots = Slot.objects.filter(ground=ground).order_by("start_time")
    return Response(
        [
            {
                "id": s.id,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "is_booked": s.is_booked,
            }
            for s in slots
        ]
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def vendor_create_slots(request):
    """Create slots for a ground.

    Expected payload:
      { ground_id: 1, slots: [{start_time: "06:00", end_time: "07:00"}, ...] }
    """
    ground_id = request.data.get("ground_id")
    slots = request.data.get("slots") or []

    if not ground_id or not isinstance(slots, list) or not slots:
        return Response({"success": False, "error": "ground_id and slots[] required"}, status=400)

    try:
        ground = Ground.objects.select_related("turf").get(id=ground_id)
    except Ground.DoesNotExist:
        return Response({"success": False, "error": "Ground not found"}, status=404)

    if ground.turf.owner_id != request.user.id:
        return Response({"success": False, "error": "Forbidden"}, status=403)

    created = 0
    for item in slots:
        st = item.get("start_time")
        et = item.get("end_time")
        if not st or not et:
            continue
        Slot.objects.create(ground=ground, start_time=st, end_time=et)
        created += 1

    return Response({"success": True, "created": created})


# --------- Discount (placeholder – no Discount model in backend yet)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_list_discounts(request):
    """Placeholder: frontend has DiscountPage but backend has no Discount model.

    Returns empty list for now.
    """
    return Response([])


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def vendor_create_discount(request):
    """Placeholder endpoint so frontend can submit Deal Request."""
    return Response({"success": True})

# ----------------adminlaa vendor add panna vendiya model-----------------
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import TurfBanner, TurfGallery, Vendor
from datetime import datetime

@api_view(['POST'])
def create_vendor(request):
    try:
        data = request.data

        vendor = Vendor.objects.create(
            venuename=data.get("venuename"),
            ownername=data.get("ownername"),
            email=data.get("email"),
            phone=data.get("phone"),
            location=data.get("location"),
            address=data.get("address"),
            pincode=data.get("pincode"),
            totalturf=int(data.get("totalturf")),
            availablegames=data.get("availablegames", []),
            status="Approved"
        )

        return Response({
            "message": "Vendor Created",
            "vendor_id": vendor.vendor_id
        })

    except Exception as e:
        return Response({"error": str(e)}, status=400)
# ------------add turf page laa vendor id kuduta name varnu------------------------------
@api_view(['GET'])
def get_vendor(request, vendor_id):
    try:
        vendor = Vendor.objects.get(vendor_id=vendor_id)

        return Response({
            "vendor_id": vendor.vendor_id,
            "venuename": vendor.venuename
        })

    except Vendor.DoesNotExist:
        return Response(
            {"error": "Vendor not found"},
            status=404
        )

# ------------- vendor list------------------
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Vendor
from django.forms.models import model_to_dict


@api_view(['GET'])
def vendor_list(request):
    vendors = Vendor.objects.all().order_by('-created_at')

    data = []
    for v in vendors:
        data.append({
            "id": v.id,
            "vendor_id": v.vendor_id,
            "venuename": v.venuename,
            "ownername": v.ownername,
            "phone": v.phone,
            "location": v.location,
            "totalturf": v.totalturf,
            "status": v.status,
        })

    return Response(data)
@api_view(['DELETE'])
def delete_vendor(request, id):
    try:
        vendor = Vendor.objects.get(vendor_id=id)
        vendor.delete()
        return Response({"message": "Deleted"})
    except Vendor.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
    

@api_view(['PUT'])
def vendor_status_toggle(request, id):
    vendor = Vendor.objects.get(vendor_id=id)
    vendor.status = request.data.get("status")
    vendor.save()

    return Response({"message": "Status updated"})


#------------------Admin Adding Turf through vendor id---------------------#
from datetime import datetime
import json

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_add_turf(request):

    ser = AdminTurfCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    # -------------------------
    # ✅ GET VENDOR
    # -------------------------
    vendor = Vendor.objects.get(vendor_id=data["vendorId"])

    # -------------------------
    # ✅ CREATE TURF
    # -------------------------
    turf = Turf.objects.create(
        name=data["name"],
        location=data["location"],
        price_per_hour=data["price"],
        description=data.get("description", ""),
        games=data.get("games", []),
        amenities=data.get("amenities", []),
        features=data.get("features", []),
        vendor=vendor,
        vendor_code=vendor.vendor_id,
        owner=request.user,
        is_approved=True
    )

    # -------------------------
    # ✅ CREATE SLOT ROWS (FIXED)
    # -------------------------
    slots = data.get("slots", [])

    # FormData sends string
    if isinstance(slots, str):
        slots = json.loads(slots)

    for s in slots:

        # ⭐ CONVERT STRING → TIME OBJECT
        start_time = datetime.strptime(
            s["from"], "%I:%M %p"
        ).time()

        end_time = datetime.strptime(
            s["to"], "%I:%M %p"
        ).time()

        Slot.objects.create(
            turf=turf,
            start_time=start_time,
            end_time=end_time,
            price=s["price"],
            is_available=True
        )

    # -------------------------
    # ✅ SAVE BANNERS
    # -------------------------
    for img in request.FILES.getlist("banner_images"):
        TurfBanner.objects.create(
            turf=turf,
            image=img
        )

    # -------------------------
    # ✅ SAVE GALLERY
    # -------------------------
    for img in request.FILES.getlist("gallery_images"):
        TurfGallery.objects.create(
            turf=turf,
            image=img
        )

    return Response({
        "success": True,
        "turf_id": turf.id
    }, status=201)

@api_view(["POST"])
def book_slot(request):

    turf = Turf.objects.get(id=request.data["turf_id"])
    slot_id = request.data["slot_id"]

    slots = turf.slots

    for slot in slots:
        if slot["id"] == slot_id:
            if slot["is_booked"]:
                return Response({"error": "Already booked"}, status=400)

            slot["is_booked"] = True

    turf.slots = slots
    turf.save()

    return Response({"success": True})

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime
from .models import Slot


@api_view(["GET"])
def turf_slots(request):

    turf_id = request.query_params.get("turf_id")
    date_str = request.query_params.get("date")   # ⭐ selected date

    # ================= VALIDATION =================
    if not turf_id:
        return Response({"error": "turf_id required"}, status=400)

    # ================= BASE QUERY =================
    slots = Slot.objects.filter(
        turf_id=turf_id,
        is_available=True
    )

    selected_date = None

    # ================= DATE FILTER =================
    if date_str:
        try:
            selected_date = datetime.strptime(
                date_str, "%Y-%m-%d"
            ).date()

            # if booking_date field exists
            if hasattr(Slot, "booking_date"):
                slots = slots.filter(booking_date=selected_date)

        except ValueError:
            return Response({"error": "Invalid date format"}, status=400)

    # ================= HIDE PAST TIME ⭐ IMPORTANT =================
    today = timezone.localdate()

    if selected_date and selected_date == today:
        now_time = timezone.localtime().time()

        # hide previous slots
        slots = slots.filter(start_time__gt=now_time)

    # ================= ORDER =================
    slots = slots.order_by("start_time")

    # ================= RESPONSE =================
    data = [
        {
            "id": s.id,
            "start_time": s.start_time.strftime("%H:%M:%S"),
            "end_time": s.end_time.strftime("%H:%M:%S"),
            "time_display": f"{s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}",
            "price": s.price,
            "is_available": s.is_available,
        }
        for s in slots
    ]

    return Response(data)