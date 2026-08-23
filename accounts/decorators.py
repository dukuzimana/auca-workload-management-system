from functools import wraps

from django.shortcuts import redirect
from django.contrib import messages



# ==================================
# ROLE REQUIRED
# ==================================

def role_required(allowed_roles):

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if not request.user.is_authenticated:

                messages.error(
                    request,
                    "Please login to access this page."
                )

                return redirect("accounts:login")



            user = request.user

            role = getattr(
                user,
                "role",
                None
            )



            # Administrator

            if (
                user.is_superuser
                or role == "admin"
            ):

                if "admin" in allowed_roles:

                    return view_func(
                        request,
                        *args,
                        **kwargs
                    )



            # Normal users

            if role in allowed_roles:

                return view_func(
                    request,
                    *args,
                    **kwargs
                )



            messages.error(
                request,
                "You do not have permission to access this page."
            )


            return redirect("accounts:login")


        return wrapper


    return decorator






# ==================================
# ADMIN ONLY
# ==================================

def admin_required(view_func):


    @wraps(view_func)

    def wrapper(request, *args, **kwargs):


        if not request.user.is_authenticated:


            messages.error(
                request,
                "Please login first."
            )


            return redirect("accounts:login")




        user = request.user


        if (
            user.is_superuser
            or getattr(user, "role", None) == "admin"
        ):

            return view_func(
                request,
                *args,
                **kwargs
            )




        messages.error(
            request,
            "Administrator access only."
        )


        return redirect("accounts:login")


    return wrapper






# ==================================
# LECTURER ONLY
# ==================================

def lecturer_required(view_func):


    @wraps(view_func)

    def wrapper(request, *args, **kwargs):


        if not request.user.is_authenticated:


            messages.error(
                request,
                "Please login first."
            )


            return redirect("accounts:login")




        role = getattr(
            request.user,
            "role",
            None
        )



        if role == "lecturer":


            return view_func(
                request,
                *args,
                **kwargs
            )




        messages.error(
            request,
            "Lecturer access only."
        )


        return redirect("accounts:login")



    return wrapper






# ==================================
# REPRESENTATIVE ONLY
# ==================================

def representative_required(view_func):


    @wraps(view_func)

    def wrapper(request, *args, **kwargs):


        if not request.user.is_authenticated:


            messages.error(
                request,
                "Please login first."
            )


            return redirect("accounts:login")




        role = getattr(
            request.user,
            "role",
            None
        )



        if role == "representative":


            return view_func(
                request,
                *args,
                **kwargs
            )




        messages.error(
            request,
            "Representative access only."
        )


        return redirect("accounts:login")



    return wrapper
