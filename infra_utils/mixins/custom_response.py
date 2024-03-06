from rest_framework.response import Response


class CustomResponseMixin:
    def finalize_response(self, request, response, *args, **kwargs):
        # Check if the response is a DRF Response instance
        if isinstance(response, Response):
            # Modify response data here
            data = {
                "success": True if response.status_code < 400 else False,
                "data": response.data,
            }
            response.data = data
        return super().finalize_response(request, response, *args, **kwargs)
