
from rest_framework.permissions import DjangoModelPermissions

from rest_framework.permissions import BasePermission


class PuedeModificarCliente(BasePermission):

    def has_permission(self, request, view):

        return request.user.is_authenticated

    def has_object_permission(
        self,
        request,
        view,
        obj
    ):

        if request.method in [
            'GET',
            'HEAD',
            'OPTIONS'
        ]:

            return True

        return request.user.is_staff
class ClienteModelPermissions(DjangoModelPermissions):

    perms_map = {
        'GET': [
            '%(app_label)s.view_%(model_name)s'
        ],

        'OPTIONS': [],

        'HEAD': [],

        'POST': [
            '%(app_label)s.add_%(model_name)s'
        ],

        'PUT': [
            '%(app_label)s.change_%(model_name)s'
        ],

        'PATCH': [
            '%(app_label)s.change_%(model_name)s'
        ],

        'DELETE': [
            '%(app_label)s.delete_%(model_name)s'
        ],
    }
class IsStaffUser(BasePermission):

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated
            and request.user.is_staff
        )