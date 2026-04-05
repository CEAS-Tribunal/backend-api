from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from dashboard.permissions import IsStaffUser
from dashboard.models import ExecMember, ExecRole
from .serializers import ExecMemberSerializer


class ExecMemberView(GenericAPIView):
    serializer_class = ExecMemberSerializer
    queryset = ExecMember.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated(), IsStaffUser()]

    def get(self, request):
        role_id = request.query_params.get('roleId')
        if not role_id:
            return Response(
                {'error': 'roleId is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            role = ExecRole.objects.get(id=role_id)
        except ExecRole.DoesNotExist:
            return Response(
                {'error': 'Role not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        members = role.ExecMember.all()
        data = ExecMemberSerializer(members, many=True).data
        return Response(data, status=status.HTTP_200_OK)
    def post(self, request):
        serializer = ExecMemberSerializer(data=request.data)
        if serializer.is_valid():
            member = serializer.save()
            return Response({
                'message': 'Member created successfully',
                'member': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'error': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request):
        member_id = request.data.get('id')
        if not member_id:
            return Response({
                'error': 'Member ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            member = ExecMember.objects.get(id=member_id)
            serializer = ExecMemberSerializer(member, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'message': 'Member updated successfully',
                    'member': serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'error': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except ExecMember.DoesNotExist:
            return Response({
                'error': 'Member not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    def delete(self, request):
        member_id = request.data.get('id')
        if not member_id:
            return Response({
                'error': 'Member ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            member = ExecMember.objects.get(id=member_id)
            member.delete()
            return Response({
                'message': 'Member deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except ExecMember.DoesNotExist:
            return Response({
                'error': 'Member not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)