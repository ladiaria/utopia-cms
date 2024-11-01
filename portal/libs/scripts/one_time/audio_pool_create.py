# UpdateAudioFilePaths.py
from audiologue.models import Audio
import os
import shutil
from django.conf import settings


audios = Audio.objects.all()
for audio in audios:
    if audio.date_uploaded:
        year = audio.date_uploaded.year
        new_file_path = os.path.join('audiologue', str(year), os.path.basename(audio.file.name))
        new_file_full_path = os.path.join(settings.MEDIA_ROOT, new_file_path)

        # Create the new directory if it doesn't exist
        os.makedirs(os.path.dirname(new_file_full_path), exist_ok=True)

        # Move the file to the new directory
        old_file_full_path = os.path.join(settings.MEDIA_ROOT, audio.file.name)
        if os.path.exists(old_file_full_path):
            shutil.move(old_file_full_path, new_file_full_path)
            audio.file.name = new_file_path
            audio.save()
            print(f"SUCCESS: Updated and moved file for Audio ID {audio.id} to {new_file_full_path}")
        else:
            print(f"ERROR: File not found for Audio ID {audio.id}: {old_file_full_path}")
    else:
        print(f"WARNING: Audio ID {audio.id} does not have a date_uploaded")
