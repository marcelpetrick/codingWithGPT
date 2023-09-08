from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Data

@csrf_exempt
def put_data(request):
    if request.method == "POST":
        data = request.POST.get('data')
        Data.objects.create(content=data)
        return JsonResponse({"status": "Data saved!"})

def get_data(request):
    data_objects = Data.objects.all()
    data_list = [obj.content for obj in data_objects]
    return JsonResponse({"data": data_list})
