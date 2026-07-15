from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path("add-facility/", views.add_facility, name="add_facility"),
    path("api/facilities/", views.facilities_map_data, name="facilities_map_data"),
    path("api/filters/", views.facility_filters, name="facility_filters"),
    path('api/profile/update/', views.update_profile, name='update_profile'),
    path('api/password/change/', views.change_password, name='change_password'),
    path('api/facilities/list/', views.list_my_facilities, name='list_my_facilities'),
    path('api/facilities/<int:facility_id>/get/', views.get_facility_data, name='get_facility_data'),
    path('api/facilities/<int:facility_id>/update/', views.update_facility, name='update_facility'),
    path("add-activity/", views.add_activity, name="add_activity"),
    path("submit-feedback/", views.submit_feedback, name="submit_feedback"),
]