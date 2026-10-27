from django.db import models
import uuid

class Case(models.Model):
    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title=models.CharField(max_length=255)
    introduction= models.TextField()
    crime_scene_description=models.TextField()

    #To the player 
    public_data = models.JSONField(default=dict)

    #Secret solution not to be revealed
    solution = models.JSONField(default=dict)

    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

