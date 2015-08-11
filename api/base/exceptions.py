def jsonapi_exception_handler(exc, context):
    """
    Custom exception handler that returns errors object as an array with a 'detail' member
    """
    from rest_framework.views import exception_handler
    response = exception_handler(exc, context)

    if response is not None and response.data['detail'] == "Authentication credentials were not provided.":
        response.status_code = 401

    return response
