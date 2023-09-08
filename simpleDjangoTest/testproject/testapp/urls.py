from django.urls import path
from . import views

urlpatterns = [
    path('putData/', views.put_data, name='put_data'),
    path('getData/', views.get_data, name='get_data'),
]

