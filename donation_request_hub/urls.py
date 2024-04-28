from django.urls import path
from . import views

urlpatterns = [
    path('', views.main_page, name='donation_hub-main'),
    path('foundations/', views.foundations, name='donation_hub-foundations'),
    path('alerts/', views.alerts, name='donation_hub-alerts'),
    path('about/', views.about, name='donation_hub-about')
]
