from io import BytesIO
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import oci
from fastapi import UploadFile, Depends

from app.core.config import settings
from app.core.exceptions import AppError


class OCIObjectStorageClient:
    ALLOWED_CONTENT_TYPES = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }

    def __init__(self) -> None:
        config = {
            "user": settings.OCI_USER_OCID,
            "key_file": settings.OCI_API_KEY_PATH,
            "fingerprint": settings.OCI_FINGERPRINT,
            "tenancy": settings.OCI_TENANCY_OCID,
            "region": settings.OCI_REGION,
        }

        self.bucket_name = settings.OCI_OBJECT_STORAGE_BUCKET
        self.namespace = settings.OCI_OBJECT_STORAGE_NAMESPACE
        self.base_url = (
            f"https://objectstorage.{settings.OCI_REGION}.oraclecloud.com"
        )

        self.client = oci.object_storage.ObjectStorageClient(config)
        self.upload_manager = oci.object_storage.UploadManager(self.client)

    async def upload_object(
            self,
            *,
            file: UploadFile,
            object_prefix: str,
    ) -> str:
        if not file.filename:
            raise AppError.bad_request("업로드할 파일 이름이 없습니다.")

        content_type = file.content_type or ""
        if content_type not in self.ALLOWED_CONTENT_TYPES:
            raise AppError.bad_request("지원하지 않는 파일 형식입니다.")

        ext = Path(file.filename).suffix.lower()
        if not ext:
            ext = self.ALLOWED_CONTENT_TYPES[content_type]

        object_name = f"{object_prefix}/{uuid4().hex}{ext}"

        data = await file.read()
        if not data:
            raise AppError.bad_request("빈 파일은 업로드할 수 없습니다.")

        max_size = 5 * 1024 * 1024
        if len(data) > max_size:
            raise AppError.bad_request("이미지 크기는 5MB 이하여햐 합니다.")

        stream = BytesIO(data)

        self.upload_manager.upload_stream(
            namespace_name=self.namespace,
            bucket_name=self.bucket_name,
            object_name=object_name,
            stream_ref=stream,
            content_type=content_type,
        )

        return object_name

    async def delete_object(self, object_name: str) -> None:
        self.client.delete_object(
            namespace_name=self.namespace,
            bucket_name=self.bucket_name,
            object_name=object_name,
        )

    def build_object_url(self, object_name: str) -> str:
        return (
            f"{self.base_url}/n/{self.namespace}/b/{self.bucket_name}/o/{object_name}"
        )

def get_oci_object_storage_client() -> OCIObjectStorageClient:
    return OCIObjectStorageClient()

OCIObjectStorageClientDep = Annotated[
    OCIObjectStorageClient,
    Depends(get_oci_object_storage_client)
]