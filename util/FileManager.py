import os
import pathlib
import shutil
from abc import abstractmethod, ABC
from os.path import exists
import boto3
import magic

BUCKET = os.environ.get("BUCKET", '')


class FileManager:
    path = 'Files'

    @staticmethod
    def get_instance():
        if BUCKET == '':
            return LocalFileManager()
        else:
            return AwsS3()

    @abstractmethod
    def save_file(self, file_upload, filename, userId):
        pass

    @abstractmethod
    def delete_file(self, filename, userId):
        pass

    @abstractmethod
    def get_file(self, filename, userId):
        pass

    @abstractmethod
    def return_file(self, filename, userId):
        pass

    def send_file(self, destination_path, target_name, userId):
        pass

    def clean_local_files(self, userId):
        pass

    def _get_filename(self, filename, userId):
        return os.path.join(self.path, str(userId), filename)


class LocalFileManager(FileManager):
    path = os.path.join(os.path.dirname(__file__), f"../Files")

    def get_file(self, filename, userId):
        filepath = self._get_filename(filename, userId)
        return filepath

    def save_file(self, file, filename, userId):
        if not os.path.exists(f"{self.path}/{userId}"):
            os.mkdir(os.path.join(self.path, str(userId)))

        filepath = self._get_filename(filename, userId)
        file_location = os.path.join(self.path, filepath)
        with open(file_location, "wb+") as file_save:
            file_save.write(file.read())

    def delete_file(self, filename, userId):
        filepath = self._get_filename(filename, userId)
        if os.path.exists(filepath):
            os.remove(filepath)
        else:
            raise FileNotFoundError

    def return_file(self, filename, userId):
        filepath = self.get_file(filename, userId)
        if exists(filepath):
            return filepath
        else:
            raise FileNotFoundError


class AwsS3(FileManager):
    def __init__(self) -> None:
        self.s3 = boto3.resource('s3')
        self.bucket = self.s3.Bucket(BUCKET)
        self.s3_client = boto3.client('s3')

    def return_file(self, filename, userId):
        key = self._get_filename(filename, userId)
        return self.s3_client.generate_presigned_url('get_object',
                                              Params={'Bucket': BUCKET,
                                                      'Key': key},
                                              ExpiresIn=3600)

    def save_file(self, file_upload, filename, userId):
        key = self._get_filename(filename, userId)
        self.bucket.put_object(
            Key=key,
            Body=file_upload,
        )

    def delete_file(self, filename, userId):
        filename = self._get_filename(filename, userId)
        self.bucket.delete_objects(
            Delete={
                'Objects': [{'Key': filename}]
            }
        )

    def get_file(self, filename, userId):
        filepath = self._get_filename(filename, userId)
        if not os.path.exists(f"./{self.path}/{userId}"):
            os.mkdir(f"./{self.path}/{userId}/")

        self.bucket.download_file(filepath, filepath)
        return filepath

    def send_file(self, filepath, filename, userId):
        self.save_file(open(filepath, 'rb'), filename, userId)
        self.clean_local_files(userId)

    def clean_local_files(self, userId):
        shutil.rmtree(f"./{self.path}/{userId}/")
