from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib.auth import (
    authenticate,
    login,
    logout
)

from django.contrib import messages

from django.contrib.auth.decorators import login_required

from accounts.decorators import admin_required

from common.search import (
    search,
    search_context,
    USER_SEARCH_FIELDS,
)

from .forms import (
    UserCreateForm,
    UserUpdateForm,
)

from .models import User

from academics.models import (
    Lecturer,
    Cohort
)


# ==================================================
# LOGIN
# ==================================================

def login_view(request):

    if request.user.is_authenticated:
        return redirect_user(request.user)

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user:

            if not user.is_active:

                messages.error(
                    request,
                    "Your account is inactive."
                )

                return redirect("accounts:login")

            login(
                request,
                user
            )

            return redirect_user(user)

        else:

            messages.error(
                request,
                "Invalid username or password."
            )

    return render(
        request,
        "accounts/login.html"
    )


# ==================================================
# ROLE REDIRECTION
# ==================================================

def redirect_user(user):

    if user.is_superuser or user.role == "admin":
        return redirect("admin_dashboard")

    elif user.role == "lecturer":
        return redirect("workload:lecturer_dashboard")

    elif user.role == "representative":
        return redirect("workload:representative_dashboard")

    return redirect("accounts:login")


# ==================================================
# LOGOUT
# ==================================================

@login_required
def logout_view(request):

    logout(request)

    messages.success(
        request,
        "Logged out successfully."
    )

    return redirect("accounts:login")


# ==================================================
# USER CRUD
# ==================================================

@login_required
@admin_required
def user_list(request):

    users = User.objects.all()


    # Applied before the text search, so searching within a role
    # stays within it. An unknown value is ignored.
    role = request.GET.get("role", "").strip()

    if role in dict(User.ROLE_CHOICES):

        users = users.filter(role=role)


    context = {
        "users": search(
            users,
            search_context(request)["search_query"],
            USER_SEARCH_FIELDS
        ).order_by("username"),

        "total_count": users.count(),
    }

    context.update(
        search_context(
            request,
            placeholder="Search by username, email or role"
        )
    )

    context["result_count"] = context["users"].count()

    context["role_choices"] = User.ROLE_CHOICES

    context["selected_role"] = role

    return render(
        request,
        "accounts/users.html",
        context
    )


@login_required
@admin_required
def create_user(request):

    if request.method == "POST":

        form = UserCreateForm(request.POST)

        if form.is_valid():

            user = form.save()

            if user.role == "admin":
                user.is_staff = True
                user.save()

            messages.success(
                request,
                f"User {user.username} created successfully."
            )

            # A login does nothing until a lecturer or cohort points at it.
            if user.role == "lecturer":

                messages.info(
                    request,
                    "Next, open Academics > Lecturers and set this "
                    "account on the lecturer's record -- either by "
                    "adding the lecturer, or by editing an existing "
                    "one. Until then their workload will not appear "
                    "when they sign in, and assignment emails cannot "
                    "reach them."
                )

            elif user.role == "representative":

                messages.info(
                    request,
                    "Next, open Academics > Cohorts and set this "
                    "account as the cohort's representative -- either "
                    "by adding the cohort, or by editing an existing "
                    "one. Until then their calendar will not appear "
                    "when they sign in, and assignment emails cannot "
                    "reach them."
                )

            return redirect("accounts:user_list")

    else:

        form = UserCreateForm()

    return render(
        request,
        "accounts/create_user.html",
        {
            "form": form
        }
    )


@login_required
@admin_required
def update_user(request, pk):

    user = get_object_or_404(
        User,
        pk=pk
    )

    if request.method == "POST":

        form = UserUpdateForm(
            request.POST,
            instance=user
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "User updated successfully."
            )

            return redirect("accounts:user_list")

    else:

        form = UserUpdateForm(instance=user)

    return render(
        request,
        "accounts/update_user.html",
        {
            "form": form,
            "account": user
        }
    )


@login_required
@admin_required
def delete_user(request, pk):

    user = get_object_or_404(
        User,
        pk=pk
    )

    if request.method == "POST":

        # Deleting the last administrator locks everyone out of user
        # management, with no way back through the UI.
        if user.is_superuser or user.role == "admin":

            remaining = User.objects.filter(
                is_active=True
            ).exclude(
                pk=user.pk
            ).filter(
                role="admin"
            ).count()

            remaining += User.objects.filter(
                is_active=True,
                is_superuser=True
            ).exclude(
                pk=user.pk
            ).exclude(
                role="admin"
            ).count()

            if remaining == 0:

                messages.error(
                    request,
                    "This is the only administrator account. "
                    "Create another administrator before deleting "
                    "this one."
                )

                return redirect("accounts:user_list")

        if user == request.user:

            messages.error(
                request,
                "You cannot delete the account you are signed in with."
            )

            return redirect("accounts:user_list")

        username = user.username

        user.delete()

        messages.success(
            request,
            f"User {username} deleted. Any lecturer record or cohort "
            "they were linked to has been kept and is now unlinked."
        )

        return redirect("accounts:user_list")

    # Show what else the deletion touches, so the confirmation is
    # informed rather than blind.
    lecturer = Lecturer.objects.filter(user=user).first()
    cohort = Cohort.objects.filter(representative=user).first()

    return render(
        request,
        "accounts/delete_user.html",
        {
            # Named "account", not "user": the sidebar renders from
            # {{ user }}, so "user" here shadows the signed-in admin.
            "account": user,
            "linked_lecturer": lecturer,
            "linked_cohort": cohort,
        }
    )
