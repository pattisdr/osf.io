from django.conf.urls import url

from api.guids import views

app_name = 'osf'

urlpatterns = [
    url(r'^(?P<guids>\w+)/$', views.GuidDetail.as_view(), name=views.GuidDetail.view_name),
]
