from rest_framework.generics import GenericAPIView 
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from dashboard.models import ExecRole 
from .serializers import ExecRoleSerializer

class ExecRoleView(GenericAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = ExecRoleSerializer
    queryset = ExecRole.objects.all()
    
    def get(self, request):
        roles = ExecRole.objects.values_list('role', flat=True)

        formatted_output = {
            'roles': list(roles),
        }
        
        return Response(formatted_output, status=status.HTTP_200_OK)
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