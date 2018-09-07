from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^(?P<request_id>\w+)/$', views.RequestDetail.as_view(), name=views.RequestDetail.view_name),
    url(r'^(?P<request_id>\w+)/actions/$', views.RequestActionList.as_view(), name=views.RequestActionList.view_name),
]
