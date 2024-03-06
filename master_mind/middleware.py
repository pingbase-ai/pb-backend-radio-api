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
