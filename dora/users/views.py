from rest_framework import permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import User


class UserMainActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["main_activity"]


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def update_main_activity(request):
    serializer = UserMainActivitySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    request.user.main_activity = serializer.validated_data["main_activity"]
    request.user.save()
    return Response(status=204)
