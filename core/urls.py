from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

from core.views import (
    create_vendor,
    delete_vendor,
    get_vendor,
    send_otp,
    turf_slots,
    vendor_status_toggle,
    verify_otp,
    signup,
    login,
    home,
    reset_password,
    list_turfs,
    turf_details,
    ground_availability,
    nearby_turfs,
    add_to_cart,
    confirm_booking,
    create_payment_order,
    verify_payment,
    turf_games,
    admin_send_otp,
    admin_login,
    admin_verify_otp,
    dashboard_summary,
    dashboard_weekly,
    users_list,
    user_toggle_active,
    turfs_list,
    bookings_list,
    booking_cancel,
    payments_list,
    vendors_list,
    vendor_approve,
    vendor_reject,
    turfs_approve,
    turfs_reject,
    vendor_create_slots,
    vendor_dashboard,
    vendor_list_slots,
    vendor_list_turfs,
    vendor_add_turf,
    vendor_booking_list,
    vendor_update_booking_status,
    vendor_list_discounts,
    vendor_create_discount,
    vendor_list,
    admin_add_turf,
)

urlpatterns = [

    # -------- USER AUTH --------
    path("send-otp/", send_otp),
    path("verify-otp/", verify_otp),
    path("signup/", signup),
    path("login/", login),
    path("home/", home),
    path("reset-password/", reset_password),

    path("turfs/<int:turf_id>/games", turf_games),

    # -------- TURFS --------
    path("turfs/", list_turfs),
    path("turfs/<int:turf_id>/", turf_details),
    path("grounds/<int:ground_id>/availability/", ground_availability),
    path("turfs/nearby/", nearby_turfs),

    # -------- BOOKINGS --------
    path("cart/add/", add_to_cart),
    path("booking/confirm/", confirm_booking),

    # -------- PAYMENTS --------
    path("payment/create-order/", create_payment_order),
    path("payment/verify/", verify_payment),

    # -------- ADMIN --------
    path("admin/send-otp/", admin_send_otp),
    path("admin/verify-otp/", admin_verify_otp),
    path("admin/login/", admin_login),
    path("admin/dashboard/summary/", dashboard_summary),
    path("admin/dashboard/weekly/", dashboard_weekly),

    path("admin/vendors/", vendors_list),
    path("admin/vendors/<int:user_id>/approve/", vendor_approve),
    path("admin/vendors/<int:user_id>/reject/", vendor_reject),

    path("admin/users/", users_list),
    path("admin/users/<int:user_id>/toggle-active/", user_toggle_active),

    path("admin/turfs/", turfs_list),
    path("turf-slots/", turf_slots),
    
    path("admin/turfs/create/", admin_add_turf),

    path("admin/turfs/<int:turf_id>/approve/", turfs_approve),
    path("admin/turfs/<int:turf_id>/reject/", turfs_reject),

    path("admin/bookings/", bookings_list),
    path("admin/bookings/<int:booking_id>/cancel/", booking_cancel),

    path("admin/payments/", payments_list),

    # -------- VENDOR MANAGEMENT --------
    path("vendors/", vendor_list),
    path("vendors/create/", create_vendor),
    path("vendors/id/<int:id>/", delete_vendor),
    path("vendors/code/<str:vendor_id>/", get_vendor),
    path("vendors/status/<int:id>/", vendor_status_toggle),

    # -------- VENDOR PANEL --------
    path("vendor/dashboard/", vendor_dashboard),
    path("vendor/turfs/", vendor_list_turfs),
    path("vendor/turfs/create/", vendor_add_turf),

    path("vendor/bookings/", vendor_booking_list),
    path("vendor/bookings/update/", vendor_update_booking_status),

    path("vendor/slots/", vendor_list_slots),
    path("vendor/slots/create/", vendor_create_slots),

    path("vendor/discounts/", vendor_list_discounts),
    path("vendor/discounts/create/", vendor_create_discount),
]

# -------- MEDIA FILES --------
# urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
