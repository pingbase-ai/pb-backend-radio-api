from django.shortcuts import render
from rest_framework.response import Response
from infra_utils.views import CustomGenericAPIView
from rest_framework.permissions import AllowAny

# Create your views here.


class HealthCheckView(CustomGenericAPIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        return Response({"status": "ok"}, status=200)
