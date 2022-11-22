from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from dora.structures.models import StructureMember

from .models import User


class StructureMemberInline(admin.TabularInline):
    model = StructureMember
    readonly_fields = ["user", "structure"]
    extra = 0

    def has_add_permission(self, request, obj):
        return False


class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""

    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Password confirmation", widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ("email",)

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


@admin.display(description="Sur Inclusion Connect", boolean=True, ordering="ic_id")
def has_migrated_to_ic(obj):
    return obj.ic_id is not None


class UserAdmin(BaseUserAdmin):
    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    # The forms to add and change user instances
    form = UserChangeForm
    add_form = UserCreationForm

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = (
        "email",
        "get_full_name",
        "is_staff",
        "is_bizdev",
        "is_active",
        "is_valid",
        "date_joined",
        "newsletter",
        has_migrated_to_ic,
    )
    list_filter = ("is_staff", "is_bizdev", "is_active", "is_valid", "newsletter")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "email",
                    "password",
                    "last_name",
                    "first_name",
                    "phone_number",
                    has_migrated_to_ic,
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_staff",
                    "is_bizdev",
                    "is_active",
                    "is_valid",
                    "newsletter",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
    search_fields = ("email", "last_name", "first_name")
    readonly_fields = ["newsletter", has_migrated_to_ic]
    ordering = ("-date_joined",)
    filter_horizontal = ()
    inlines = [StructureMemberInline]


# Now register the new UserAdmin...
admin.site.register(User, UserAdmin)
# ... and, since we're not using Django's built-in permissions,
# unregister the Group model from admin.
admin.site.unregister(Group)
