from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import User


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "newsletter",
            "main_activity",
        ]
        read_only_fields = ["email"]


@sensitive_post_parameters(["main_activity"])
@api_view(["PATCH"])
@permission_classes([permissions.IsAuthenticated])
def update_main_activity(request):
    serializer = UserProfileSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    request.user.main_activity = request.data.get("main_activity")
    request.user.save()
    return Response(status=204)
