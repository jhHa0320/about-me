from .models import Profile

def global_profile(request):
    profile = Profile.objects.first()
    return {'global_profile': profile}
