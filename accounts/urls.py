from django.urls import path


from .views import (

    # Authentication

    login_view,
    logout_view,


    # User CRUD

    user_list,
    create_user,
    update_user,
    delete_user,


)



app_name = "accounts"





urlpatterns = [


    # ==================================================
    # AUTHENTICATION
    # ==================================================


    path(

        "",

        login_view,

        name="login"

    ),



    path(

        "logout/",

        logout_view,

        name="logout"

    ),







    # ==================================================
    # USER MANAGEMENT CRUD
    # ==================================================


    path(

        "users/",

        user_list,

        name="user_list"

    ),



    path(

        "users/create/",

        create_user,

        name="create_user"

    ),



    path(

        "users/update/<int:pk>/",

        update_user,

        name="update_user"

    ),



    path(

        "users/delete/<int:pk>/",

        delete_user,

        name="delete_user"

    ),

]