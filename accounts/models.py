from django.contrib.auth.models import AbstractUser
from django.db import models



# ==================================================
# USER MODEL
# ==================================================

class User(AbstractUser):


    ROLE_CHOICES = [

        ('admin', 'Admin'),

        ('lecturer', 'Lecturer'),

        ('representative', 'Class Representative'),

    ]



    role = models.CharField(

        max_length=20,

        choices=ROLE_CHOICES,

        default='lecturer'

    )



    def __str__(self):

        return self.username


# Account linking lives on academics.Lecturer.user and
# academics.Cohort.representative -- not here. The assignment
# models that used to duplicate it were dropped in migration
# 0006 (links copied onto the records first, in 0005).

