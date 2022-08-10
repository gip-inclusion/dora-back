from rest_framework import permissions

from dora.structures.models import Structure, StructureMember


class StructurePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user

        # Nobody can delete a structure
        if request.method == "DELETE":
            return False

        # Anybody can read
        if request.method in permissions.SAFE_METHODS:
            return True

        # Authentified user can read and write
        return user and user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        # Anybody can read
        if request.method in permissions.SAFE_METHODS:
            return True

        # Staff can do anything
        if user.is_staff:
            return True

        # People can only edit their Structures' stuff
        user_structures = Structure.objects.filter(membership__user=user)
        return obj in user_structures


class StructureMemberPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user and user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        # You can't create a Member via the API (must be a Putative Member)
        if request.method == "POST":
            return False

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Staff can do anything
        if user.is_staff:
            return True

        # Struct admin can only edit their Structures' stuff
        if obj.structure in Structure.objects.filter(
            membership__user=user, membership__is_admin=True
        ):
            return True

        # People can only see their Structures' stuff
        if obj.structure in Structure.objects.filter(membership__user=user):
            return request.method in permissions.SAFE_METHODS

        # bizdevs can read only
        if user.is_bizdev:
            return request.method in permissions.SAFE_METHODS

        return False


class StructurePutativeMemberPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user and user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method == "POST":
            structure_slug = request.query_params.get("structure")
            if not structure_slug:
                return False
            # Check that we are staff, bizdev or admin of this structure
            if user.is_staff or user.is_bizdev:
                return True
            try:
                StructureMember.objects.get(
                    user_id=user.id, is_admin=True, structure__slug=structure_slug
                )
                return True
            except StructureMember.DoesNotExist:
                return False
        return False
