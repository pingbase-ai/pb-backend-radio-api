# middleware.py
import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("django")


class TimingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        """Store the start time when the request comes in."""
        request.start_time = time.time()

    def process_response(self, request, response):
        """Calculate and log the time taken to process the request."""
        if hasattr(request, "start_time"):
            duration = time.time() - request.start_time
            current_time = time.strftime("%d/%b/%Y %H:%M:%S")
            method = request.method
            path = request.path
            status_code = response.status_code
            response_length = len(response.content)

            # Using f-string for formatting the log message
            message = f'[{current_time}] "{method} {path} HTTP/1.1" {status_code} {response_length} {duration:.2f}Seconds'
            logger.info(message)

        return response


# TODO to complete this properly.
class SelectiveCORSMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # List of paths to allow CORS
        public_paths = [
            "/api/v1/users/register-enduser",
            "/api/v1/users/enduser/init",
            "/another/public/path/",
        ]

        # Check if the requested path is in the public paths list
        if any(request.path.startswith(path) for path in public_paths):
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Origin, Content-Type, Accept"

        return response
