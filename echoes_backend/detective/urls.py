from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name="health_check"),
    path('cases/generate/', views.generate_case,name="generate_case"),
    path("cases/<str:case_id>/", views.get_case, name="get_case"),
]