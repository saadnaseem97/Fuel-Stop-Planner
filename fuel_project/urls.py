from django.contrib import admin
from django.urls import path
from fuel_api import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/plan_route/', views.plan_route, name='plan_route'),
    path('', views.map_view, name='map'),
]