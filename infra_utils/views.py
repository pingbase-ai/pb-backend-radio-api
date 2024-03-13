from django.shortcuts import render

# Create your views here.
from rest_framework import generics, views
from rest_framework.response import Response
from .mixins.custom_response import CustomResponseMixin


class CustomGenericAPIView(CustomResponseMixin, generics.GenericAPIView):
    pass


class CustomAPIView(CustomResponseMixin, views.APIView):
    pass


class CustomGenericAPIListView(CustomResponseMixin, generics.ListAPIView):
    pass
