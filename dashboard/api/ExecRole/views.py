from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from dashboard.permissions import IsStaffUser
from dashboard.models import ExecRole
from dashboard.api.ExecMember.serializers import ExecMemberSerializer
from .serializers import ExecRoleSerializer


class ExecRoleView(GenericAPIView):
    serializer_class = ExecRoleSerializer
    queryset = ExecRole.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated(), IsStaffUser()]

    def get(self, request):
        include_members = request.query_params.get("include_members", "").lower() in ("true", "1", "yes")
        sections = [
            {
                "id": "president",
                "color": "indigo",
                "title": "Officers",
                "subtitle": "Executive Role",
                "roles": self._roles_for_committee("pres", include_members),
            },
            {
                "id": "cos",
                "color": "teal",
                "title": "Chief of Staff",
                "subtitle": "Executive Role",
                "roles": self._roles_for_committee("cos", include_members),
            },
            {
                "id": "vpca",
                "color": "rose",
                "title": "Vice President of Collegiate Affairs",
                "subtitle": "Executive Role",
                "roles": self._roles_for_committee("vpca", include_members),
            },
            {
                "id": "vpe",
                "color": "sky",
                "title": "Vice President of Events",
                "subtitle": "Executive Role",
                "roles": self._roles_for_committee("vpe", include_members),
            },
        ]
        return Response(sections, status=status.HTTP_200_OK)

    # Preferred order for role names (first in list = first on page). Others stay alphabetical after these.
    ROLE_DISPLAY_ORDER = [
        "President",
        "Chief of Staff",
        "Vice President of Events",
        "Vice President of Collegiate Affairs",
        "Treasurer",
        "Senators",
        "Partnership Development",
    ]

    def _roles_for_committee(self, committee_value, include_members):
        qs = ExecRole.objects.filter(committee=committee_value).order_by("role")
        if include_members:
            qs = qs.prefetch_related("ExecMember__user")
        roles = []
        for role in qs:
            payload = {"id": role.id, "role": role.role, "description": role.description}
            if include_members:
                members = role.ExecMember.all()
                payload["members"] = ExecMemberSerializer(members, many=True).data
            roles.append(payload)
        # Sort: preferred order first, then the rest alphabetically by role name
        order_map = {name: i for i, name in enumerate(self.ROLE_DISPLAY_ORDER)}

        def sort_key(item):
            name = item["role"]
            if name in order_map:
                return (0, order_map[name])
            return (1, name.lower())

        roles.sort(key=sort_key)
        return roles

    def post(self, request):
        serializer = ExecRoleSerializer(data=request.data)
        if serializer.is_valid():
            role = serializer.save()
            return Response({
                'message': 'Role created successfully',
                'role': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'error': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request):
        role_id = request.data.get('id')
        if not role_id:
            return Response({
                'error': 'Role ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            role = ExecRole.objects.get(id=role_id)
            serializer = ExecRoleSerializer(role, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'message': 'Role updated successfully',
                    'role': serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'error': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except ExecRole.DoesNotExist:
            return Response({
                'error': 'Role not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    def delete(self, request):
        role_id = request.data.get('id')
        if not role_id:
            return Response({
                'error': 'Role ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            role = ExecRole.objects.get(id=role_id)
            role.delete()
            return Response({
                'message': 'Role deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except ExecRole.DoesNotExist:
            return Response({
                'error': 'Role not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)