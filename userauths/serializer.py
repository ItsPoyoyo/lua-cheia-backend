from django.contrib.auth.password_validation import validate_password

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer 


from userauths.models import Profile, User

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token['full_name'] = user.full_name
        token['email'] = user.email
        token['username'] = user.username
        try:
            token['vendor_id'] = user.vendor.id
        except:
            token['vendor_id'] = 0

        return token
        
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError("Passwords must match")
        return attrs
    
    def create(self, validated_data):
        user = User.objects.create(
            full_name=validated_data['full_name'],
            email=validated_data['email'],
            phone=validated_data['phone'],
        )

        email_user, mobile = user.email.split("@")
        user.username = email_user
        user.set_password(validated_data['password'])
        user.save()
        
        return user

# In serializers.py
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'phone']  # Ensure phone is included
        

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Profile
        fields = ['id', 'full_name', 'address', 'city', 'state', 'country', 'image', 'user']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        user = instance.user

        if user_data:
            email = user_data.get('email', user.email)  # Keep existing email if not provided
            phone = user_data.get('phone', user.phone)

            # Check if the email or phone has changed
            if email != user.email or phone != user.phone:
                # Ensure the email/phone is not already taken by someone else
                if User.objects.filter(email=email).exclude(id=user.id).exists():
                    raise serializers.ValidationError({'email': 'This email is already taken by another user.'})
                if User.objects.filter(phone=phone).exclude(id=user.id).exists():
                    raise serializers.ValidationError({'phone': 'This phone number is already taken by another user.'})

                # Save the changes
                user.email = email
                user.phone = phone
                user.save(update_fields=['email', 'phone'])

        # Update profile fields
        instance.full_name = validated_data.get('full_name', instance.full_name)
        instance.address = validated_data.get('address', instance.address)
        instance.city = validated_data.get('city', instance.city)
        instance.state = validated_data.get('state', instance.state)
        instance.country = validated_data.get('country', instance.country)
        instance.image = validated_data.get('image', instance.image)
        instance.save()

        return instance
