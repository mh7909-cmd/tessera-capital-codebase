"""
Google Drive Service (OAuth2 Version)
负责将生成的报告上传到指定的 Google Drive 文件夹
使用 OAuth2 以支持个人账号的存储配额
"""

import os
import pickle
from typing import List, Optional
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from ..utils.logger import get_logger

logger = get_logger('mirofish.gdrive')

class GDriveService:
    """
    Google Drive 上传服务 (OAuth2)
    """
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    DEFAULT_FOLDER_ID = '1kE4OmpQOGTheULpGOY2ZD4YE62hVH6jj'
    
    def __init__(self, token_path: Optional[str] = None):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.token_path = token_path or os.path.join(self.base_dir, 'token.pickle')
        self.credentials_path = os.path.join(self.base_dir, 'client_secrets.json')
        self.service = self._authenticate()

    def _authenticate(self):
        """
        使用 OAuth2 Token 认证
        """
        creds = None
        # token.pickle 存储用户的访问和刷新令牌
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # 如果没有有效的凭据，则失败（由外部 setup 脚本处理初始认证）
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    with open(self.token_path, 'wb') as token:
                        pickle.dump(creds, token)
                except Exception as e:
                    logger.error(f"刷新 Google Token 失败: {str(e)}")
                    return None
            else:
                logger.error("找不到有效的 Google OAuth Token。请先运行 setup_gdrive.py")
                return None
        
        try:
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            logger.error(f"创建 Google Drive 服务失败: {str(e)}")
            return None

    def upload_file(self, file_path: str, folder_id: Optional[str] = None) -> Optional[str]:
        """
        上传单个文件
        """
        if not self.service:
            logger.error("GDrive 服务未初始化 (OAuth)，跳过上传")
            return None
        
        if not file_path or not os.path.exists(file_path):
            logger.error(f"要上传的文件不存在: {file_path}")
            return None
        
        folder_id = folder_id or self.DEFAULT_FOLDER_ID
        file_name = os.path.basename(file_path)
        
        # 确定 MIME 类型
        mime_type = 'application/octet-stream'
        if file_path.endswith('.pdf'):
            mime_type = 'application/pdf'
        elif file_path.endswith('.docx'):
            mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif file_path.endswith('.md'):
            mime_type = 'text/markdown'
            
        try:
            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            media = MediaFileUpload(file_path, mimetype=mime_type)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"文件上传成功: {file_name} (ID: {file_id})")
            return file_id
            
        except Exception as e:
            logger.error(f"上传文件失败 {file_name}: {str(e)}")
            return None

    def upload_batch(self, file_paths: List[str], folder_id: Optional[str] = None) -> List[str]:
        """
        批量上传文件
        """
        if not self.service:
            return []
            
        results = []
        for path in file_paths:
            if path:
                fid = self.upload_file(path, folder_id)
                if fid:
                    results.append(fid)
        return results
