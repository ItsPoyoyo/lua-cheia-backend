from django.shortcuts import render

from rest_framework_simplejwt.views import TokenObtainPairView

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny

from userauths.models import User, Profile
from userauths.serializer import MyTokenObtainPairSerializer, RegisterSerializer, UserSerializer, ProfileSerializer
from userauths.serializer import ProfileSerializer  # Move this inside the view function if needed


from rest_framework.response import Response

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
import base64

import random
import shortuuid
import logging


from rest_framework.permissions import IsAuthenticated
# Create your views here.

logger = logging.getLogger(__name__)

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny, )
    serializer_class = RegisterSerializer

def generate_otp():
    uuid_key = shortuuid.uuid()
    unique_key = uuid_key[:6]
    return unique_key



class PasswordResetEmailVerify(generics.RetrieveAPIView):
    permission_classes = (AllowAny, )
    serializer_class = UserSerializer


    def get_object(self):
        email = self.kwargs['email']
        user = User.objects.get(email=email)



        if user: 
            user.otp = generate_otp()
            user.save()

            uidb64 = user.pk
            otp = user.otp

            link = f"http://localhost:5173/create-new-password?otp={otp}&uidb64={uidb64}" 

            print("user =====", link)

            # Send email

            

        return user


class PasswordChangeView(generics.CreateAPIView):
    permission_classes = (AllowAny, )
    serializer_class = UserSerializer

    def create(self, request):
        payload = request.data

        otp = payload['otp']
        uidb64 = payload['uidb64']
        password = payload['password']

        user = User.objects.get(id=uidb64, otp=otp)
        if user:
            user.set_password(password)
            user.otp = ""
            user.save()

            return Response( {"message": "Password Changed Successfully"}, status=status.HTTP_201_CREATED)
        else:
            return Response( {"message": "An Error Occured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ProfileSerializer

    def get_object(self):
        user_id = self.kwargs['user_id']
        user = User.objects.get(id=user_id)
        profile = Profile.objects.get(user=user)
        return profile

class ProfileUpdateView(generics.UpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    lookup_field = 'user_id'

    def update(self, request, *args, **kwargs):
        try:
            print("Incoming request data:", request.data)
            print("Incoming files:", request.FILES)

            # Get the profile instance
            instance = self.get_object()

            # Log current user data
            print("Current user data - Email:", instance.user.email)
            print("Current user data - Phone:", instance.user.phone)

            # Let the serializer handle the update
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            # Refresh the instances
            instance.refresh_from_db()
            instance.user.refresh_from_db()

            # Log updated user data
            print("Updated user data - Email:", instance.user.email)
            print("Updated user data - Phone:", instance.user.phone)

            # Return updated profile data
            return Response(serializer.data)
        except Exception as e:
            print("Error updating profile:", str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)